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
from evaluate import evaluate_conditions


class Stratergy:
    def enter_positions(self, info):
        try:
            flag = False
            for symbol in [info["ce"], info["pe"]]:
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
            flag = True
            self._strategy["entry"] = info["price"]
            self._strategy["old"] = info["atm"]
            self._strategy["is_position"] = True

        except Exception as e:
            logging.error(f"Error placing orders: {e}")
        finally:
            return flag

    def exit_positions(self):
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
            if all((cv, cc, pv, pc)):
                ce["vwap"] = float(cv)
                ce["price"] = float(cc)
                pe["vwap"] = float(pv)
                pe["price"] = float(pc)

                price = round(ce["price"] + pe["price"], 2)  # 100
                vwap = round(ce["vwap"] + pe["vwap"], 2)  # 102
                pnl = round(vwap - price, 2)  # 2

                self._strategy.update(
                    {
                        "ce": ce["symbol"],
                        "pe": pe["symbol"],
                        "price": price,
                        "vwap": vwap,
                        "pnl": pnl,
                    }
                )

        except Exception as e:
            logging.error(f"Error getting info: {e}")
            traceback.print_exc()
        finally:
            return self._strategy

    def on_tick(self, entry_cond, exit_cond):
        try:
            self._timer = self._timer.add(seconds=CHECK_SECS)
            # check if atm is changed and set it

            self._strategy["atm"] = self.get_mkt_atm
            state = self.info
            if self._strategy["is_position"]:
                if evaluate_conditions(exit_cond, state, "exit conditions"):
                    self.exit_positions()
            else:
                if evaluate_conditions(entry_cond, state, "entry conditions"):
                    self.enter_positions(state)

            self._display.at(2, self._strategy)
        except Exception as e:
            print(f"on tick error as {e}")
            traceback.print_exc()

    def run(self):
        exit_cond, entry_cond = ["atm != old"], []
        try:
            if COND["disable_vwap"] <= 0:
                exit_cond.append(f"pnl < {COND['disable_vwap']}")
            if COND["disable_vwap"] <= 0:
                entry_cond.append("price < vwap")

            if not any(entry_cond):
                entry_cond.append("atm != old")

            print(f"{entry_cond = } \n {exit_cond = }")
        except Exception as e:
            logging.error(f"{e} in conditions")

        while not is_time_past(STOP):
            now = pdlm.now()
            txt = f"now:{now.format('HH:mm:ss')} > next trade:{self._timer.format('HH:mm:ss')} ?"
            self._display.at(1, txt)
            if pdlm.now() > self._timer:
                self.on_tick(entry_cond, exit_cond)
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


def main():
    try:
        while not is_time_past(START):
            print("clock:", pdlm.now().format("HH:mm:ss"), "*z#z~z* till ", START)
        else:
            print("Happy Trading")
            api = get_api()
            ul = dict(exchange=dct_sym[SYMBOL]["exch"], token=dct_sym[SYMBOL]["token"])
            Stratergy(api, SYMBOL, YAML[SYMBOL], ul).run()
    except Exception as e:
        logging.error(str(e))
        traceback.print_exc()
        SystemExit(0)


main()
