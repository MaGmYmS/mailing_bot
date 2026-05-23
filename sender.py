import logging
from datetime import datetime
from uuid import uuid4

from telegram import Bot
from telegram.error import TelegramError

from db_json import add_message, get_messages, update_message_views


logger = logging.getLogger(__name__)


async def send_to_groups(bot: Bot, groups: list, text: str):
    success = 0
    failed = 0

    for group in groups:
        try:
            sent_message = await bot.send_message(
                chat_id=group["chat_id"],
                text=text
            )

            message_data = {
                "internal_id": str(uuid4()),
                "text": text[:100],
                "date_sent": datetime.utcnow().isoformat(),
                "platform": "telegram",
                "chat_id": group["chat_id"],
                "group_name": group["title"],
                "message_id": sent_message.message_id,
                "views": 0,
                "last_view_update": datetime.utcnow().isoformat()
            }

            await add_message(message_data)

            success += 1

        except TelegramError as e:
            logger.error(f"Send error: {e}")
            failed += 1

    return success, failed


async def update_views(bot: Bot):
    messages = await get_messages()

    for msg in messages:
        try:
            chat = await bot.get_chat(msg["chat_id"])

            # Telegram Bot API не позволяет получать просмотры
            # сообщений в группах напрямую.
            # Для каналов можно читать forwarded/public stats,
            # но полноценно views API не предоставляет.

            current_views = msg.get("views", 0)

            await update_message_views(
                msg["internal_id"],
                current_views
            )

        except Exception as e:
            logger.error(f"Views update error: {e}")