from __init__ import logging,  CNFG, CMMN, FILS, F_POS, SYMBOL, YAML, UTIL
from symbols import Symbols, dct_sym
from paper import Paper
from omspy_brokers.finvasia import Finvasia
import pendulum as pdlm
import traceback
from typing import Dict, List
from rich import print

CHECK_IN_SECS = 60


def filter_by_keys(keys: List, lst: List[Dict]) -> List[Dict]:
    new_lst = []
    if lst and isinstance(lst, list) and any(lst):
        for dct in lst:
            new_dct = {}
            for key in keys:
                if dct.get(key, None):
                    new_dct[key] = float(dct[key])
            new_lst.append(new_dct)
    return new_lst


def get_api():
    if CMMN["live"]:
        api = Finvasia(**CNFG)
    else:
        api = Paper(**CNFG)
    if not api.authenticate():
        logging.error("Failed to authenticate")
        SystemExit()
    return api


class ApiHelper:
    count = 0
    second = pdlm.now().second

    @staticmethod
    def scriptinfo(api, exchange, token):
        try:
            if ApiHelper.second != pdlm.now().second:
                UTIL.slp_til_nxt_sec()
            resp = api.scriptinfo(exchange, token)
            ApiHelper.count += 1
            ApiHelper.second = pdlm.now().second
            return float(resp['lp'])
        except Exception as e:
            print(e)
            traceback.print_exc()

    @staticmethod
    def historical(api, exchange, token):
        try:
            def sum_by_key(key):
                return sum(dct[key] for dct in filtered)

            lst_white = ["intvwap", "intv", "intc"]
            lastBusDay = pdlm.now()
            fromBusDay = lastBusDay.replace(
                hour=9, minute=15, second=0, microsecond=0
            ).subtract(days=1)
            if ApiHelper.second != pdlm.now().second:
                UTIL.slp_til_nxt_sec()
            logging.debug(f"{exchange}{token} \n")
            resp = api.historical(exchange, token, fromBusDay.timestamp(),
                                  lastBusDay.timestamp(), 1)
            filtered = filter_by_keys(lst_white, resp)
            # find the average by key intvwap in the filtered list
            for dct in filtered:
                dct['ivc'] = dct["intv"] * dct["intc"]
            vwap = sum_by_key("ivc") / sum_by_key("intv")
            ApiHelper.count += 1
            ApiHelper.second = pdlm.now().second
            return vwap, resp[0]["intc"]
        except Exception as e:
            print(e)
            traceback.print_exc()


class Stratergy:
    def __init__(self, api, base, base_info, ul):
        self._api = api
        self._base = base
        self._base_info = base_info
        self._symbol = Symbols(
            base_info['exchange'], base, base_info['expiry'])
        self._symbol.get_exchange_token_map_finvasia()
        self._ul = ul
        self._atm = 0
        self._tokens = self._symbol.get_tokens(self.atm)
        self._is_roll = False
        self._timer = pdlm.now()
        if FILS.is_file_not_2day(F_POS):
            FILS.nuke_file(F_POS)

    @property
    def is_no_position(self):
        lst_of_pos = self._api.positions
        # find if list of positions is not empty and
        # if quantity is not equal to zero
        is_pos = False
        for pos in lst_of_pos:
            if pos["quantity"] != 0:
                is_pos = True
                break
        return is_pos

    @property
    def atm(self):
        lp = ApiHelper().scriptinfo(
            self._api, self._ul["exchange"], self._ul["token"])
        logging.debug(lp)
        atm = self._symbol.get_atm(lp)
        self._is_roll = True if atm != self._atm else False
        self._atm = atm
        return self._atm

    @property
    def ce(self):
        self._ce = self._symbol.find_option_by_distance(self._atm,
                                                        self._base_info["away_from_atm"],
                                                        "C", self._tokens)
        return self._ce

    @property
    def pe(self):
        self._pe = self._symbol.find_option_by_distance(self._atm,
                                                        self._base_info["away_from_atm"],
                                                        "P", self._tokens)
        return self._pe

    @property
    def info(self):
        cv, cc = ApiHelper().historical(
            self._api, self._base_info["exchange"], self.ce["token"]
        )
        if cv and cc:
            self._ce["vwap"] = float(cv)
            self._ce["price"] = float(cc)
            pv, pc = ApiHelper().historical(
                self._api, self._base_info["exchange"], self.pe["token"]
            )
            if pv and pc:
                self._pe["vwap"] = float(pv)
                self._pe["price"] = float(pc)
                self._price = self._ce["price"] + self._pe["price"]
                self._vwap = self._ce["vwap"] + self._pe["vwap"]
            self._strategy = {
                "ce": self._ce,
                "pe": self._pe,
                "price": self._price,
                "vwap": self._vwap
            }
        return self._strategy

    @property
    def is_enter(self):
        # TODO
        if self._strategy["price"] < self._strategy["vwap"]:
            return True
        return False

    def run(self):
        def place_order(symbol):
            self._api.order_place(
                symbol=symbol,
                side="BUY",
                quantity=self._base_info["quantity"],
                price=self._ce["price"],
                exchange="NFO",
                tag="enter",
            )

        def close_positions():
            for pos in self._api.positions:
                self._api.order_place(
                    symbol=pos["symbol"],
                    side="BUY",
                    quantity=abs(pos["quantity"]),
                    exchange="NFO",
                    product="NRML",
                    order_type="MARKET",
                    tag="close",
                )

        while True:
            next_trade = self._timer.add(seconds=CHECK_IN_SECS)
            print(f"next trade:{next_trade.to_datetime_string()}")
            print(self.info)
            if self.is_no_position:
                if self.is_enter:
                    place_order(self._ce["symbol"])
                    place_order(self._pe["symbol"])
                    self._timer = pdlm.now()
            else:
                if self._is_roll and pdlm.now() > next_trade:
                    close_positions()
                    place_order(self._ce["symbol"])
                    place_order(self._pe["symbol"])
                    pdlm.now = self._timer


def main():
    try:
        api = get_api()
        ul = dict(
            exchange=dct_sym[SYMBOL]["exch"],
            token=dct_sym[SYMBOL]["token"]
        )
        Stratergy(api, SYMBOL, YAML[SYMBOL], ul).run()
    except Exception as e:
        print(e)
        traceback.print_exc()


if __name__ == "__main__":
    main()
