import logging
from datetime import datetime, timedelta
from random import choice
from typing import Dict

from pymongo.collection import Collection
from telegram import Update, User, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest
from telegram.ext import (
    Updater,
    MessageHandler,
    Filters,
    CallbackContext,
    CallbackQueryHandler,
)

from config import get_config
from db.mongo import get_db
from mode import Mode

MAGIC_NUMBER = "42"
QUARANTINE_TIME = 60
I_AM_TURKISH = [
    "I'm turkish!",
    "Я турок!",
    "私はトルコ人です！",
    "Ја сам Турчин!",
    "men turkman!",
    "ฉันเป็นคนตุรกี!",
    "ຂ້ອຍເປັນຄົນຕຸລະກີ!",
    "Мен түрікпін!",
    "Jeg er tyrkisk!",
    "我是土耳其人！",
    "He turkish ahau!",
]

logger = logging.getLogger(__name__)


class DB:
    def __init__(self, db_name: str):
        self._coll: Collection = get_db(db_name).quarantine

    def add_user(self, user_id: str):
        return (
            self._coll.insert_one(
                {
                    "_id": user_id,
                    "rel_messages": [],
                    "datetime": datetime.now() + timedelta(minutes=QUARANTINE_TIME),
                }
            )
            if self.find_user(user_id) is None
            else None
        )

    def find_user(self, user_id: str):
        return self._coll.find_one({"_id": user_id})

    def find_all_users(self):
        return self._coll.find({})

    def add_user_rel_message(self, user_id: str, message_id: str):
        self._coll.update_one(
            {"_id": user_id}, {"$addToSet": {"rel_messages": message_id}}
        )

    def delete_user(self, user_id: str):
        return self._coll.delete_one({"_id": user_id})

    def delete_all_users(self):
        return self._coll.delete_many({})


db = DB("towel_mode")
mode = Mode(
    mode_name="towel_mode", default=True, off_callback=lambda _: db.delete_all_users()
)


def _is_time_gone(user: Dict) -> bool:
    return user["datetime"] < datetime.now()


def _delete_user_rel_messages(chat_id: int, user_id: str, context: CallbackContext):
    for msg_id in db.find_user(user_id=user_id)["rel_messages"]:
        try:
            context.bot.delete_message(chat_id, msg_id)
        except BadRequest as err:
            logger.info("can't delete msg: %s", err)


@mode.add
def add_towel_mode(upd: Updater, handlers_group: int):
    logger.info("registering towel-mode handlers")
    dp = upd.dispatcher

    dp.add_handler(
        MessageHandler(
            Filters.status_update.new_chat_members, catch_new_user, run_async=True
        ),
        handlers_group,
    )

    dp.add_handler(
        MessageHandler(
            Filters.chat_type.groups & ~Filters.status_update,
            catch_reply,
            run_async=True,
        ),
        handlers_group,
    )

    dp.add_handler(CallbackQueryHandler(i_am_a_turkish_btn, run_async=True), handlers_group)

    upd.job_queue.run_repeating(
        ban_user,
        interval=60,
        first=60,
        context={"chat_id": get_config()["GROUP_CHAT_ID"]},
    )


def quarantine_user(user: User, chat_id: str, context: CallbackContext):
    logger.info("put %s in quarantine", user)
    db.add_user(user.id)

    markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton(choice(I_AM_TURKISH), callback_data=MAGIC_NUMBER)]]
    )

    message_id = context.bot.send_message(
        chat_id,
        f"{user.name} НЕ нажимай на кнопку ниже, чтобы доказать, что ты турок.\n"
        "Просто ответь (reply) на это сообщение, кратко написав о себе.\n"
        "Я буду удалять твои сообщения, пока ты не сделаешь это.\n"
        f"А если не сделаешь, через {QUARANTINE_TIME} минут выкину из чата.\n"
        "Ничего личного, просто боты одолели.\n",
        reply_markup=markup,
    ).message_id

    db.add_user_rel_message(
        user.id,
        message_id,
    )

    if user.id == context.bot.get_me().id:
        message_id = context.bot.send_message(
            chat_id,
            "Я простой бот-кебаб, в-основном занимаюсь тем, что бросаю полотенца в новичков.\n",
            reply_to_message_id=message_id,
        ).message_id

        db.delete_user(user_id=user["_id"])
        context.bot.send_message(
            chat_id, "Добро пожаловать в дом на горе!", reply_to_message_id=message_id
        )


def catch_new_user(update: Update, context: CallbackContext):
    for user in update.message.new_chat_members:
        quarantine_user(user, update.effective_chat.id, context)


def catch_reply(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = db.find_user(user_id)
    if user is None:
        return

    if (
        update.effective_message.reply_to_message is not None
        and update.effective_message.reply_to_message.from_user.id
        == context.bot.get_me().id
    ):

        _delete_user_rel_messages(update.effective_chat.id, user_id, context)
        db.delete_user(user_id=user["_id"])

        update.message.reply_text("Добро пожаловать в дом на горе!")
    else:
        context.bot.delete_message(
            update.effective_chat.id, update.effective_message.message_id, 10
        )


def quarantine_filter(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = db.find_user(user_id)
    if user is not None:
        context.bot.delete_message(
            update.effective_chat.id, update.effective_message.message_id, 10
        )


def i_am_a_turkish_btn(update: Update, context: CallbackContext):
    user = update.effective_user
    query = update.callback_query

    if query.data == MAGIC_NUMBER:
        if db.find_user(user.id) is not None:
            msg = f"{user.name}, попробуй прочитать сообщение от бота внимательней!!!"
        else:
            msg = f"-5 пунктов социального рейтинга, {user.name}"

        context.bot.answer_callback_query(query.id, msg, show_alert=True)


def ban_user(context: CallbackContext):
    chat_id = context.bot.get_chat(chat_id=context.job.context["chat_id"]).id
    logger.debug("get chat.id: %s", chat_id)

    for user in db.find_all_users():
        if _is_time_gone(user):
            try:
                context.bot.kick_chat_member(chat_id, user["_id"])
                _delete_user_rel_messages(chat_id, user["_id"], context)
            except BadRequest as err:
                logger.error("can't ban user %s, because of: %s", user, err)

            db.delete_user(user["_id"])

            logger.info("user banned: %s", user)
