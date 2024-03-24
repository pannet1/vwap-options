from __init__ import logging,  CNFG, CMMN, SYMBOL, YAML
from symbols import Symbols, dct_sym
from paper import Paper
from omspy_brokers.finvasia import Finvasia
import traceback


class Datasource:
    def __init__(self, api, tokens):
        self.api = api
        self.tokens = tokens


class Stratergy:
    def __init__(self, api, tokens):
        self.api = api
        self.tokens = tokens
        self.price = 0.00
        self.vwap = 0.00


def get_api():
    if CMMN["live"]:
        api = Finvasia(**CNFG)
    else:
        api = Paper(**CNFG)

    if not api.authenticate():
        logging.error("Failed to authenticate")
        SystemExit()
    return api


def main():
    try:
        obj_sym = Symbols(
            YAML[SYMBOL]["exchange"], CMMN["base"],
            YAML[SYMBOL]["expiry"]
        )
        obj_sym.get_exchange_token_map_finvasia()
        api = get_api()
        resp = api.finvasia.get_quotes(
            dct_sym[SYMBOL]["exch"], dct_sym[SYMBOL]["token"])
        atm = obj_sym.get_atm(float(resp("lp")))
        lst = list(obj_sym.get_tokens(atm))
    except Exception as e:
        print(e)
        traceback.print_exc()


main()
