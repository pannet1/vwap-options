from __init__ import logging, SYMBOL, YAML, UTIL
from symbols import Symbols, dct_sym
import traceback
from rich import print
import pendulum as pdlm
from api_helper import ApiHelper
from login import get_api
from clock import is_time_past

CHECK_IN_SECS = 30
T_START = "9:16:00"


class Stratergy:
    def place_order(self, symbol):
        args = dict(
            symbol=symbol,
            side="S",
            quantity=self._base_info["quantity"],
            exchange="NFO",
            product="MIS",
            order_type="MARKET",
            tag="enter",
        )
        self._api.order_place(**args)

    def close_positions(self):
        for pos in self._api.positions:
            if pos["quantity"] < 0:
                args = dict(
                    symbol=pos["symbol"],
                    side="B",
                    quantity=abs(pos["quantity"]),
                    exchange="NFO",
                    product="MIS",
                    order_type="MARKET",
                    tag="close",
                )
                self._api.order_place(**args)

    def __init__(self, api, base, base_info, ul):
        self._is_position = False
        self._api = api
        self._timer = pdlm.now()
        self._ul = ul
        self._base = base
        self._base_info = base_info
        self._symbol = Symbols(
            base_info["exchange"], base, base_info["expiry"])
        self._symbol.get_exchange_token_map_finvasia()

        self._atm = self.atm
        self._tokens = self._symbol.get_tokens(self._atm)

    @property
    def atm(self):
        lp = ApiHelper().scriptinfo(
            self._api, self._ul["exchange"], self._ul["token"])
        return self._symbol.get_atm(lp)

    @property
    def ce(self):
        self._ce = self._symbol.find_option_by_distance(
            self._atm, self._base_info["away_from_atm"], "C", self._tokens
        )
        return self._ce

    @property
    def pe(self):
        self._pe = self._symbol.find_option_by_distance(
            self._atm, self._base_info["away_from_atm"], "P", self._tokens
        )
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
                "vwap": self._vwap,
            }
        return self._strategy

    @property
    def is_quantity(self):
        """
        not implemented
        """
        lst_of_pos = self._api.positions
        print(f"positions \n{lst_of_pos}")
        is_pos = False
        if any(lst_of_pos):
            for pos in lst_of_pos:
                if pos["quantity"] != 0:
                    is_pos = True
                    break
        return is_pos

    @property
    def is_enter(self):
        print(self._atm)
        if (atm := self.atm) != self._atm:
            self._atm = atm
            return True
        """
        if self._strategy["price"] < self._strategy["vwap"]:
            print("entry condition is True")
            return True
        """
        return False

    def on_tick(self):
        self._timer = self._timer.add(seconds=CHECK_IN_SECS)

        flag = False
        if self.is_enter:
            flag = True
        print(self.info)
        if flag:
            if self._is_position:
                self.close_positions()
            else:
                self._is_position = True
            self.place_order(self._ce["symbol"])
            self.place_order(self._pe["symbol"])
        """
        self._positions = self._api.positions
        print(self._positions)
        """

    def run(self):
        while True:
            now = pdlm.now()
            print(
                f"now:{now.format('HH:mm:ss')} > next trade:{self._timer.format('HH:mm:ss')} ?"
            )
            if pdlm.now() > self._timer:
                self.on_tick()
            else:
                UTIL.slp_for(1)
            print(self._api.orders)


def main():
    try:
        api = get_api()
        ul = dict(exchange=dct_sym[SYMBOL]["exch"],
                  token=dct_sym[SYMBOL]["token"])
        while not is_time_past(T_START):
            print("clock:", pdlm.now().format("HH:mm:ss"), "zzz for ", T_START)
        else:
            print("Happy Trading")
            Stratergy(api, SYMBOL, YAML[SYMBOL], ul).run()
    except Exception as e:
        print(e)
        traceback.print_exc()


main()
