import logging

from telegram import Update
from telegram.ext import CommandHandler, Updater, CallbackContext

logger = logging.getLogger(__name__)


def add_core(upd: Updater, core_handlers_group: int):
    logger.info("register smile-mode handlers")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("start", start, run_async=True), core_handlers_group)
    dp.add_handler(CommandHandler("help", help_, run_async=True), core_handlers_group)


def start(update: Update, _: CallbackContext):
    update.message.reply_text(
        "Мирабулички всем в этом чате 🍢\n"
    )


def help_(update: Update, _: CallbackContext):
    update.message.reply_text(
        "Бот должен быть админом со всеми разрешениями\n\n"
        "Для админов чата:\n\n"
        "SmileMode: позволяет только не текстовые сообщения (stickers, gif)\n"
        "`/smile_mode_on` – smile mode ON\n"
        "`/smile_mode_off` – smile mode OFF\n"
        "\n"
        "Version: просто версия\n"
        "`/version` – показывает текущую версию бота\n"
        "Для всех:\n\n"
        "SinceMode: показывает как давно обсуждали тему\n"
        "`/since TOPIC` – обновляет счетчик\n"
        "`/since_list` – список всех обсуждений\n"
        "Дефолтные режимы:\n"
        "TowelMode: бросает полотенце и ждет описание от нового участника\n"
        "TowelMode включен по умолчанию\n\n"
        "\n\n"
    )


def error(update: Update, context: CallbackContext):
    logger.warning('Update "%s" caused error "%s"', update, context.error)
