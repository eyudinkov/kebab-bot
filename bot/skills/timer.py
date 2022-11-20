import logging
from telegram import Update, Message
from telegram.ext import Updater, CommandHandler, CallbackContext

from mode import cleanup_queue_update

from typing import Optional

logger = logging.getLogger(__name__)

SEC_IN_MINUTE = 60


def add_timer(upd: Updater, handlers_group: int):
    logger.info("registering timer handler")

    dp = upd.dispatcher

    dp.add_handler(CommandHandler("timer", timer, run_async=True), handlers_group)


def timer(update: Update, context: CallbackContext):
    logger.info("making timer")

    try:
        minutes = int(" ".join(context.args))
        message: Optional[Message] = update.message.reply_text(
            f"Стрелочка вращается, запустил таймер на {minutes} мин", disable_notification=False)
        remaining_time = SEC_IN_MINUTE * minutes

        context.job_queue.run_once(
            lambda _: context.bot.send_message(update.effective_chat.id, "Стрелочка вернулась на место"),
            remaining_time
        )

        cleanup_queue_update(
            context.job_queue,
            update.message,
            message,
            remaining_time,
            remove_cmd=True,
            remove_reply=True,
        )

    except Exception as err:
        logger.error("can't create timer: %s", err)
        context.bot.send_message(update.effective_chat.id, "Не пиши глупости, укажи нормальное значение для таймера")
        update.message.delete()
