import flask
from flask import request, redirect, abort

import google_api
import telegram
import os

import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging._nameToLevel[
                        os.environ.get("LOG_LEVEL", "DEBUG")])
logger = logging.getLogger(__name__)


app = flask.Flask(__name__)
app.debug = bool(os.environ.get("DEBUG", False))

bot = telegram.Bot(os.environ.get('TOKEN'))


@app.route("/auth")
def auth():
    chat_id = request.args.get("state", None)
    code = request.args.get("code", None)
    if not chat_id or not code:
        abort(400, "state and code parameters must be set")

    if google_api.fetch_token(chat_id, code):
        bot.send_message(chat_id, "I have been authorized")
    else:
        bot.send_message(chat_id, "Auhorization failed. Please repeat /login")
    return redirect("http://t.me/%s" % (bot.username))


if __name__ == "__main__":

    app.run(host='127.0.0.1', port=8080, debug=True, ssl_context='adhoc')
