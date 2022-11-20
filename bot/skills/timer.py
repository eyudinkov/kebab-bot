import logging
from datetime import datetime

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import Updater, CommandHandler, CallbackContext
from typing import List
from time import sleep

logger = logging.getLogger(__name__)

def add_timer(upd: Updater, handlers_group: int):
	logger.info("registering timer handler")
	dp = upd.dispatcher
	dp.add_handler(CommandHandler("timer", timer, run_async=True), handlers_group)


def timer(update: Update, context: CallbackContext):
	logger.info("making timer")

	minutes = 0

	try:
		minutes = int(context.args[0])
	except:
		context.bot.send_message(
      		update.effective_chat.id,
        	"Не пиши глупости, укажи нормальное значение для таймера"
        )

		return

	SEC_IN_MINUTE = 60
	send_text = "Стрелочка вращается, запустил таймер на {} мин".format(minutes)

	context.bot.send_message(update.effective_chat.id, send_text)
	sleep(minutes * SEC_IN_MINUTE)
	context.bot.send_message(update.effective_chat.id, "Стрелочка вернулась на место")
