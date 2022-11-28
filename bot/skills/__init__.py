import logging
from typing import List, Dict, Callable, Tuple

import toml
from telegram import Update
from telegram.ext import CommandHandler, Updater, CallbackContext

from filters import admin_filter
from mode import cleanup_queue_update
from skills.ban import add_ban
from skills.banme import add_banme
from skills.core import add_core
from skills.length import add_length
from skills.mute import add_mute
from skills.kebab import add_kebab
from skills.roll import add_roll
from skills.since_mode import add_since_mode
from skills.smile_mode import add_smile_mode
from skills.still import add_still
from skills.towel_mode import add_towel_mode
from skills.trusted_mode import add_trusted_mode
from skills.namaz import add_namaz
from skills.timer import add_timer
from skills.paradise_mode import add_paradise_mode
from skills.kek_mode import add_kek_mode
from skills.profanity_mode import add_profanity_mode

logger = logging.getLogger(__name__)

def _add_version(upd: Updater, version_handlers_group: int):
    logger.info("register version handlers")
    dp = upd.dispatcher
    dp.add_handler(
        CommandHandler(
            "version",
            _version,
            filters=admin_filter,
            run_async=True,
        ),
        version_handlers_group,
    )


def _get_version_from_pipfile() -> str:
    with open("Pipfile", "r") as pipfile:
        toml_dict = toml.loads(pipfile.read())
    version = toml_dict["description"][0]["version"]
    return version


def _version(update: Update, context: CallbackContext):
    version = _get_version_from_pipfile()

    logger.info("current ver.: %s", version)

    chat_id = update.effective_chat.id

    result = context.bot.send_message(
        chat_id,
        f"version.:{version}\n\n" f"{_get_skills_hints(skills)}",
    )

    cleanup_queue_update(
        context.job_queue,
        update.message,
        result,
        120,
    )


def _make_skill(add_handlers: Callable, name: str, hint: str) -> Dict:
    return {"name": name, "add_handlers": add_handlers, "hint": hint}


skills: List[Dict] = [
    _make_skill(add_core, "core", " core"),
    _make_skill(_add_version, "😎 version", " версия"),
    _make_skill(add_still, "🍢 still", "ты же помнишь это?"),
    _make_skill(add_mute, "🤭 mute", " заблокировать на N минут"),
    _make_skill(add_roll, "🔫 roll", " испытать удачу?"),
    _make_skill(add_banme, "⚔️ banme", " commit sudoku"),
    _make_skill(add_ban, "🔨 ban!", " ban🔨 ban🔨 ban🔨"),
    _make_skill(add_kebab, "🍢 kebab", " сделать кебаб?"),
    _make_skill(add_length, "🍆 length", " длина твоего инструмента"),
    _make_skill(add_namaz, "🙏 namaz", " получить время намаза"),
    _make_skill(add_trusted_mode, "🍢 список доверенных кебабов", " настоящий ли ты кебаб?"),
    _make_skill(add_smile_mode, "🍢 smile mode", " только стикеры и картинки"),
    _make_skill(add_since_mode, "🛠 since mode", " в разработке"),
    _make_skill(add_paradise_mode, "🌈 paradise mode", " еще один день в раю"),
    _make_skill(add_kek_mode, "🤪 kek mode", " kek?"),
    _make_skill(add_profanity_mode, "🔨 не ругайся!", " поаккуратнее с языком молодой человек"),
    _make_skill(add_towel_mode, "🧼 towel mode", " anti kebab"),
    _make_skill(add_timer, 'timer', " тик-так")
]

commands_list: List[Tuple[str, str]] = [
    ("kebab", "сделать кебаб?"),
    ("mute", "🤭 заблокировать на N минут"),
    ("unmute", "😎 разблокировать пользователя"),
    ("leaders", "🏅 показать лидеров"),
    ("wipe_leaders", "👠 стереть всю историю"),
    ("top", "показать активных кебабов"),
    ("trust", "🍢 сделать кебабом"),
    ("untrust", "🖕"),
    ("trusted_list", "🍢 список доверенных кебабов"),
    ("ban", "ban🔨 ban🔨 ban🔨"),
    ("roll", "испытать удачу"),
    ("still", "ты же помнишь это?"),
    ("banme", "commit suicide"),
    ("version", "показать версию"),
    ("wipe_me", "👩🏻‍🦼 стереть всю свою историю"),
    ("length", "узнать свой размер 🍆"),
    ("longest", "узнать самый длинный 🍆"),
    ("namaz", "получить время намаза 🙏"),
    ("timer", "запустить таймер")
]


def _get_skills_hints(skills_list: List[Dict]) -> str:
    return "\n".join(f"{s['name']} – {s['hint']}" for s in skills_list)
