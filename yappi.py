from functools import partial
import logging
import re

from telegram import InlineKeyboardButton as Button
from telegram import InlineKeyboardMarkup, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters

import yadict
import config

from models import CallbackEntity, Request, User

if config.Config.DEBUG:
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.DEBUG
    )
else:
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.DEBUG,
        filename='yappi.log'
    )


class AnswerOption(object):
    TRANSLATE = '1'
    SKIP = '2'


class MessageTemplate(object):
    TRANSLATE = 'Would you like to translate it?'
    SKIP = 'Nevermind'
    CALLBACK_DATA_MISSING = 'Can\'t identify your request :('
    USER_STATS_LINE = '*{}:* {}'


def save_callback_data(data):
    return CallbackEntity.create(data=data)


def encode_callback_data(answer_option, index):
    return '{}@{}'.format(answer_option, index)


def decode_callback_data(callback_data):
    index = int(callback_data.split('@')[1])
    return CallbackEntity.get_callback(index)


def decode_answer_option(callback_data):
    return callback_data.split('@')[0]


def userify(func):
    def wrapper(*args, **kwargs):
        update = args[1]
        request = update.callback_query or update.message
        tid = request.from_user.id
        name = request.from_user.first_name
        user = User.create(tid=tid, name=name)
        kwargs['user'] = user
        return func(*args, **kwargs)
    return wrapper


@userify
def handle_message(bot, update, args, **kwargs):
    user = kwargs['user']
    try:
        bot.sendMessage(
            update.message.chat_id,
            yadict.prepare_message(args, user),
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as err:
        logging.exception(str(err))


def edit_message(bot, update, text):
    bot.editMessageText(
        text=text,
        chat_id=update.callback_query.message.chat_id,
        message_id=update.callback_query.message.message_id,
        parse_mode=ParseMode.MARKDOWN
    )


def handle_text(bot, update):
    user_message = update.message.text
    data_id = save_callback_data(user_message)
    encode_translate = encode_callback_data(AnswerOption.TRANSLATE, data_id)
    encode_skip = encode_callback_data(AnswerOption.SKIP, data_id)

    keyboard = [[
        Button('tr', callback_data=encode_translate),
        Button('skip', callback_data=encode_skip)
    ]]
    markup = InlineKeyboardMarkup(keyboard)

    bot.send_message(
        chat_id=update.message.chat_id,
        text=MessageTemplate.TRANSLATE,
        reply_markup=markup,
        parse_mode=ParseMode.MARKDOWN)


@userify
def handle_message_dialog(bot, update, answer, **kwargs):
    reply = partial(edit_message, bot, update)
    callback_data = update.callback_query.data
    content = decode_callback_data(callback_data)
    user = kwargs['user']

    if not content:
        reply(MessageTemplate.CALLBACK_DATA_MISSING)

    # translate request
    elif answer == AnswerOption.TRANSLATE:
        chat_id = update.callback_query.message.chat_id
        reply(yadict.prepare_message(content, user))

    elif answer == AnswerOption.SKIP:
        reply(MessageTemplate.SKIP)


def callback_handler(bot, update):
    answer = decode_answer_option(update.callback_query.data)

    translate_answers = (
        AnswerOption.TRANSLATE,
        AnswerOption.SKIP)

    if answer in translate_answers:
        handle_message_dialog(bot, update, answer)


def stats(bot, update):
    stats_message = '\n'.join(
        MessageTemplate.USER_STATS_LINE.format(k, v)
        for k, v in Request.statistics().items()
    )

    bot.sendMessage(
        update.message.chat_id,
        stats_message,
        parse_mode=ParseMode.MARKDOWN
    )


updater = Updater(config.Config.BTOKEN)

updater.dispatcher.add_handler(CallbackQueryHandler(callback_handler))
updater.dispatcher.add_handler(
    CommandHandler('tr', handle_message, pass_args=True))
updater.dispatcher.add_handler(CommandHandler('stats', stats))
updater.dispatcher.add_handler(MessageHandler(Filters.text, handle_text))

updater.start_polling()
updater.idle()
