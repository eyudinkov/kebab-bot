import logging

from telegram import Update
from telegram.ext import MessageHandler, Filters, Updater, CallbackContext

from mode import Mode, OFF

logger = logging.getLogger(__name__)

mode = Mode(mode_name="smile_mode", default=OFF, pin_info_msg=True)


@mode.add
def add_smile_mode(upd: Updater, handlers_group: int):
    logger.info("registering smile-mode handlers")
    dp = upd.dispatcher
    dp.add_handler(
        MessageHandler(~Filters.sticker & ~Filters.animation, smile, run_async=True),
        handlers_group,
    )


def smile(update: Update, context: CallbackContext):
    logger.debug("remove msg: %s", update.effective_message)
    context.bot.delete_message(
        update.effective_chat.id, update.effective_message.message_id, 10
    )
