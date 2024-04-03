from __init__ import logging,  FILS, F_POS, SYMBOL, YAML, UTIL
from symbols import Symbols, dct_sym
import traceback
from rich import print
import pendulum as pdlm
from api_helper import ApiHelper, get_api

CHECK_IN_SECS = 60


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
    def is_position(self):
        lst_of_pos = self._api.positions
        # find if list of positions is not empty and
        # if quantity is not equal to zero
        print(f"positions \n{lst_of_pos}")
        is_pos = False
        if any(lst_of_pos):
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
        logging.debug(
            f"is_enter price: {self._strategy['price']} < vwap: {self._strategy['vwap']}")
        if self._strategy["price"] < self._strategy["vwap"]:
            return True
        return False

    def run(self):
        def place_order(symbol):
            args = dict(
                symbol=symbol,
                side="S",
                quantity=self._base_info["quantity"],
                exchange="NFO",
                product="MIS",
                order_type="MARKET",
                tag="enter",
            )
            if not CMMN["live"]:
                args["price"] = self._ce["price"]
            self._api.order_place(**args)

        def close_positions():
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
                    if not CMMN["live"]:
                        ret = self._api.finvasia.searchscrip(
                            "NFO", pos["symbol"])
                        if ret is not None:
                            token = ret['values'][0]['token']
                            args["price"] = self._api.scriptinfo(
                                "NFO", pos["symbol"], token
                            )
                    self._api.order_place(**args)

        while True:
            next_trade = self._timer.add(seconds=CHECK_IN_SECS)
            print(f"next trade:{next_trade.to_datetime_string()}")
            print(self.info)
            UTIL.slp_for(5)
            if self.is_position:
                if self._is_roll and pdlm.now() > next_trade:
                    close_positions()
                    place_order(self._ce["symbol"])
                    place_order(self._pe["symbol"])
                    pdlm.now = self._timer
            else:
                if self.is_enter:
                    place_order(self._ce["symbol"])
                    place_order(self._pe["symbol"])
                    self._timer = pdlm.now()


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


main()
