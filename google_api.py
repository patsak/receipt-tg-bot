import os
from requests_oauthlib import OAuth2Session
import db
import gspread
import logging
from environment import client_id, client_secret
from oauth2client.client import AccessTokenCredentials


authorization_base_url = "https://accounts.google.com/o/oauth2/v2/auth"
token_url = "https://www.googleapis.com/oauth2/v4/token"
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file"
]
redirect_uri = os.environ.get("REDIRECT_URI", "https://localhost:8080/auth")

google = OAuth2Session(client_id, scope=scope, redirect_uri=redirect_uri)


SPREADSHEET_NAME = 'tg_receipts_bot'

logger = logging.getLogger(__name__)


def auth_url(chat_id):
    google.state = chat_id
    url, state = google.authorization_url(
        authorization_base_url, access_type="offline", prompt="consent")
    return url


def is_auth(chat_id):
    return fetch_token(chat_id) != None


def fetch_token(chat_id, code=None):
    google.state = chat_id
    token = None
    try:
        token = db.get_token(chat_id)

        if code:

            token = google.fetch_token(token_url,
                                       client_secret=client_secret,
                                       code=code)
            db.save_token(chat_id, token)
        elif 'access_token' not in token:
            refresh_token = token.get('refresh_token', None)
            if refresh_token:
                token = google.refresh_token(
                    token_url, refresh_token, client_id=client_id, client_secret=client_secret)
                db.save_token(chat_id, token)
    except (TimeoutError, ConnectionError) as service_error:
        logger.error("Connection problem. %s" % (service_error))
        raise service_error

    if 'access_token' in token:
        return token
    else:
        return None


def append_rows(chat_id, values, header):
    logger.debug("Append %d values" % (len(values)))
    service = _get_client(chat_id)

    try:
        sheet = service.open(SPREADSHEET_NAME)
    except gspread.exceptions.SpreadsheetNotFound:
        logger.debug("Create spreadsheet")
        sheet = service.create(SPREADSHEET_NAME)
        worksheet = sheet.get_worksheet(0)
        worksheet.clear()
        worksheet.resize(1, len(values) + 1)
        worksheet.append_row(header)

    worksheet = sheet.get_worksheet(0)

    for r in values:
        worksheet.append_row(r)
    return "https://docs.google.com/spreadsheets/d/%s/" % (str(sheet.id))


def _get_client(chat_id):
    google.state = chat_id
    google.token = fetch_token(chat_id)

    creds = AccessTokenCredentials(
        google.token['access_token'], 'tg-receipt-bot/1.0')
    gc = gspread.authorize(creds)

    return gc
