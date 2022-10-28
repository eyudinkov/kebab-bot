import logging

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import Updater, CommandHandler, CallbackContext

from filters import trusted_filter, admin_filter

logger = logging.getLogger(__name__)


def add_kebab(upd: Updater, handlers_group: int):
    logger.info("registering kebab handlers")
    dp = upd.dispatcher
    dp.add_handler(
        CommandHandler(
            "kebab",
            kebab,
            filters=trusted_filter | admin_filter,
            run_async=True,
        ),
        handlers_group,
    )


def kebab(update: Update, context: CallbackContext):
    text = " ".join(context.args)
    chat_id = update.effective_chat.id

    try:
        context.bot.delete_message(chat_id, update.effective_message.message_id)
    except BadRequest as err:
        logger.info("can't delete msg: %s", err)

    if text:
        context.bot.send_message(chat_id, text)
