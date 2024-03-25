from __init__ import logging,  CNFG, CMMN, SYMBOL, YAML
from symbols import Symbols, dct_sym
from paper import Paper
from omspy_brokers.finvasia import Finvasia
import pendulum as pdlm
import traceback
import datetime


def get_api():
    if CMMN["live"]:
        api = Finvasia(**CNFG)
    else:
        api = Paper(**CNFG)

    if not api.authenticate():
        logging.error("Failed to authenticate")
        SystemExit()
    return api


class LastPrice:
    count = 0

    @classmethod
    def full_quote(cls, api, exchange, token):
        lastBusDay = datetime.datetime.today()
        lastBusDay = lastBusDay.replace(
            hour=0, minute=0, second=0, microsecond=0)
        resp = api.finvasia.get_time_price_series(
            exchange, token)
        cls.count += 1
        return resp


class Stratergy:
    def __init__(self, api, base, dct_base, ul):
        self._api = api
        self._base = dct_base
        self._symbol = Symbols(dct_base['exchange'], base, dct_base['expiry'])
        self._symbol.get_exchange_token_map_finvasia()
        self._ul = ul
        self._tokens = self._symbol.get_tokens(self.atm)

    @property
    def atm(self):
        resp = LastPrice.full_quote(
            self._api, self._ul["exchange"], self._ul["token"])
        self._atm = self._symbol.get_atm(float(resp["lp"]))
        return self._atm

    @property
    def ce(self):
        self._ce = self._symbol.find_option_by_distance(self.atm,
                                                        self._base["away_from_atm"],
                                                        "C", self._tokens)
        return self._ce

    @property
    def pe(self):
        self._pe = self._symbol.find_option_by_distance(self.atm,
                                                        self._base["away_from_atm"],
                                                        "P", self._tokens)
        return self._pe

    @property
    def price_and_vwap(self):
        call_resp = LastPrice.full_quote(
            self._api, self._base["exchange"], self.ce["token"]
        )
        print(call_resp)
        return call_resp

    def run(self):
        while pdlm.now() < pdlm.parse("15:30"):
            price, vwap = self.price_and_vwap


def main():
    try:
        api = get_api()
        ul = dict(
            exchange=dct_sym[SYMBOL]["exch"],
            token=dct_sym[SYMBOL]["token"]
        )
        sgy = Stratergy(api, SYMBOL, YAML[SYMBOL], ul)
        sgy.price_and_vwap()

    except Exception as e:
        print(e)
        traceback.print_exc()


if __name__ == "__main__":
    main()
