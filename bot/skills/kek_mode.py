import logging
from typing import Callable

from google.cloud import translate
from telegram import Update, User
from telegram.error import BadRequest, TelegramError
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext

from config import get_project_id
from mode import Mode, OFF

logger = logging.getLogger(__name__)

mode = Mode(mode_name="kek_mode", default=OFF, pin_info_msg=True)


@mode.add
def add_kek_mode(upd: Updater, handlers_group: int):
    logger.info("registering kek handlers")
    dp = upd.dispatcher

    dp.add_handler(
        MessageHandler(
            ~Filters.status_update,
            kek,
            run_async=True,
        ),
        handlers_group,
    )


def kek(update: Update, context: CallbackContext):
    text = update.message["text"]
    user: User = update.effective_user
    chat_id = update.effective_chat.id

    try:
        context.bot.delete_message(chat_id, update.effective_message.message_id)
    except (BadRequest, TelegramError) as err:
        logger.info("can't delete msg: %s", err)

    number = sum([ord(c) for c in user.full_name])
    languages = ["ro", "uk", "sr", "sk", "sl", "uz", "bg", "mn", "kk"]
    language = languages[number % len(languages)]
    emoji = chr(ord("😀") + number % 75)

    try:
        context.bot.send_message(
            chat_id, f"{emoji} {user.full_name}: {translation(text, language)}"
        )
    except TelegramError as err:
        logger.info("can't translate msg: %s, because of: %s", text, err)


def f(text: str, language: str) -> str:
    project_id = get_project_id()
    client = translate.TranslationServiceClient()
    parent = client.common_location_path(project_id, "global")

    response = client.translate_text(
        parent=parent,
        contents=[text],
        mime_type="text/plain",
        source_language_code="ru",
        target_language_code=language,
    )

    return response.translations[0].translated_text


def _make_translation(func: Callable[[str, str], str]) -> Callable[[str, str], str]:
    def tr(string: str, lang: str) -> str:
        if string is None or len(string) < 1:
            raise ValueError("nothing to translate")
        return func(string, lang)

    return tr


translation = _make_translation(f)
