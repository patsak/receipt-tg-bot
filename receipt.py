import requests
import json
import sys
from requests.auth import HTTPBasicAuth
import logging
import db
import hashlib
import json
from urllib.parse import parse_qs

_session = requests.Session()
_session.headers["Content-Type"] = "application/json; charset=UTF-8"
_base_url = "https://proverkacheka.nalog.ru:9999/v1"
_session.headers["device-id"] = "0230123"
_session.headers["device-os"] = "android"

logger = logging.getLogger(__name__)

_actual_item_keys = ['name', 'quantity', 'price', 'sum']
_common = ['id', 'datetime', 'fn', 'fpd', 'fd', 'shop', 'shop_inn', 'total_cash',
           'total_ecash']

header = _common + _actual_item_keys


class QueryException(Exception):
    pass


class Receipt():
    def __init__(self, fn, fd, fpd, entries=None):
        self.fn = fn
        self.fd = fd
        self.fpd = fpd
        self.key = Receipt._receipt_key(fn, fd, fpd)
        self.entries = entries

    @staticmethod
    def _receipt_key(fn, fd, fpd):
        key = str(fn) + str(fd) + str(fpd)
        key = hashlib.md5(key.encode('utf-8')).hexdigest()[0:8]
        return key


def get_receipt(qrcodedata):
    query = parse_qs(qrcodedata)
    if "fn" not in query or "fp" not in query or "i" not in query:
        raise QueryException(
            "Неправильный формат запроса. Должен быть текст распознанный с баркода чека.")
    fn = query["fn"][0]
    fpd = query["fp"][0]
    fd = query["i"][0]
    rec = Receipt(fn, fd, fpd)
    return rec


def fetch_and_build_details(rec):

    res, body = fetch_details(rec)
    if res:
        body = body['document']['receipt']
        res = []
        response = {}
        response['shop'] = body.get('user', None)
        response['shop_inn'] = body.get('userInn', None)
        response['total_cash'] = float(body.get('cashTotalSum', None))/100
        response['total_ecash'] = float(body.get('ecashTotalSum', None))/100
        response['datetime'] = body.get('dateTime', None)
        response['fn'] = rec.fn
        response['fpd'] = rec.fpd
        response['fd'] = rec.fd

        for index, item_raw in enumerate(body['items']):

            item = {}
            for k in _actual_item_keys:
                item[k] = item_raw.get(k, None)

            item['price'] = float(item['price'])/100
            item['sum'] = float(item['sum'])/100

            entry = {**item, **response}
            id_ = rec.key+"_"+str(index)
            id_ = hashlib.md5(id_.encode('utf8')).hexdigest()[0:8]
            entry['id'] = id_
            res.append(entry)
        rec.entries = res
        return True, rec
    else:
        return False, None


def register(email, phone):
    res = _session.post(
        "%s/mobile/users/signup" % _base_url,
        json={
            "email": email,
            "name": "receipt",
            "phone": phone
        })  # type: request.Response

    if res.ok:
        return True, "ok"
    else:
        return False, (res.text, res.status_code)


def signin(phone, _pass):
    _session.auth = HTTPBasicAuth(phone, _pass)

    res = _session.get("%s/mobile/users/login" %
                       _base_url)  # type: request.Response
    if not res.ok:
        _session.auth = None
    return res.ok


def fetch_details(receipt):

    cached_doc = db.get_receipt(receipt.key)
    if cached_doc:
        logger.debug("Take receipt with key %s from cache" % (receipt.key))
        return True, json.loads(cached_doc)

    params = {
        "fiscalSign": receipt.fpd,
        "sendToEmail": "no"
    }
    res = _session.get("%s/inns/*/kkts/*/fss/%s/tickets/%s" %
                       (_base_url, receipt.fn, receipt.fd), params=params)
    if res.status_code == 202:
        res = _session.get("%s/inns/*/kkts/*/fss/%s/tickets/%s" %
                           (_base_url, receipt.fn, receipt.fd), params=params)
        if res.ok:
            db.save_receipt(receipt.key, json.dumps(
                res.json(), indent=None, ensure_ascii=False))
        return True, res.json() if res.ok else res.text
    if res.status_code == 200:
        logger.debug("Save receipt with key %s" % (receipt.key))
        if res.ok:
            db.save_receipt(receipt.key, json.dumps(
                res.json(), indent=None, ensure_ascii=False))
        return True, res.json()
    if res.status_code >= 500:
        logger.error("Receipt service error %s" % (str(res.text)))
        raise ConnectionError(
            "nalog.ru service unavailable. Please repeat later.")

    return False, res.text
