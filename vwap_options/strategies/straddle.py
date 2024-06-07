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
    if match:
        return int(match.group(1))
    else:
        return None


class StraddleStrategy:
    def enter_position(self, option_type):
        info = self.info
        # with sl-m order
        try:
            flag = False
            symbol = info[option_type]
            logging.debug(f"entering {symbol}")
            args = dict(
                symbol=symbol,
                quantity=str(self._base_info["quantity"]),
                disclosed_quantity=str(self._base_info["quantity"]),
                side="S",
                exchange="NFO",
                product="M",
                order_type="SL-MKT",
                tag="enter",
                # @TODO: get Current Price
                trigger_price=info["spot"],
            )
            resp = self._api.order_place(**args)
            logging.debug(args)
            logging.debug(resp)
            if symbol == info["ce"]:
                self._strategy["is_ce_position"] = True
            if symbol == info["pe"]:
                self._strategy["is_pe_position"] = True
            flag = True

        except Exception as e:
            logging.error(f"Error placing orders: {e}")
        finally:
            return flag

    def exit_position(self, option_type):
        # @TODO exit position
        print(f"closing {option_type}")
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

    def __init__(self, api, base, base_info, ul):
        self._strategy = {"old": 0, "pnl": 0, "is_position": False}
        self._api = api
        self._timer = pdlm.now()
        self._ul = ul
        self._base = base
        self._base_info = base_info
        self._symbol = Symbols(base_info["exchange"], base, base_info["expiry"])
        self._symbol.get_exchange_token_map_finvasia()

        self._strategy["atm"] = self.get_mkt_atm
        self._tokens = self._symbol.get_tokens(self._strategy["atm"])
        self._display = Display()

    @property
    def get_mkt_atm(self):
        lp = ApiHelper().scriptinfo(self._api, self._ul["exchange"], self._ul["token"])
        return self._symbol.get_atm(lp)

    @property
    def get_spot_and_mkt_atm(self):
        lp = ApiHelper().scriptinfo(self._api, self._ul["exchange"], self._ul["token"])
        return lp, self._symbol.get_atm(lp)

    def option_info(self, c_or_p):
        return self._symbol.find_option_by_distance(
            self._strategy["atm"],
            self._base_info["away_from_atm"],
            c_or_p,
            self._tokens,
        )

    @property
    def info(self):
        try:
            ce = self.option_info("C")
            pe = self.option_info("P")
            cv, cc = ApiHelper().historical(
                self._api, self._base_info["exchange"], ce["token"]
            )
            pv, pc = ApiHelper().historical(
                self._api, self._base_info["exchange"], pe["token"]
            )
            spot, atm = self.get_spot_and_mkt_atm
            ce["price"] = float(cc)
            pe["price"] = float(pc)

            self._strategy.update(
                {
                    "ce": ce["symbol"],
                    "pe": pe["symbol"],
                    "ce_price": ce["price"],
                    "pe_price": pe["price"],
                    "ce_strike": extract_strike(ce["symbol"]),
                    "pe_strike": extract_strike(pe["symbol"]),
                    "spot": spot,
                    "atm": atm,
                    "upper_band": spot + self._base_info["band_width"],
                    "lower_band": spot - self._base_info["band_width"],
                }
            )
            print(f"info: {self._strategy}")

        except Exception as e:
            logging.error(f"Error getting info: {e}")
            traceback.print_exc()
        finally:
            return self._strategy

    def on_tick(self):
        try:
            self._timer = self._timer.add(seconds=60)
            if self._strategy["is_position"]:
                spot = self._strategy["spot"]
                self.check_and_update_position("ce", "upper_band", spot)
                self.check_and_update_position("pe", "lower_band", spot)

            if not self._strategy["is_position"]:
                self.enter_position("ce")
                self.enter_position("pe")
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
        print(f"spot: {spot} band: {band}")
        if band == "upper_band":
            return spot > self._strategy[band]
        return spot < self._strategy[band]

    def run(self):
        while not is_time_past(STOP):
            now = pdlm.now()
            txt = f"now:{now.format('HH:mm:ss')} > next trade:{self._timer.format('HH:mm:ss')} ?"
            self._display.at(1, txt)
            if pdlm.now() > self._timer:
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
