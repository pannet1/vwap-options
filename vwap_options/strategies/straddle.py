from __init__ import logging, CMMN, DATA, UTIL, STOP
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
        self._strategy = {"old": 0, "pnl": 0, "is_position": False, "is_started": False}
        self._api = api
        self._timer = pdlm.now()
        self._ul = ul
        self._base = base
        self._base_info = base_info
        self._symbol = Symbols(base_info["exchange"], base, base_info["expiry"])
        self._symbol.get_exchange_token_map_finvasia()
        self._strategy["atm"] = self.get_mkt_atm
        self._strategy["spot"] = self.get_mkt_atm
        self._tokens = self._symbol.get_tokens(self._strategy["atm"])
        self._display = Display()

    def enter_position(self, option_type):
        self.update_option(option_type)
        symbol = self._strategy[f"{option_type}_symbol"]
        try:
            flag = False
            logging.debug(f"entering {symbol}")
            args = dict(
                symbol=symbol,
                quantity=str(self._base_info["quantity"]),
                disclosed_quantity=str(self._base_info["quantity"]),
                side="S",
                exchange="NFO",
                product="M",
                order_type="MKT",
                tag="enter",
            )
            resp = self._api.order_place(**args)
            for k, v in self._tokens.items():
                if symbol == v:
                    token = k.split("|")[1]
                    lp = ApiHelper().scriptinfo(self._api, "NFO", token)
                    args["side"] = "B"
                    args["order_type"] = "SL-M"
                    args["price"] = lp
                    args["tag"] = "exit"
                    resp = self._api.order_place(**args)
                    if resp:
                        args["order_id"] = resp
                        flag = True
                        if option_type == "ce":
                            self._strategy["is_ce_position"] = flag
                            self._strategy["ce_stop"] = args
                        else:
                            self._strategy["is_pe_position"] = flag
                            self._strategy["pe_stop"] = args
                        return flag
        except Exception as e:
            logging.error(f"Error enter positions: {e}")
            traceback.print_exc()
        finally:
            return flag

    def exit_position(self, option_type):
        print(f"closing {option_type}")
        resp_stop = self._strategy[f"{option_type}_stop"]
        args = dict(
            order_id=resp_stop["order_id"],
            tradingsymbol=resp_stop["symbol"],
            exchange=resp_stop["exchange"],
        )
        if CMMN["live"] == 1:
            self._api.order_modify(**args)
        else:
            self._api.order_modify(**resp_stop)
        self._strategy[f"is_{option_type}_position"] = False

    def exit_positions(self):
        for pos in self._api.positions:
            logging.debug(f"closing {pos['symbol']}")
            if pos["quantity"] < 0:
                args = dict(
                    symbol=pos["symbol"],
                    quantity=abs(pos["quantity"]),
                    disclosed_quantity=abs(pos["quantity"]),
                    product="M",
                    side="B",
                    order_type="MKT",
                    exchange="NFO",
                    tag="close",
                )
                resp = self._api.order_place(**args)
                logging.debug(args)
                logging.debug(resp)
        self._strategy["entry"] = 0
        self._strategy["is_position"] = False

    @property
    def get_mkt_atm(self):
        lp = ApiHelper().scriptinfo(self._api, self._ul["exchange"], self._ul["token"])
        return self._symbol.get_atm(lp)

    def get_spot_and_mkt_atm(self):
        lp = ApiHelper().scriptinfo(self._api, self._ul["exchange"], self._ul["token"])
        return lp, self._symbol.get_atm(lp)

    def option_info(self, c_or_p):
        option_type = "C" if c_or_p == "ce" else "P"
        return self._symbol.find_option_by_distance(
            self._strategy["atm"],
            self._base_info["away_from_atm"],
            option_type,
            self._tokens,
        )

    def update_option(self, option_type):
        option = self.option_info(option_type)
        try:
            _, price = ApiHelper().historical(
                self._api, self._base_info["exchange"], option["token"]
            )
            spot, atm = self.get_spot_and_mkt_atm()
            self._strategy[f"{option_type}_symbol"] = option["symbol"]
            self._strategy[f"{option_type}_price"] = float(price)
            self._strategy[f"{option_type}_strike"] = extract_strike(option["symbol"])
        except Exception as e:
            logging.error(f"Error updating info: {e}")
            traceback.print_exc()

    def on_start(self):
        try:
            ce = self.option_info("ce")
            pe = self.option_info("pe")
            _, ce_price = ApiHelper().historical(
                self._api, self._base_info["exchange"], ce["token"]
            )
            _, pe_price = ApiHelper().historical(
                self._api, self._base_info["exchange"], pe["token"]
            )
            spot, atm = self.get_spot_and_mkt_atm()

            self._strategy.update(
                {
                    "ce_symbol": ce["symbol"],
                    "pe_symbol": pe["symbol"],
                    "ce_price": float(ce_price),
                    "pe_price": float(pe_price),
                    "ce_strike": extract_strike(ce["symbol"]),
                    "pe_strike": extract_strike(pe["symbol"]),
                    "spot": spot,
                    "atm": atm,
                    "upper_band": spot + self._base_info["band_width"],
                    "lower_band": spot - self._base_info["band_width"],
                    "is_started": True,
                    "is_ce_position": False,
                    "is_pe_position": False,
                }
            )

        except Exception as e:
            logging.error(f"Error getting info: {e}")
            traceback.print_exc()
        finally:
            return self._strategy

    def update_bands(self):
        current_spot = self._strategy["spot"]
        upper_band = self._strategy["upper_band"]
        lower_band = self._strategy["lower_band"]
        band_width = self._base_info["band_width"]

        upper_band_limit = upper_band + band_width * 3
        lower_band_limit = lower_band - band_width * 3

        if current_spot > upper_band_limit:
            self._strategy["upper_band"] = upper_band + band_width

        if current_spot < lower_band_limit:
            self._strategy["lower_band"] = lower_band - band_width

    def on_tick(self):
        try:
            current_spot, atm = self.get_spot_and_mkt_atm()
            self._strategy["spot"] = current_spot
            self.update_bands()
            self._timer = self._timer.add(seconds=60)
            if self._strategy["is_position"]:
                self.check_and_update_position("ce", "upper_band", current_spot)
                self.check_and_update_position("pe", "lower_band", current_spot)

            if not self._strategy["is_position"]:
                self.enter_position("ce")
                self.enter_position("pe")
                if (
                    self._strategy["is_ce_position"]
                    and self._strategy["is_pe_position"]
                ):
                    self._strategy["is_position"] = True

            self._display.at(2, self._strategy)
        except Exception as e:
            logging.error(f"on tick error as {e}")
            traceback.print_exc()

    def check_and_update_position(self, position, band, spot):
        position_key = f"is_{position}_position"
        if self._strategy[position_key]:
            if self.check_spot(spot, band):
                self.exit_position(position)
                self._strategy[position_key] = False
        if not self._strategy[position_key]:
            if not self.check_spot(spot, band):
                self.enter_position(position)
                self._strategy[position_key] = True

    def check_spot(self, spot, band):
        print(f"current_spot: {spot} band: {band}")
        if band == "upper_band":
            return spot > self._strategy[band]
        return spot < self._strategy[band]

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
            self._display.at(3, self._api.positions)
        else:
            if self._strategy["is_position"]:
                logging.debug("closing positions")
                self.exit_positions()
            if not CMMN["live"]:
                self._display.at(3, self._api.positions)
                logging.debug("converting orders to positions in paper mode")
                df = pd.read_csv(DATA + "orders.csv")
                if not df.empty:
                    df = self._api._ord_to_pos(df)
                    df.to_csv(DATA + "positions.csv", index=False)
