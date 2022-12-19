import logging
import cloudscraper
import math

from bs4 import BeautifulSoup
from datetime import datetime, timedelta

from telegram import Update, Message
from telegram.ext import Updater, CommandHandler, CallbackContext
from pymongo.collection import Collection

from mode import cleanup_queue_update

from config import get_config
from db.mongo import get_db
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)
scraper = cloudscraper.create_scraper()
update_delta = timedelta(minutes=10)


def _get_now():
    return datetime.now()


class DB:
    def __init__(self, db_name: str):
        self._coll: Collection = get_db(db_name).namaz

    def add_times(self, id: str):
        return (
            self._coll.insert_one(
                {
                    "_id": id,
                    "today": [],
                    "tomorrow": [],
                    "message_id": None,
                    "start_minute": None,
                }
            )
            if self.find_times(id) is None
            else None
        )

    def find_times(self, id: str):
        return self._coll.find_one({"_id": id})

    def find_all_times(self):
        return self._coll.find({})

    def update_message_id(self, id: str, message_id: str):
        self._coll.update_one(
            {"_id": id}, {"$set": {"message_id": message_id}}
        )

    def update_start_minute(self, id: str, minute: str):
        self._coll.update_one(
            {"_id": id}, {"$set": {"start_minute": minute}}
        )

    def add_times_rel(self, id: str, today: List[str], tomorrow: List[str]):
        self._coll.update_one(
            {"_id": id}, {"$set": {"today": today, "tomorrow": tomorrow}}
        )

    def delete_times(self, id: str):
        return self._coll.delete_one({"_id": id})

    def drop_times(self):
        return self._coll.drop()


db = DB("namaz")


def add_namaz(upd: Updater, handlers_group: int):
    logger.info("registering namaz handlers")

    dp = upd.dispatcher

    dp.add_handler(
        CommandHandler(
            "namaz",
            namaz,
            run_async=True,
        ),
        handlers_group,
    )

    upd.job_queue.run_repeating(
        update_datas,
        interval=60,
        first=10,
        context={"chat_id": get_config()["GROUP_CHAT_ID"]},
    )

    upd.job_queue.run_repeating(
        update_notifications,
        interval=1,
        first=30,
        context={"chat_id": get_config()["GROUP_CHAT_ID"]},
    )


def _plural(x):
    last_two_digits = x % 100
    tens = last_two_digits // 10
    ones = last_two_digits % 10

    if tens == 1:
        return 2

    if ones == 1:
        return 0

    if ones >= 2 and ones <= 4:
        return 1

    return 2


def _show_plural(value, list):
    suffix = list[_plural(value)]
    return "{0} {1}".format(value, suffix)


def _nearest(items, pivot, alternative_date=None):
    items = [d for d in sorted(items) if d > pivot]
    return items[0] if items else alternative_date


def _transform_to_dates(elements, date):
    return [datetime.strptime(f"{date} {element}:00", "%d.%m.%Y %H:%M:%S") for element in elements]


def _get_time_row(soup, date):
    return list(
        filter(
            lambda x: (x != date and x != "\n"),
            [element.text for element in soup.find(
                "td", text=date).parent.children]
        )
    )


def _is_time_gone(times: Dict) -> bool:
    return times["_id"] != _get_now().strftime("%d.%m.%Y")


def _get_date_strs():
    now = _get_now()
    today_str = now.strftime("%d.%m.%Y")
    tomorrow_str = (now + timedelta(days=1)).strftime("%d.%m.%Y")

    return [today_str, tomorrow_str]


def _parse_page():
    try:
        page = scraper.get("https://namazvakitleri.diyanet.gov.tr/en-US/9228/prayer-time-for-finike")
        soup = BeautifulSoup(page.content, "html.parser")

        today_str, tomorrow_str = _get_date_strs()

        today_times = _get_time_row(soup, today_str)
        tomorrow_times = _get_time_row(soup, tomorrow_str)

        db.add_times(str(today_str))
        db.add_times_rel(str(today_str), today_times, tomorrow_times)

    except Exception as err:
        logger.error("error while updating datas: %s", err)


def update_datas(context: CallbackContext):
    chat_id = context.bot.get_chat(chat_id=context.job.context["chat_id"]).id

    logger.info("get chat.id: %s", chat_id)

    times = db.find_all_times()

    if len(list(times)) > 0:
        for time in db.find_all_times():
            logger.info("get time object: %s", time)
            if _is_time_gone(time):

                logger.info("times is gone, deleting")

                db.delete_times(time["_id"])

                _parse_page()
    else:
        _parse_page()


def _remove_message(context: CallbackContext):
    message = context.job.context["message"]
    id = context.job.context["id"]

    db.update_message_id(id, None)
    db.update_start_minute(id, None)

    message.delete()


def update_notifications(context: CallbackContext):
    chat_id = context.bot.get_chat(chat_id=context.job.context["chat_id"]).id
    times = db.find_all_times()

    if len(list(times)) > 0:
        next_pray_time = _get_next_pray_delta()
        id = str(_get_date_strs()[0])

        message_id = db.find_times(id)["message_id"]
        start_minute = db.find_times(id)["start_minute"]
        current_minute = str(math.ceil(next_pray_time.seconds / 60))

        time = _show_time(next_pray_time, False)
        text = f"⚠️ !!! Внимание !!! ⚠️ \nДо намаза осталось {time}"

        if isinstance(next_pray_time, timedelta):
            if next_pray_time.seconds <= update_delta.seconds:
                if message_id is None:
                    message: Optional[Message] = context.bot.send_message(chat_id, text)

                    db.update_message_id(id, message.message_id)
                    db.update_start_minute(id, current_minute)

                    context.job_queue.run_once(
                        _remove_message,
                        next_pray_time.seconds,
                        context={
                            "message": message,
                            "id": id,
                        }
                    )
                elif start_minute != current_minute:
                    message_id_after_update = db.find_times(id)["message_id"]
                    if message_id_after_update is not None and current_minute != '0':
                        context.bot.edit_message_text(text, chat_id, message_id=message_id_after_update)
                        db.update_start_minute(id, current_minute)


def namaz(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    namaz_result = _get_namaz()

    logger.info("get namaz: %s", namaz_result)

    result: Optional[Message] = context.bot.send_message(chat_id, namaz_result)

    cleanup_queue_update(
        context.job_queue,
        update.message,
        result,
        120,
        remove_cmd=True,
        remove_reply=False,
    )


def _get_next_pray_delta():
    now = _get_now()

    try:
        today_str = now.strftime("%d.%m.%Y")

        times = db.find_times(today_str)

        logger.info("get times: %s", times)

        if times is not None:
            today_str, tomorrow_str = _get_date_strs()

            today_times = _transform_to_dates(times["today"], today_str)
            tomorrow_times = _transform_to_dates(times["tomorrow"], tomorrow_str)

            next_pray_time = _nearest(today_times, now, tomorrow_times[0])
            delta = next_pray_time - now

            return delta

    except Exception as err:
        logger.error("error while getting next pray time: %s", err)
        return err


def _show_time(delta: timedelta, show_seconds_and_hours: bool = True):
    h, m, s = str(
        timedelta(seconds=delta.seconds)).split(":")
    hours = _show_plural(int(h), ["час", "часа", "часов"])
    minutes = _show_plural(int(m), ["минута", "минуты", "минут"])
    seconds = _show_plural(int(s), ["секунда", "секунды", "секунд"])

    return show_seconds_and_hours and f"{hours} {minutes} {seconds}" or f"{minutes}"


def _get_namaz():

    delta = _get_next_pray_delta()

    logger.info("get delta: %s", delta)

    if isinstance(delta, timedelta):
        time = _show_time(delta)

        if time:
            return f"До следующего намаза осталось: {time}"
        else:
            return "Не получилось получить время намаза 😥"

    return delta
