import logging
from datetime import datetime
from typing import Optional
from random import choice

from pymongo.collection import Collection
from telegram import Update, User
from telegram.ext import Updater, CommandHandler, CallbackContext

from db.mongo import get_db
from filters import admin_filter
from mode import Mode, ON, cleanup_queue_update

from skills.roll import HONORED_EMOJIS, get_username

logger = logging.getLogger(__name__)

mode = Mode(mode_name="trusted_mode", default=ON)


class DB:
    def __init__(self, db_name: str):
        self._coll: Collection = get_db(db_name).users

    def get_all_users(self):
        return self._coll.find({})

    def get_user(self, user_id: int) -> Optional[dict]:
        return self._coll.find_one(
            {
                "_id": user_id,
            }
        )

    def trust(self, user: User, admin_id: str):
        self._coll.insert_one(
            {
                "_id": user.id,
                "by": admin_id,
                "datetime": datetime.now(),
                "meta": user.to_dict()
            }
        )

    def untrust(self, user_id):
        self._coll.delete_one({"_id": user_id})

    def drop_all(self):
        self._coll.drop()


_db = DB(db_name="trusted")


def add_trusted_mode(upd: Updater, handlers_group: int):
    logger.info("register trusted-mode handlers")
    dp = upd.dispatcher
    dp.add_handler(
        CommandHandler(
            "trust",
            trust_callback,
            filters=admin_filter,
            run_async=True,
        ),
        handlers_group,
    )

    dp.add_handler(
        CommandHandler(
            "untrust",
            untrust_callback,
            filters=admin_filter,
            run_async=True,
        ),
        handlers_group,
    )

    dp.add_handler(
        CommandHandler(
            "trusted_list",
            trusted_list,
            run_async=True,
        ),
        handlers_group,
    )


def _get_user_and_admin(update):
    user: User = update.message.reply_to_message.from_user
    admin: User = update.effective_user
    chat_id = update.effective_chat.id
    return user, chat_id, admin


def trust_callback(update: Update, context: CallbackContext):
    user, chat_id, admin = _get_user_and_admin(update)

    if user and admin and chat_id:
        if _db.get_user(user.id) is not None:
            msg = f"{user.name} уже настоящий кебаб 👍"
        else:
            _db.trust(user, admin.id)
            msg = f"🪄 {user.name} теперь ты настоящий кебаб!"

        context.bot.send_message(chat_id, msg)


def untrust_callback(update: Update, context: CallbackContext):
    user, chat_id, _ = _get_user_and_admin(update)

    if user and chat_id:
        _db.untrust(user.id)
        context.bot.send_message(chat_id, f"{user.name} больше не настоящий кебаб 🖕")


def trusted_list(update: Updater, context: CallbackContext):
    users = _db.get_all_users()
    message = "Нет настоящих кебабов 😢"

    if len(list(users)) > 0:
        message = "Список настоящих кебабов:\n"
        
        for user in _db.get_all_users():
            message += f"{choice(HONORED_EMOJIS)} {get_username(user)} \n"

    result = context.bot.send_message(update.effective_chat.id, message)

    cleanup_queue_update(
        context.job_queue,
        update.message,
        result,
        120,
        remove_cmd=True,
        remove_reply=False,
    )
