import logging
import os
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, ConversationHandler, RegexHandler, Filters
import receipt
import json
import traceback
from io import BytesIO
import hashlib
import datetime
import sys
import db

from environment import phone, password, webhook_port, webhook_base_url, token

import google_api
# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging._nameToLevel[
                        os.environ.get("LOG_LEVEL", "DEBUG")])
logger = logging.getLogger(__name__)


BARCODE, LOGIN, REPEAT = range(3)


def _get_document_bytes(query, data):
    bytes_ = BytesIO()
    res = list(map(lambda e: json.dumps(
        e, indent=None, ensure_ascii=False), data))
    h = hashlib.md5(query.encode('utf8'))
    bytes_.name = "receipt_%s_%s.txt" % (
        datetime.date.today(), h.hexdigest()[0:8])
    bytes_.writelines(map(lambda e: e.encode('utf8'), res))
    bytes_.seek(0)

    return bytes_


def login(bot, update):
    update.message.reply_text(
        "Нажмите на ссылку, чтобы я получил права к гугл документам для записи детализации чека в таблицу")
    chat_id = update.message.chat_id
    url = google_api.auth_url(chat_id)
    update.message.reply_text(url)


def is_logged_in(bot, update):
    update.message.reply_text("yes" if google_api.is_auth(
        update.message.chat_id) else "no")


def start_processing(bot, update):
    update.message.reply_text('Введите текст из баркода с чека',
                              reply_markup=ReplyKeyboardMarkup([['/cancel']]))
    return BARCODE


def repeat(bot, update, user_data):

    logger.debug("Repeat answer %s" % (update.message.text))
    if update.message.text == 'нет':
        update.message.reply_text(
            'Хорошо, буду ждать другого чека.', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    user_data['repeat'] = update.message.text == 'да'
    update.message.text = user_data['receipt']
    update.message.reply_text(
        'Хорошо, запишем еще раз', reply_markup=ReplyKeyboardMarkup([['/cancel']]))
    return receipt_info(bot, update, user_data)


def receipt_info(bot, update, user_data):
    logger.debug("receive %s" % update.message.text)
    if not google_api.fetch_token(update.message.chat_id):

        login(bot, update)
        return ConversationHandler.END

    try:
        rec = receipt.get_receipt(update.message.text)
        if db.is_receipt_processed(rec.key) and 'repeat' not in user_data:
            reply_keyboard = [['да', 'нет'], ['/cancel']]

            update.message.reply_text(
                'Этот чек уже обрабатывался. Записать его еще раз?',
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
            user_data['receipt'] = update.message.text
            return REPEAT

        fetched, rec = receipt.fetch_and_build_details(rec)

        if fetched:

            chat_id = update.message.chat_id
            # doc = _get_document_bytes(update.message.text, data)
            # bot.send_document(chat_id=chat_id, document=doc)

            rows = []
            for r in rec.entries:
                rows.append(list(map(lambda k: r[k], receipt.header)))

            update.message.reply_text(
                "Начал записывать чек в гугл таблицу", quote=True)

            url = google_api.append_rows(chat_id, rows, receipt.header)
            db.mark_receipt_as_processed(rec.key)
            update.message.reply_text(
                "Чек с %d записями был записан в документ %s. Ссылка - %s" % (len(rows), google_api.SPREADSHEET_NAME, url), quote=True)

        else:
            update.message.reply_text(
                "Такого чека не существует. Возможно он был распечатан больше месяца назад или он еще не дошел до налоговой.", quote=True)

    except receipt.QueryException as qe:
        update.message.reply_text(str(qe), quote=True)
        return BARCODE
    except (TimeoutError, ConnectionError) as ec:
        update.message.reply_text(
            'Проблемы с соединением. Повторите запрос позже.')
        return BARCODE
    except Exception as e:
        logger.error(e)
        update.message.reply_text(
            "Упс! У меня какие то проблемы. Обратитесь к разработчику на гитхабе - https://github.com/patsak/tg-receipt-bot")
        traceback.print_exc(file=sys.stdout)
    user_data.clear()
    return ConversationHandler.END


def cancel(bot, update, user_data):
    update.message.reply_text(
        'Больше не жду данных с чека. Если потребуется ввести новые данные нажмите /send_receipt', reply_markup=ReplyKeyboardRemove())
    user_data.clear()
    return ConversationHandler.END


def main():
    if not receipt.signin(phone, password):
        exit(1)

    updater = Updater(token)

    dp = updater.dispatcher

    dp.add_handler(ConversationHandler(

        entry_points=[CommandHandler('send_receipt', start_processing)],
        states={
            BARCODE: [MessageHandler(Filters.text, receipt_info, pass_user_data=True)],
            REPEAT: [RegexHandler('^(да|нет)$', repeat, pass_user_data=True)],
        },
        fallbacks=[CommandHandler('cancel', cancel, pass_user_data=True)]))

    dp.add_handler(CommandHandler("sign_in", login))
    dp.add_handler(CommandHandler("is_logged_in", is_logged_in))

    if webhook_base_url:

        updater.start_webhook(listen="0.0.0.0",
                              port=webhook_port,
                              webhook_url=webhook_base_url + "/" + token)
        updater.bot.set_webhook(webhook_base_url + "/" + token)
    else:
        updater.start_polling()

    updater.idle()


if __name__ == "__main__":
    main()
