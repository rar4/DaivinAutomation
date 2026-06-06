import asyncio
import logging
import os
import random
import re
import time
from operator import is_

from openai._utils import is_mapping
from telethon.errors.rpcerrorlist import ScoreInvalidError

logger = logging.getLogger(__name__)

# Unicode emojis for reactions
HEART_EMOJI = "❤️"
DISLIKE_EMOJI = "👎"


class LeoMatchBotModule:
    """Module for handling automated profile browsing on @leomatchbot."""

    def __init__(self, bot_client, analyzer, db):
        self.bot_client = bot_client
        self.analyzer = analyzer
        self.db = db
        self.profiles_to_browse = 0
        self.is_browsing = False
        self._last_recovery_time = 0

    def _random_pause(self):
        """Adds a random pause between 1-3 seconds (sync/blocking)."""
        pause_seconds = random.uniform(1, 3)
        time.sleep(pause_seconds)

    async def start_browsing(self):
        """Initiates the browsing session: sends /start, then 1, then sets random profile count."""
        self.is_browsing = True

        # Load range from env or use defaults
        min_profiles = int(os.getenv("PROFILES_MIN", 5))
        max_profiles = int(os.getenv("PROFILES_MAX", 20))
        self.profiles_to_browse = random.randint(min_profiles, max_profiles)

        logger.info(
            f"Starting browsing session. Target: {self.profiles_to_browse} profiles."
        )

        # Send /start command
        await self.bot_client.send_message("/start")
        self._random_pause()
        logger.info("Sent /start command to leomatchbot.")

        # Send '1' to start browsing people
        await self.bot_client.send_message("1")
        self._random_pause()
        logger.info("Sent '1' to start browsing people.")

    async def return_to_browsing(self):
        """Sends /start and 1 to return to profile browsing after misc message."""
        # Cooldown check: prevent flooding /start if called too frequently (e.g., every 10 seconds)
        current_time = asyncio.get_event_loop().time()
        if current_time - self._last_recovery_time < 10:
            logger.info(
                "Recovery cooldown active. Skipping /start to prevent flooding."
            )
            return

        self._last_recovery_time = current_time
        logger.info("Returning to profile browsing...")
        await self.bot_client.send_message("/start")
        self._random_pause()
        await self.bot_client.send_message("1")
        self._random_pause()
        logger.info("Returned to profile browsing.")

    def _extract_photos(self, event):
        """
        Extracts photo data from a message event.
        Returns a list of photo data or empty list if no photos.
        """
        photos = []
        if hasattr(event.message, "media") and event.message.media:
            # Check for photo in media
            if hasattr(event.message.media, "photo"):
                photos.append(event.message.media.photo)
            # Check for document (could be photo)
            elif hasattr(event.message.media, "document"):
                photos.append(event.message.media.document)
        return photos

    def _parse_and_save_user(self, profile_text: str, photos: list) -> tuple:
        """
        Parses Russian profile format: "Name, Age, City – Description"
        Returns tuple of (age, name, last_name, bio, photos) for database saving.
        """
        # Pattern: "Name, Age, City – Description"
        pattern = r"(\w+), (\d{2}), (\w+) – ([\s\S]*)"
        match = re.match(pattern, profile_text)

        if match:
            name = match.group(1).strip()
            age = int(match.group(2).strip())
            _city = match.group(3).strip()  # noqa: F841 - extracted for future use
            description = match.group(4)

            # Split name into first and last name

            return (age, name, description, photos)

        # Return defaults if pattern doesn't match
        return (None, None, profile_text, photos)

    async def handle_message(self, event):
        """
        Handles incoming messages from leomatchbot during browsing.
        Returns True if the message was processed, False otherwise.
        """
        try:
            profile_text = event.message.text

            # Extract photos from the event
            photos = self._extract_photos(event)

            if not self.is_browsing:
                return False

            logger.info(f"Received profile:\n{profile_text}")

            # Parse user data from profile text
            parsed_user = self._parse_and_save_user(profile_text, photos)
            description = parsed_user[2]

            if parsed_user[1] == "Олександр":
                logger.info("Skipping User's profile")
                return False
            # Length check: dislike if description is less than 150 symbols
            if len(description) < 150:
                logger.info(
                    f"Profile description too short ({len(description)} symbols). Auto-disliking."
                )
                # Add a pause to simulate analysis time and avoid rapid-fire disliking
                self._random_pause()
                analysis_result = {
                    "score": 0,
                    "interest": "Too short",
                    "summary": f"Description too short ({len(description)} symbols).",
                }
                is_match = "NO"
                score = 0
            else:
                # Analyze the profile (run in thread pool to avoid blocking)
                analysis_result = await asyncio.get_event_loop().run_in_executor(
                    None, self.analyzer.analyze_profile, profile_text, photos
                )
                logger.info(analysis_result)
                is_match = analysis_result["is_match"]
                score = analysis_result["score"]

            # Save user to database (run in thread pool to avoid blocking)
            user_id = await asyncio.get_event_loop().run_in_executor(
                None,
                self.db.save_user,
                parsed_user[0],
                parsed_user[1],
                parsed_user[2],
                parsed_user[3],
            )

            # Check if score is above threshold (55)
            if is_match == "YES":
                logger.info(f"Profile matches (score: {score}). Sending {HEART_EMOJI}")
                await self._send_reaction(HEART_EMOJI)
            else:
                logger.info(
                    f"Profile does not match (score: {score}). Sending {DISLIKE_EMOJI}"
                )
                await self._send_reaction(DISLIKE_EMOJI)

            # Save analysis to database (run in thread pool to avoid blocking)
            interest_id = await asyncio.get_event_loop().run_in_executor(
                None, self.db.save_interest, analysis_result["interest"]
            )
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.db.save_analysis,
                user_id,
                self.analyzer.model,
                "prompts/system_prompt.md",
                score,
                analysis_result["summary"],
                interest_id,
                None,
            )

            # Decrement counter and check if done
            self.profiles_to_browse -= 1
            if self.profiles_to_browse <= 0:
                logger.info("Browsing session complete. Stopping.")
                self.is_browsing = False

            return True
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return False

    async def _send_reaction(self, emoji: str):
        """Sends an emoji reaction to the bot."""
        await self.bot_client.send_message(emoji)
        self._random_pause()
