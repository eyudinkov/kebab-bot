import logging
from datetime import datetime
from functools import reduce
from typing import Dict, List

from pymongo.collection import Collection
from telegram.ext import Updater, CommandHandler, CallbackContext

from mode import Mode
from db.mongo import get_db

topics_coll: Collection = get_db('since_mode').topics
logger = logging.getLogger(__name__)
mode = Mode(mode_name="since_mode", default=True, pin_info_msg=False)


@mode.add
def add_since_mode(upd: Updater, handlers_group: int):
    logger.info("register since-mode handlers")
    dp = upd.dispatcher
    dp.add_handler(
        CommandHandler(
            "since",
            since_callback,
            run_async=True,
        ),
        handlers_group,
    )
    dp.add_handler(
        CommandHandler(
            "since_list",
            since_list_callback,
            run_async=True,
        ),
        handlers_group,
    )


def _get_topic(t: str) -> Dict:
    topic = topics_coll.find_one({"topic": t})
    logger.info("topic from db for title %s is %s", t, topic)

    return (
        topic
        if topic is not None
        else {"topic": t.lower(), "since_datetime": datetime.now(), "count": 1}
    )


def _get_delta_days(t: datetime) -> str:
    d = datetime.now() - t
    return f"{d.days}"


def _update_topic(t: Dict):
    if "_id" in t:
        topics_coll.update_one(
            {"topic": t["topic"]},
            {"$inc": {"count": 1}, "$set": {"since_datetime": datetime.now()}},
        )
    else:
        topics_coll.insert_one(t)


def since_callback(update, context):
    topic_title = " ".join(context.args)
    if len(topic_title) == 0:
        logging.warning("topic is empty")
        update.message.reply_text("топик пуст 😢")
        return

    if len(topic_title) > 64:
        logging.warning("topic too long")
        update.message.reply_text("топик слишком длинный 😢")
        return

    current_topic = _get_topic(topic_title)
    update.message.reply_text(
        f"{_get_delta_days(current_topic['since_datetime'])} дней без «{current_topic['topic']}»! "
        f"Обсуждали {current_topic['count']} раз\n",
    )

    _update_topic(current_topic)


def _get_all_topics(limit: int) -> List[Dict]:
    return list(topics_coll.find({}).sort("-count").limit(limit))


def since_list_callback(update: Updater, context: CallbackContext):
    ts = reduce(
        lambda acc, el: acc
        + f"{_get_delta_days(el['since_datetime'])} дней без «{el['topic']}»! "
        f"Обсуждали {el['count']} раз\n",
        _get_all_topics(20),
        "",
    )
    update.message.reply_text(ts or "список топиков пуст 😢")
