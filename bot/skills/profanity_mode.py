import logging
import re
from functools import partial

from telegram import Update, User
from telegram.error import BadRequest, TelegramError
from telegram.ext import MessageHandler, Filters, Updater, CallbackContext

from mode import Mode, ON

logger = logging.getLogger(__name__)

mode = Mode(mode_name="profanity_mode", default=ON, pin_info_msg=True)


def _variants_of_letter(alphabet, letter):
    letters = alphabet.get(letter, letter)
    return '|'.join(letters.split())


def _build_profanity_phrase(*symbols, **kwargs):
    variants_func = kwargs.get('variants_func', partial(_variants_of_letter, {
        'а': 'а',
        'б': 'б6',
        'в': 'в',
        'г': 'г',
        'д': 'д',
        'е': 'е',
        'ё': 'ё',
        'ж': 'ж',
        'з': 'з',
        'и': 'и',
        'й': 'й',
        'к': 'к',
        'л': 'л',
        'м': 'м',
        'н': 'н',
        'о': 'о',
        'п': 'п',
        'р': 'р',
        'с': 'с',
        'т': 'т',
        'у': 'у',
        'ф': 'ф',
        'х': 'х',
        'ц': 'ц',
        'ч': 'ч',
        'ъ': 'ъ',
        'ы': 'ы',
        'ь': 'ь',
        'э': 'э',
        'ю': 'ю',
        'я': 'я',
    }))
    separator = '(?:[^а-я])*'

    if len(symbols) == 1:
        symbols = symbols[0].split()

    symbol_regexp = []
    for symbol in symbols:
        if len(symbol) == 1:
            symbol = [symbol]

        parts = [variants_func(i) for i in symbol]
        symbol_regexp.append('[{}]+'.format('|'.join(parts)))

    return r'[а-я]*({})[а-я]*'.format(separator.join(symbol_regexp))


def _build_neutral_phrase(*symbols):
    if len(symbols) == 1:
        symbols = symbols[0].split()
    out = []
    for symbol in symbols:
        out.append('[{}]'.format(symbol))
    return r'({})'.format(''.join(out))


def _create_profanity_re():
    return re.compile('|'.join([
        _build_profanity_phrase('п еи з д'),
        _build_profanity_phrase('х у йёуяиюе'),
        _build_profanity_phrase('о х у е втл'),
        _build_profanity_phrase('п и д оеа р'),
        _build_profanity_phrase('п и д р'),
        _build_profanity_phrase('её б а нклт'),
        _build_profanity_phrase('у её б оа нтк'),
        _build_profanity_phrase('её б л аои'),
        _build_profanity_phrase('в ы её б'),
        _build_profanity_phrase('е б ё т'),
        _build_profanity_phrase('св ъь еёи б'),
        _build_profanity_phrase('б л я'),
        _build_profanity_phrase('г оа в н'),
        _build_profanity_phrase('м у д а кч'),
        _build_profanity_phrase('г ао н д о н'),
        _build_profanity_phrase('ч м оы'),
        _build_profanity_phrase('д е р ь м'),
        _build_profanity_phrase('ж о п'),
        _build_profanity_phrase('ш л ю х'),
        _build_profanity_phrase('з ао л у п'),
        _build_profanity_phrase('м ао н д'),
        _build_profanity_phrase('с у ч а р'),
        _build_profanity_phrase('д ао л б ао её б'),
        _build_profanity_phrase('оа б оа с а тц'),
        _build_profanity_phrase('д р оа ч'),
    ]), re.IGNORECASE | re.UNICODE)


def _create_neutral_re():
    return re.compile('|'.join([
        _build_neutral_phrase('х л е б а л оа'),
        _build_neutral_phrase('с к и п и д а р'),
        _build_neutral_phrase('к о л е б а н и яей'),
        _build_neutral_phrase('з ао к оа л е б а лт'),
        _build_neutral_phrase('р у б л я'),
        _build_neutral_phrase('с т е б е л ь'),
        _build_neutral_phrase('с т р а х о в к ауи'),
        r'([о][с][к][о][Р][б][л][я]([т][ь])*([л])*([е][ш][ь])*)',
        r'([в][л][ю][б][л][я](([т][ь])([с][я])*)*(([е][ш][ь])([с][я])*)*)',
        r'((([п][о][д])*([з][а])*([п][е][р][е])*)*[с][т][р][а][х][у]([й])*([с][я])*([е][ш][ь])*([е][т])*)',
        r'([м][е][б][е][л][ь]([н][ы][й])*)',
        r'([Уу][Пп][Оо][Тт][Рр][Ее][Бб][Лл][Яя]([Тт][Ьь])*([Ее][Шш][Ьь])*([Яя])*([Лл])*)',
        r'([Ии][Сс][Тт][Рр][Ее][Бб][Лл][Яя]([Тт][Ьь])*([Ее][Шш][Ьь])*([Яя])*([Лл])*)',
        r'([Сс][Тт][Рр][Аа][Хх]([Аа])*)',
    ]), re.IGNORECASE | re.UNICODE)


class ObsceneWordsFilter(object):
    def __init__(self, bad_regexp, good_regexp):
        self.bad_regexp = bad_regexp
        self.good_regexp = good_regexp

    def find_bad_word_matches(self, text):
        return self.bad_regexp.finditer(text)

    def find_bad_word_matches_without_good_words(self, text):
        for match in self.find_bad_word_matches(text):
            if not self.is_word_good(match.group()):
                yield match

    def is_word_good(self, word):
        return bool(self.good_regexp.match(word))

    def is_word_bad(self, word):
        if self.is_word_good(word):
            return False

        return bool(self.bad_regexp.match(word))

    def mask_bad_words(self, text):
        for match in self.find_bad_word_matches_without_good_words(text):
            start, end = match.span()
            text = self.mask_text_range(text, start, end)
        return text

    @staticmethod
    def mask_text_range(text, start, stop, symbol='*'):
        return text[:start] + (symbol * (stop - start)) + text[stop:]


filter = ObsceneWordsFilter(_create_profanity_re(), _create_neutral_re())


@mode.add
def add_profanity_mode(upd: Updater, handlers_group: int):
    logger.info("registering profanity-mode handlers")

    dp = upd.dispatcher

    dp.add_handler(
        MessageHandler(~Filters.status_update, profanity, run_async=True),
        handlers_group,
    )


def profanity(update: Update, context: CallbackContext):
    text = update.message["text"]
    user: User = update.effective_user
    chat_id = update.effective_chat.id
    generator = filter.find_bad_word_matches(text)
    words = list(map(lambda x: x.group(0), list(generator)))

    if len(words) > 0:
        try:
            context.bot.delete_message(chat_id, update.effective_message.message_id)
        except (BadRequest, TelegramError) as err:
            logger.info("can't delete msg: %s", err)

        context.bot.send_message(
            chat_id, f"{user.full_name} написал(а) нехорошие слова.\n\nИзмененное сообщение:\n{filter.mask_bad_words(text)}\n\nУра, еще один день в раю!"
        )
