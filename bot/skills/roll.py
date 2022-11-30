import logging
import os
from datetime import datetime, timedelta
from random import randint
from tempfile import gettempdir
from threading import Lock
from typing import List, Optional, Tuple, Dict
from uuid import uuid4

import re

import pymongo
from PIL import Image, ImageDraw, ImageFont
from pymongo.collection import Collection
from telegram import Update, User, Message, ChatMember
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext
from telegram.ext.filters import Filters
from telegram.error import BadRequest

from db.mongo import get_db
from filters import admin_filter
from mode import cleanup_queue_update
from skills.mute import mute_user_for_time

logger = logging.getLogger(__name__)

MUTE_MINUTES = 16 * 60
NUM_BULLETS = 6
LIMIT_FOR_IMAGE = 25
FONT = "firacode.ttf"


class DB:
    def __init__(self, db_name: str):
        self._coll: Collection = get_db(db_name).leaders

    def find_all(self):
        return list(self._coll.find({}).sort("total_time_in_club", pymongo.DESCENDING))

    def find(self, user_id: str):
        return self._coll.find_one({"_id": user_id})

    def add(self, user: User):
        now: datetime = datetime.now()
        return self._coll.insert_one(
            {
                "_id": user.id,
                "meta": user.to_dict(),
                "shot_counter": 0,
                "miss_counter": 0,
                "dead_counter": 0,
                "total_time_in_club": timedelta().seconds,
                "first_shot": now,
                "last_shot": now,
            }
        )

    def dead(self, user_id: str, mute_min: int):
        self._coll.update_one(
            {"_id": user_id},
            {
                "$inc": {
                    "shot_counter": 1,
                    "dead_counter": 1,
                    "total_time_in_club": mute_min * 60,
                },
                "$set": {"last_shot": datetime.now()},
            },
        )

    def miss(self, user_id: str):
        self._coll.update_one(
            {"_id": user_id},
            {
                "$inc": {"shot_counter": 1, "miss_counter": 1},
                "$set": {"last_shot": datetime.now()},
            },
        )

    def remove(self, user_id: str):
        self._coll.delete_one({"_id": user_id})

    def remove_all(self):
        self._coll.delete_many({})


_db = DB(db_name="roll")

MEME_REGEX = re.compile(r"\/[rрp][оo0][1lл]{2}", re.IGNORECASE)


def add_roll(upd: Updater, handlers_group: int):
    logger.info("registering roll handlers")
    dp = upd.dispatcher
    dp.add_handler(MessageHandler(Filters.dice, roll), handlers_group)
    dp.add_handler(
        MessageHandler(Filters.regex(MEME_REGEX), roll, run_async=True), handlers_group
    )
    dp.add_handler(
        CommandHandler(
            "wipe_me",
            wipe_me,
            run_async=True,
        ),
        handlers_group,
    )
    dp.add_handler(
        CommandHandler(
            "leaders",
            show_leaders,
            filters=admin_filter,
            run_async=True,
        ),
        handlers_group,
    )
    dp.add_handler(
        CommandHandler(
            "top",
            show_active,
            run_async=True,
        ),
        handlers_group,
    )
    dp.add_handler(
        CommandHandler(
            "wipe_leaders",
            wipe_leaders,
            filters=admin_filter,
            run_async=True,
        ),
        handlers_group,
    )


barrel_lock = Lock()


def _reload(context: CallbackContext) -> List[bool]:
    empty, bullet = False, True
    barrel: List[bool] = [empty] * NUM_BULLETS
    lucky_number = randint(0, NUM_BULLETS - 1)
    barrel[lucky_number] = bullet
    context.chat_data["barrel"] = barrel

    return barrel


def get_miss_string(shots_remain: int) -> str:
    s = ["😕", "😟", "😥", "😫", "😱"]
    misses = ["🔘"] * (NUM_BULLETS - shots_remain)
    chances = ["⚪️"] * shots_remain
    barrel_str = "".join(misses + chances)
    h = get_mute_minutes(shots_remain - 1) // 60
    return f"{s[NUM_BULLETS - shots_remain - 1]}🔫 МИМО! Попытка: {barrel_str}, {h} час."


def get_mute_minutes(shots_remain: int) -> int:
    return MUTE_MINUTES * (NUM_BULLETS - shots_remain)


def _shot(context: CallbackContext) -> Tuple[bool, int]:
    with barrel_lock:
        barrel = context.chat_data.get("barrel")
        if barrel is None or len(barrel) == 0:
            barrel = _reload(context)

        logger.debug("barrel before shot: %s", barrel)

        fate = barrel.pop()
        context.chat_data["barrel"] = barrel
        shots_remained = len(barrel)
        if fate:
            _reload(context)

    return fate, shots_remained


def get_username(h: Dict) -> str:
    m = h["meta"]
    username = m.get("username")
    fname = m.get("first_name")
    lname = m.get("last_name")
    return (
        username
        or " ".join(filter(lambda x: x is not None, [fname, lname]))
        or "unknown"
    )


JPEG = "JPEG"
EXTENSION = ".jpg"
COLOR = "white"
MODE = "L"
FONT_SIZE = 12


def _create_empty_image(image_path, limit):
    width = 480
    line_multi = 1
    header_height = 30
    line_px = FONT_SIZE * line_multi
    height = int((limit * line_px * 1.5) + header_height)
    size = (width, height)
    logger.info("Creating image")
    image = Image.new(MODE, size, COLOR)
    logger.info("Saving image")
    try:
        image.save(image_path, JPEG)
        logger.info("Empty image saved")
    except (ValueError, OSError) as err:
        logger.error("Error during image saving, error: %s", err)
        return None
    return image


def _add_text_to_image(text, image_path):
    logger.info("Adding text to image")
    image = Image.open(image_path)
    logger.info("Getting font")
    font_path = os.path.join("fonts", FONT)
    font = ImageFont.truetype(font_path, FONT_SIZE)
    logger.info("Font %s has been found", FONT)
    draw = ImageDraw.Draw(image)
    position = (45, 0)
    draw.text(xy=position, text=text, font=font)
    try:
        image.save(image_path, JPEG)
        logger.info("Image with text saved")
    except (ValueError, OSError) as err:
        logger.error("Error during image with text saving, error: %s", err)
        os.remove(image_path)
        return None
    return image


def from_text_to_image(text, limit):
    limit = max(limit, LIMIT_FOR_IMAGE)
    logger.info("Getting temp dir")
    tmp_dir = gettempdir()
    file_name = str(uuid4())
    image_path = f"{tmp_dir}/{file_name}{EXTENSION}"
    _create_empty_image(image_path, limit)
    _add_text_to_image(text, image_path)
    image = open(image_path, "rb")
    return image, image_path


def show_leaders(update: Update, context: CallbackContext):
    board = (
        f"{'Таблица главных кебабов'.center(52)}\n"
        f"{''.rjust(51, '=')}\n"
        f"{'время в клубе'.center(18)} "
        f"| {'попытки'.center(8)} "
        f"| {'смерти'.center(6)} "
        f"| {'кебаб'.center(11)} "
        f"\n"
        f"{''.ljust(18, '-')} + {''.ljust(8, '-')} + {''.ljust(6, '-')} + {''.ljust(11, '-')}\n"
    )

    leaders = _db.find_all()
    leaders_length = len(leaders)

    for leader in leaders:
        username = get_username(leader)
        board += (
            f"{str(timedelta(seconds=(leader['total_time_in_club']))).ljust(18)} "
            f"| {str(leader['shot_counter']).ljust(8)} "
            f"| {str(leader['dead_counter']).ljust(6)} "
            f"| {username.ljust(15)}\n"
        )

    board += f"{''.rjust(51, '-')}"
    try:
        board_image, board_image_path = from_text_to_image(board, leaders_length)
    except (ValueError, RuntimeError, OSError) as err:
        logger.error("Cannot get image from text, leaders error: %s", err)
        return

    result: Optional[Message] = None

    if leaders_length <= LIMIT_FOR_IMAGE:
        result = context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=board_image,
            disable_notification=True,
        )
    else:
        result = context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=board_image,
            disable_notification=True,
        )

    cleanup_queue_update(
        context.job_queue,
        update.message,
        result,
        600,
        remove_cmd=True,
        remove_reply=False,
    )

    os.remove(board_image_path)


def show_active(update: Update, context: CallbackContext):
    leaders = _db.find_all()

    message = "Никто не пришёл на фан встречу 😢"

    restricted = []

    for leader in leaders:
        try:
            chat_member = context.bot.get_chat_member(
                update.effective_chat.id, leader.get("_id")
            )
            if chat_member.status == ChatMember.RESTRICTED:
                restricted.append(leader)

        except BadRequest:
            logger.error("can't get user %s, skip", leader)

    if len(restricted) > 0:
        message = "Лидеры ☠️:\n"

        for leader in restricted:
            name = get_username(leader)
            number = sum([ord(c) for c in name])
            emoji = chr(ord("😀") + number % 75)
            message += f"{emoji} {name} \n"

    result = context.bot.send_message(update.effective_chat.id, message)

    cleanup_queue_update(
        context.job_queue,
        update.message,
        result,
        120,
        remove_cmd=True,
        remove_reply=False,
    )


def roll(update: Update, context: CallbackContext):
    if update.message is None:
        return

    user: User = update.effective_user
    result: Optional[Message] = None
    existing_user = _db.find(user_id=user.id)
    if existing_user is None:
        _db.add(user=user)

    is_shot, shots_remained = _shot(context)
    shot_result = "he is dead!" if is_shot else "miss!"
    logger.info(
        "user: %s[%s] is rolling and... %s", user.full_name, user.id, shot_result
    )

    if is_shot:
        mute_min = get_mute_minutes(shots_remained)
        result = context.bot.send_message(
            update.effective_chat.id,
            f"💥 бум! {user.full_name} 😵 [{mute_min // 60} час. отдыха]",
        )

        mute_user_for_time(update, context, user, timedelta(minutes=mute_min))
        _db.dead(user.id, mute_min)
    else:

        _db.miss(user.id)

        result = context.bot.send_message(
            update.effective_chat.id,
            f"{user.full_name}: {get_miss_string(shots_remained)}",
        )
    cleanup_queue_update(
        context.job_queue,
        update.message,
        result,
        120,
        remove_cmd=True,
        remove_reply=False,
    )


def wipe_me(update: Update, context: CallbackContext):
    user: User = update.effective_user

    _db.remove(user.id)
    logger.info("%s was removed from DB", user.full_name)
    result = update.message.reply_text("ок, бумер 😒", disable_notification=True)

    cleanup_queue_update(
        context.job_queue,
        update.message,
        result,
        120,
        remove_cmd=True,
        remove_reply=False,
    )


def wipe_leaders(update: Update, context: CallbackContext):
    _db.remove_all()
    logger.info("all leaders were removed from DB")
    result = update.message.reply_text("👍", disable_notification=True)

    cleanup_queue_update(
        context.job_queue,
        update.message,
        result,
        120,
        remove_cmd=True,
        remove_reply=False,
    )
