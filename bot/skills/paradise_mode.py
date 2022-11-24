import logging

from telegram import Update, User
from telegram.error import BadRequest, TelegramError
from telegram.ext import MessageHandler, Filters, Updater, CallbackContext

from mode import Mode, OFF

logger = logging.getLogger(__name__)

mode = Mode(mode_name="paradise_mode", default=OFF, pin_info_msg=True)


@mode.add
def add_paradise_mode(upd: Updater, handlers_group: int):
    logger.info("registering paradise-mode handlers")

    dp = upd.dispatcher

    dp.add_handler(
        MessageHandler(~Filters.status_update, paradise, run_async=True),
        handlers_group,
    )


def paradise(update: Update, context: CallbackContext):
    text = update.message["text"]
    user: User = update.effective_user
    chat_id = update.effective_chat.id

    try:
        context.bot.delete_message(chat_id, update.effective_message.message_id)
    except (BadRequest, TelegramError) as err:
        logger.info("can't delete msg: %s", err)

    context.bot.send_message(
        chat_id, f"🌈 Райское сообщение от {user.full_name}: {text}"
    )
