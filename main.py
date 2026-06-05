import os
import asyncio
import logging
from dotenv import load_dotenv
from telethon import events
from telegram_client import TelegramBotClient
from llm_analyzer import LLMAnalyzer
from database import DatabaseManager

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

    await bot_client.start()
    client = bot_client.get_client()

    logger.info("Bot is running and listening for profiles from @leomatchbot...")

    @client.on(events.NewMessage(chats='leomatchbot'))
    async def handler(event):
        profile_text = event.message.text
        logger.info(f"Received profile:\n{profile_text}")

        # 1. Analyze the profile
        analysis_result = analyzer.analyze_profile(profile_text)
        is_match = analysis_result["is_match"]
        
        # 2. Save User (Basic extraction - in a real app, you'd parse the profile_text)
        # For now, we store the raw text as bio and use a placeholder for other fields
        user_id = db.save_user(
            age=None, 
            name="Unknown", 
            last_name="Unknown", 
            bio=profile_text, 
            photos=None
        )

        if is_match:
            logger.info("Match found! Generating opener...")
            # 3. Generate a personalized message
            opener = analyzer.generate_opener(profile_text)
            logger.info(f"Generated opener: {opener}")
            
            # 4. Save Interest and Analysis
            interest_id = db.save_interest(analysis_result["interest"])
            db.save_analysis(
                user_id=user_id,
                model_name=analyzer.model,
                prompt_path="prompts/system_prompt.md",
                match_score=analysis_result["score"],
                profile_summary=analysis_result["summary"],
                interest_id=interest_id,
                opener=opener
            )
            
            # 5. Send the message to the bot
            await bot_client.send_message(opener)
        else:
            logger.info("Profile does not match preferences. Skipping.")

    # Keep the client running
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopped by user.")