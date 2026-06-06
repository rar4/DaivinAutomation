import asyncio
import logging
import os
import re

from dotenv import load_dotenv
from telethon import events

from database import DatabaseManager
from leomatch_module import LeoMatchBotModule
from llm_analyzer import LLMAnalyzer
from telegram_client import TelegramBotClient

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _is_profile_message(text: str) -> bool:
    """
    Detects if a message is a profile based on Russian text structure.
    Format: "Name, Age, City – Description"
    """
    if not text:
        return False

    # Check for Russian profile pattern: "Name, Age, City – Description"
    pattern = r"^[^,]+,\s*\d+,\s*[^,]+?\s*"
    return bool(re.match(pattern, text))


async def main():
    # Load config from environment
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")

    if not api_id or not api_hash:
        logger.error("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in .env")
        return

    # Initialize components
    bot_client = TelegramBotClient(api_id, api_hash)
    analyzer = LLMAnalyzer()
    db = DatabaseManager()

    # Initialize LeoMatchBot module
    leomatch_module = LeoMatchBotModule(bot_client, analyzer, db)

    await bot_client.start()
    client = bot_client.get_client()

    logger.info("Bot is running and listening for profiles from @leomatchbot...")

    # Register handler - only process profile messages (text with pattern)
    @client.on(events.NewMessage(chats="leomatchbot"))
    async def handler(event):
        try:
            text = event.message.text if event.message else ""
            # Only process if it matches the profile pattern
            if _is_profile_message(text):
                await leomatch_module.handle_message(event)
        except Exception as e:
            logger.error(f"Handler error: {e}")

    # Start browsing session AFTER handler is registered
    await leomatch_module.start_browsing()

    # Keep the client running
    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopped by user.")
