from __init__ import logging, CMMN, SYMBOL, DATA, YAML, UTIL
from __init__ import CHECK_SECS, START, STOP, COND
from symbols import Symbols, dct_sym
import traceback
import pendulum as pdlm
from api_helper import ApiHelper
from login import get_api
from clock import is_time_past
from display import Display
import pandas as pd


class Stratergy:
    def place_order(self, symbol):
        logging.debug(f"entering {symbol}")
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
            logging.debug(f"closing {pos['symbol']}")
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

        self._atm = 0
        self._tokens = self._symbol.get_tokens(self.atm)
        self._display = Display()

    @property
    def atm(self):
        lp = ApiHelper().scriptinfo(
            self._api, self._ul["exchange"], self._ul["token"])
        return self._symbol.get_atm(lp)

    @property
    def ce(self):
        return self._symbol.find_option_by_distance(
            self._atm, self._base_info["away_from_atm"], "C", self._tokens
        )

    @property
    def pe(self):
        return self._symbol.find_option_by_distance(
            self._atm, self._base_info["away_from_atm"], "P", self._tokens
        )

    @property
    def info(self):
        pe = self.pe
        ce = self.ce
        if pe and ce:
            self._pe = pe
            self._ce = ce
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
        print(lst_of_pos)
        is_pos = False
        if any(lst_of_pos):
            for pos in lst_of_pos:
                if pos["quantity"] != 0:
                    is_pos = True
                    break
        return is_pos

    @property
    def get_atm(self):
        atm = self.atm
        txt = f"atm before: {self._atm} atm now: {atm}"
        self._display.at(1, txt)
        if atm != self._atm:
            return atm
        """
        if self._strategy["price"] < self._strategy["vwap"]:
            print("entry condition is True")
            return True
        """
        return 0

    def on_tick(self):
        self._timer = self._timer.add(seconds=CHECK_SECS)
        # check if atm is changed and set it
        atm = self.get_atm
        if atm > 0:
            # close positions if any before changing the atm
            if self._is_position:
                self.close_positions()
            # set atm
            self._atm = atm

        # get info for the current atm
        info = self.info
        if atm > 0:
            self.place_order(self._ce["symbol"])
            self.place_order(self._pe["symbol"])
            self._is_position = True
        self._display.at(3, info)

    def run(self):
        D_COND = {}
        try:
            if COND["sl_points"] > 0:
                D_COND["sl"] == COND["sl_points"] * 0.05
            if COND["vwap"] > 0:
                D_COND["vwap"] == COND["vwap"]
        except Exception as e:
            logging.error(f"{e} in conditions")

        while not is_time_past(STOP):
            now = pdlm.now()
            txt = f"now:{now.format('HH:mm:ss')} > next trade:{self._timer.format('HH:mm:ss')} ?"
            self._display.at(2, txt)
            if pdlm.now() > self._timer:
                self.on_tick()
            else:
                UTIL.slp_for(1)
            self._display.at(6, self._api.positions)
        else:
            if self._is_position:
                logging.debug("closing positions")
                self.close_positions()
            if not CMMN["live"]:
                self._display.at(7, self._api.positions)
                logging.debug("converting orders to positions in paper mode")
                df = pd.read_csv(DATA + "orders.csv")
                if not df.empty:
                    df = self._api._ord_to_pos(df)
                    df.to_csv(DATA + "positions.csv", index=False)


def main():
    try:
        while not is_time_past(START):
            print("clock:", pdlm.now().format(
                "HH:mm:ss"), "*z#z~z* till ", START)
        else:
            print("Happy Trading")
            api = get_api()
            ul = dict(exchange=dct_sym[SYMBOL]["exch"],
                      token=dct_sym[SYMBOL]["token"])
            Stratergy(api, SYMBOL, YAML[SYMBOL], ul).run()
    except Exception as e:
        logging.error(str(e))
        traceback.print_exc()
        SystemExit(0)


main()
