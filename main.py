import asyncio
import logging

from telegram import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

from config import BOT_TOKEN, ADMINS, LOG_FILE

from db_json import (
    ensure_files,
    add_group,
    get_groups,
    remove_group
)

from sender import send_to_groups, update_views

from stats import generate_stats

from scheduler import weekly_stats_scheduler


logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("➕ Добавить группу")],
        [KeyboardButton("📋 Мои группы")],
        [KeyboardButton("❌ Удалить группу")],
        [KeyboardButton("📊 Статистика")]
    ],
    resize_keyboard=True
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("Нет доступа")
        return

    await update.message.reply_text(
        "Бот запущен",
        reply_markup=MAIN_KEYBOARD
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return

    text = update.message.text

    if text == "➕ Добавить группу":
        context.user_data["waiting_group"] = True

        await update.message.reply_text(
            "Отправьте ссылку на группу:"
        )

        return

    if context.user_data.get("waiting_group"):
        context.user_data["waiting_group"] = False

        try:
            chat = await context.bot.get_chat(text)

            admins = await context.bot.get_chat_administrators(chat.id)

            bot_id = context.bot.id

            is_admin = any(
                admin.user.id == bot_id
                for admin in admins
            )

            if not is_admin:
                await update.message.reply_text(
                    "Бот должен быть администратором группы"
                )
                return

            await add_group({
                "chat_id": chat.id,
                "title": chat.title,
                "username": chat.username
            })

            await update.message.reply_text(
                f"Группа добавлена: {chat.title}"
            )

        except Exception as e:
            logger.error(e)

            await update.message.reply_text(
                "Не удалось добавить группу"
            )

        return

    if text == "📋 Мои группы":
        groups = await get_groups()

        if not groups:
            await update.message.reply_text("Список пуст")
            return

        msg = "📋 Группы:\n\n"

        for group in groups:
            msg += f"• {group['title']}\n"

        await update.message.reply_text(msg)

        return

    if text == "❌ Удалить группу":
        groups = await get_groups()

        if not groups:
            await update.message.reply_text("Нет групп")
            return

        msg = "Отправьте ID группы для удаления:\n\n"

        for g in groups:
            msg += f"{g['chat_id']} — {g['title']}\n"

        context.user_data["waiting_delete"] = True

        await update.message.reply_text(msg)

        return

    if context.user_data.get("waiting_delete"):
        context.user_data["waiting_delete"] = False

        try:
            chat_id = int(text)

            await remove_group(chat_id)

            await update.message.reply_text(
                "Группа удалена"
            )

        except:
            await update.message.reply_text(
                "Неверный ID"
            )

        return

    if text == "📊 Статистика":
        report = await generate_stats()

        await update.message.reply_text(report)

        return

    context.user_data["pending_text"] = text

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Подтвердить",
                callback_data="confirm_send"
            ),
            InlineKeyboardButton(
                "❌ Отмена",
                callback_data="cancel_send"
            )
        ]
    ])

    await update.message.reply_text(
        "Отправить это во все группы?\n"
        "Напишите ПОДТВЕРЖДАЮ или нажмите кнопку.",
        reply_markup=keyboard
    )


async def confirm_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text != "ПОДТВЕРЖДАЮ":
        return

    text = context.user_data.get("pending_text")

    if not text:
        return

    groups = await get_groups()

    success, failed = await send_to_groups(
        context.bot,
        groups,
        text
    )

    await update.message.reply_text(
        f"Рассылка завершена\n\n"
        f"Успешно: {success}\n"
        f"Ошибок: {failed}"
    )

    context.user_data.pop("pending_text", None)


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    await query.answer()

    if query.data == "cancel_send":
        context.user_data.pop("pending_text", None)

        await query.edit_message_text(
            "Рассылка отменена"
        )

        return

    if query.data == "confirm_send":
        text = context.user_data.get("pending_text")

        if not text:
            await query.edit_message_text(
                "Нет текста"
            )
            return

        groups = await get_groups()

        success, failed = await send_to_groups(
            context.bot,
            groups,
            text
        )

        await query.edit_message_text(
            f"Рассылка завершена\n\n"
            f"Успешно: {success}\n"
            f"Ошибок: {failed}"
        )

        context.user_data.pop("pending_text", None)


async def views_task(application):
    while True:
        await update_views(application.bot)

        await asyncio.sleep(3600)


async def post_init(application):
    asyncio.create_task(
        views_task(application)
    )

    asyncio.create_task(
        weekly_stats_scheduler(application)
    )


async def main():
    await ensure_files()

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        CallbackQueryHandler(callback_handler)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            confirm_text
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    logger.info("Bot started")

    await app.run_polling()


if __name__ == "__main__":
    import asyncio
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()
    )

    app = Application.builder().token(BOT_TOKEN).build()

    app.run_polling()