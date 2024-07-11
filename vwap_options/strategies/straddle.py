from __init__ import logging, CMMN, DATA, UTIL, STOP, COND
from toolkit.kokoo import is_time_past
from symbols import Symbols
import traceback
import pendulum as pdlm
from api_helper import ApiHelper
from display import Display
import pandas as pd
import re


def extract_strike(symbol):
    match = re.search(r"[CP](\d+)$", symbol)
    return int(match.group(1)) if match else None


class StraddleStrategy:
    def __init__(self, api, base, base_info, ul):
        self._strategy = {"is_started": False}
        self._ce = {"is_position": False}
        self._pe = {"is_position": True}
        self._api = api
        self._timer = pdlm.now()
        self._ul = ul
        self._base = base
        self._base_info = base_info
        self._symbol = Symbols(base_info["exchange"], base, base_info["expiry"])
        self._symbol.get_exchange_token_map_finvasia()
        self._display = Display()

    def place_order(self, option_type):
        try:
            if option_type == "ce":
                symbol = self._ce["ce"]
                self._ce["is_position"] = True
            else:
                symbol = self._pe["pe"]
                self._pe["is_position"] = True
            logging.debug(f"entering {symbol}")
            args = dict(
                symbol=symbol,
                quantity=str(self._base_info["quantity"]),
                side="S",
                exchange="NFO",
                product="M",
                order_type="MKT",
                tag="enter",
            )
            resp = self._api.order_place(**args)
            logging.debug(resp)
        except Exception as e:
            logging.error(f"Error enter positions: {e}")
            traceback.print_exc()

    def exit_position(self, option_type):
        try:
            if option_type == "ce":
                symbol = self._ce["ce"]
                self._ce["is_position"] = False
            else:
                symbol = self._pe["pe"]
                self._pe["is_position"] = False
            logging.debug(f"closing {symbol}")
            args = dict(
                symbol=symbol,
                quantity=str(self._base_info["quantity"]),
                side="B",
                exchange="NFO",
                product="M",
                order_type="MKT",
                tag="close",
            )
            resp = self._api.order_place(**args)
            logging.debug(resp)
        except Exception as e:
            logging.error(f"Error enter positions: {e}")
            traceback.print_exc()

    def exit_positions(self):
        for pos in self._api.positions:
            logging.debug(f"closing {pos['symbol']}")
            if pos["quantity"] < 0:
                args = dict(
                    symbol=pos["symbol"],
                    quantity=abs(pos["quantity"]),
                    product="M",
                    side="B",
                    order_type="MKT",
                    exchange="NFO",
                    tag="close",
                )
                resp = self._api.order_place(**args)
                logging.debug(args)
                logging.debug(resp)

    def get_spot_and_mkt_atm(self):
        lp = ApiHelper().scriptinfo(self._api, self._ul["exchange"], self._ul["token"])
        return lp, self._symbol.get_atm(lp)

    def option_info(self, c_or_p):
        option_type = "C" if c_or_p == "ce" else "P"
        _, atm = self.get_spot_and_mkt_atm()
        return self._symbol.find_option_by_distance(
            atm,
            self._base_info["away_from_atm"],
            option_type,
            self._tokens,
        )

    def on_start(self):
        try:
            spot, atm = self.get_spot_and_mkt_atm()
            self._tokens = self._symbol.get_tokens(atm)
            self._strategy["spot"] = spot
            self._strategy["atm"] = atm
            self._ce["band"] = spot + self._base_info["band_width"]
            self._pe["band"] = spot - self._base_info["band_width"]
            self._strategy["is_started"] = True
            for option_type in ["ce", "pe"]:
                option = self.option_info(option_type)
                if option_type == "ce":
                    self._ce["ce"] = option["symbol"]
                    self._ce["is_position"] = False
                else:
                    self._pe["pe"] = option["symbol"]
                    self._pe["is_position"] = True
                self.place_order(option_type)
        except Exception as e:
            logging.error(f"Error on start: {e}")
            traceback.print_exc()

    def update_bands(self, current_spot):
        upper_band = self._ce["band"]
        lower_band = self._pe["band"]
        band_width = self._base_info["band_width"]

        upper_band_limit = upper_band + band_width * 3
        lower_band_limit = lower_band - band_width * 3

        if current_spot > upper_band_limit:
            self._ce["band"] = upper_band + band_width

        if current_spot < lower_band_limit:
            self._pe["band"] = lower_band - band_width

    def on_tick(self):
        try:
            current_spot, _ = self.get_spot_and_mkt_atm()
            self._strategy["spot"] = current_spot
            if COND["trailing"]:
                self.update_bands(current_spot)
            self._timer = self._timer.add(seconds=60)
            for option_type in ["ce", "pe"]:
                self.check_and_update_position(option_type)
            self._display.at(2, self._strategy)
            self._display.at(3, self._ce)
            self._display.at(4, self._pe)
            logging.info(
                f'on tick {current_spot=} ce {self._ce["is_position"]} pe {self._pe["is_position"]}'
            )
        except Exception as e:
            logging.error(f"on tick error as {e}")
            traceback.print_exc()

    def check_and_update_position(self, option_type):
        spot = self._strategy["spot"]
        option = getattr(self, f"_{option_type}")
        if option["is_position"]:
            if self.check_spot(spot, option_type):
                self.exit_position(option_type)
                option["is_position"] = False
                setattr(self, f"_{option_type}", option)
        if not option["is_position"]:
            if not self.check_spot(spot, option_type):
                self.place_order(option_type)

    def check_spot(self, spot, option_type):
        if option_type == "ce":
            return spot > self._ce["band"]
        return spot < self._pe["band"]

    def run(self):
        while not is_time_past(STOP):
            now = pdlm.now()
            txt = f"now:{now.format('HH:mm:ss')} > next trade:{self._timer.format('HH:mm:ss')} ?"
            self._display.at(1, txt)
            if pdlm.now() > self._timer:
                if not self._strategy["is_started"]:
                    self.on_start()
                self.on_tick()
            else:
                UTIL.slp_for(1)
            try:
                self._display.at(5, self._api.positions)
            except Exception as e:
                logging.error(f"{e} in display()")

        else:
            if self._strategy["is_started"]:
                self.exit_positions()
                self._strategy["is_started"] = False
            if not CMMN["live"]:
                self._display.at(5, self._api.positions)
                logging.debug("converting orders to positions in paper mode")
                df = pd.read_csv(DATA + "orders.csv")
                if not df.empty:
                    df = self._api._ord_to_pos(df)
                    df.to_csv(DATA + "positions.csv", index=False)
