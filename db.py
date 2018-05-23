import redis
import os

r = redis.StrictRedis(host=os.environ.get(
    "REDIS_HOST", "localhost"), port=int(os.environ.get('REDIS_PORT', 6379)), db=0)


def save_token(chat_id, token):
    chat_id = str(chat_id)
    r.set(chat_id + "_token", token['access_token'],
          ex=(int(token['expires_in']) - 600))
    r.set(chat_id + "_refresh_token", token['refresh_token'])


def save_receipt(key, document):
    r.set("receipt_" + key, document, ex=3600)


def get_receipt(key):
    receipt = r.get("receipt_" + key)
    if receipt:
        return receipt.decode("utf-8")
    return None


def mark_receipt_as_processed(key):
    r.set("r_processed_" + key, "1", ex=3600*24*30)


def is_receipt_processed(key):
    return r.get("r_processed_" + key) != None


def get_token(chat_id):
    chat_id = str(chat_id)
    ret = {}
    access_token = r.get(chat_id + "_token")
    if access_token:
        ret['access_token'] = access_token.decode("utf-8")
    refresh_token = r.get(chat_id + "_refresh_token")
    if refresh_token:
        ret['refresh_token'] = refresh_token.decode("utf-8")

    expires_in = r.ttl(chat_id + "_token")
    if expires_in:
        ret['expires_in'] = int(expires_in)
    return ret


def get_refresh_token(chat_id):
    chat_id = str(chat_id)
    r.get(chat_id + "_refresh_token")
