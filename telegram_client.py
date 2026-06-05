import os
import logging
from telethon import TelegramClient, events
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramBotClient:
    def __init__(self, api_id, api_hash, bot_username='leomatchbot'):
        self.api_id = api_id
        self.api_hash = api_hash
        self.bot_username = bot_username
        self.client = TelegramClient('session_name', self.api_id, self.api_hash)

    async def start(self):
        await self.client.start()
        logger.info("Telegram Client started.")

    async def send_message(self, text):
        await self.client.send_message(self.bot_username, text)
        logger.info(f"Sent message to {self.bot_username}: {text}")

    def on_message_received(self, event):
        """
        This will be passed to Telethon's event listener.
        """
        if event.chat.username == self.bot_username or event.chat.id == self.bot_username:
            return event.message.text
        return None

    async def disconnect(self):
        await self.client.disconnect()
        logger.info("Telegram Client disconnected.")

    def get_client(self):
        return self.client