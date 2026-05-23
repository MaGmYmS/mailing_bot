import asyncio
import logging
from datetime import datetime, timedelta

import pytz

from config import (
    WEEKLY_STATS_DAY,
    WEEKLY_STATS_HOUR_MSK,
    ADMINS
)

from stats import generate_stats


logger = logging.getLogger(__name__)


DAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6
}


async def weekly_stats_scheduler(application):
    while True:
        now = datetime.now(pytz.timezone("Europe/Moscow"))

        target_day = DAYS[WEEKLY_STATS_DAY]

        days_ahead = target_day - now.weekday()

        if days_ahead < 0:
            days_ahead += 7

        target = now.replace(
            hour=WEEKLY_STATS_HOUR_MSK,
            minute=0,
            second=0,
            microsecond=0
        ) + timedelta(days=days_ahead)

        if target <= now:
            target += timedelta(days=7)

        sleep_seconds = (target - now).total_seconds()

        logger.info(f"Weekly stats sleep: {sleep_seconds}")

        await asyncio.sleep(sleep_seconds)

        report = await generate_stats()

        for admin_id in ADMINS:
            try:
                await application.bot.send_message(
                    chat_id=admin_id,
                    text=f"📈 Ваша еженедельная статистика:\n\n{report}"
                )
            except Exception as e:
                logger.error(f"Weekly stats send error: {e}")