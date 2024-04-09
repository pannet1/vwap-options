import pendulum as pdlm
import traceback
from rich import print
from __init__ import UTIL
from typing import List, Dict


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
            return float(resp["lp"])
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
                hour=9, minute=15, second=0, microsecond=0)
            resp = api.historical(
                exchange, token, fromBusDay.timestamp(), lastBusDay.timestamp(), 1
            )
            print(resp)
            filtered = filter_by_keys(lst_white, resp)
            # find the average by key intvwap in the filtered list
            for dct in filtered:
                dct["ivc"] = dct["intv"] * dct["intc"]
            vwap = sum_by_key("ivc") / sum_by_key("intv")
            ApiHelper.count += 1
            ApiHelper.second = pdlm.now().second
            return vwap, resp[0]["intc"]
        except Exception as e:
            print(e)
            traceback.print_exc()


if __name__ == "__main__":
    import pandas as pd
    from symbols import dct_sym

    """
    ul = dict(
        exchange=dct_sym[SYMBOL]["exch"],
        token=dct_sym[SYMBOL]["token"]
    )
    lastBusDay = pdlm.now()
    fromBusDay = lastBusDay.replace(
        hour=9, minute=15, second=0, microsecond=0
    ).subtract(days=10)
    lp = api.historical(ul["exchange"], ul["token"],
                        fromBusDay.timestamp(), lastBusDay.timestamp(), 15)
    pd.DataFrame(lp).to_csv("history.csv")
    """
