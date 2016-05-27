import logging
import random

from telegram import Emoji, ForceReply, InlineKeyboardButton, \
    InlineKeyboardMarkup, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, \
    CallbackQueryHandler, Filters

import yadict
import config

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    filename='yappi.log'
)


def handle_message(bot, update, args):
    try:
        bot.sendMessage(
            update.message.chat_id,
            yadict.prepare_message(args),
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as err:
        logging.exception(str(err))


Q_MENU, Q_AWAIT_ANSWER = range(2)

q_state = dict()
q_context = dict()
q_values = dict()


def ask(bot, update):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    chat_state = q_state.get(user_id, Q_MENU)

    if chat_state == Q_MENU:
        q_state[user_id] = Q_AWAIT_ANSWER

        text, translate, answers = yadict.guess()
        answers = [(answ, flag)
                   for answ, flag in zip(answers, [0] * len(answers))]
        answers.append((translate, 1))
        random.shuffle(answers)

        q_context[user_id] = text, translate, answers

        reply_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton(a[0], callback_data=a[0])] for a in answers])
        bot.sendMessage(chat_id, text=text, reply_markup=reply_markup)


def get_answer_index(answ, answers):
    for i, a in enumerate(answers):
        if a[0] == answ:
            return i


def mark_right_answer(answers):
    for i, answ in enumerate(answers):
        if answ[1]:
            answers[i] = u'*{0}*'.format(answers[i][0]), answers[i][1]


def mark_answer(answers, ind, mark):
    answers[ind] = u'{0} {1}'.format(answers[ind][0], mark), answers[ind][1]


def confirm_answer(bot, update):
    query = update.callback_query
    chat_id = query.message.chat_id
    user_id = query.from_user.id
    query_data = query.data
    user_state = q_state.get(user_id, Q_MENU)
    text, translate, answers = q_context.get(user_id, None)

    if user_state == Q_AWAIT_ANSWER:
        del q_state[user_id]
        del q_context[user_id]
        bot.answerCallbackQuery(query.id, text="Ok!")

        answer_index = get_answer_index(query_data, answers)
        mark_right_answer(answers)
        content = text + '\n'

        if query_data == translate:
            mark_answer(answers, answer_index,
                        Emoji.WHITE_HEAVY_CHECK_MARK.decode('utf-8'))
            content += '\n'.join(zip(*answers)[0])
            bot.editMessageText(text=content,
                                chat_id=chat_id,
                                message_id=query.message.message_id,
                                parse_mode=ParseMode.MARKDOWN)
        else:
            mark_answer(answers, answer_index,
                        Emoji.NO_ENTRY_SIGN.decode('utf-8'))
            content += '\n'.join(zip(*answers)[0])
            bot.editMessageText(text=content,
                                chat_id=chat_id,
                                message_id=query.message.message_id,
                                parse_mode=ParseMode.MARKDOWN)


updater = Updater(config.Config.BTOKEN, job_queue_tick_interval=60 * 60)

updater.dispatcher.add_handler(CommandHandler(
    'tr', handle_message, pass_args=True))
updater.dispatcher.add_handler(CommandHandler('q', ask))
updater.dispatcher.add_handler(CallbackQueryHandler(confirm_answer))

updater.start_polling()
updater.idle()
