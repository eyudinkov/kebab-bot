import logging
from telegram import Update, Message
from telegram.ext import Updater, CommandHandler, CallbackContext

from mode import cleanup_queue_update

from typing import Optional

logger = logging.getLogger(__name__)
sec_in_minutes = 60


def add_timer(upd: Updater, handlers_group: int):
    logger.info("registering timer handler")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("timer", timer, run_async=True), handlers_group)


def alarm(context: CallbackContext):
    job_context = context.job.context

    job_context["cmd"].delete()
    job_context["message"].delete()

    message: Optional[Message] = context.bot.send_message(job_context["chat_id"], "Стрелочка вернулась на место")

    cleanup_queue_update(
        context.job_queue,
        None,
        message,
        30,
    )


def timer(update: Update, context: CallbackContext):
    try:
        minutes = int(" ".join(context.args))
        message: Optional[Message] = update.message.reply_text(
            f"Стрелочка вращается, запустил таймер на {minutes} мин", disable_notification=False
        )
        cmd = update.message

        context.job_queue.run_once(
            alarm,
            sec_in_minutes * minutes,
            context={
                "chat_id": update.effective_chat.id,
                "cmd": cmd,
                "message": message
            }
        )

    except Exception as err:
        logger.info("can't create timer: %s", err)
        context.bot.send_message(update.effective_chat.id, "Не пиши глупости, укажи нормальное значение для таймера")
        cmd.delete()
