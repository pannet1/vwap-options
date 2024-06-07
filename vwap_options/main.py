from __init__ import logging, SYMBOL, YAML, START, CMMN
from toolkit.kokoo import is_time_past
from symbols import dct_sym
import traceback
import pendulum as pdlm
from login import get_api
from strategies.straddle import StraddleStrategy
from strategies.vwap import VwapStrategy


def main():
    try:
        while not is_time_past(START):
            print("clock:", pdlm.now().format("HH:mm:ss"), "*z#z~z* till ", START)
        else:
            print("Happy Trading")
            api = get_api()
            ul = dict(exchange=dct_sym[SYMBOL]["exch"], token=dct_sym[SYMBOL]["token"])
            if CMMN["strategy"] == 2:
                print("Starting Straddle Strategy")
                StraddleStrategy(api, SYMBOL, YAML[SYMBOL], ul).run()
            else:
                print("Starting Vwap Strategy")
                VwapStrategy(api, SYMBOL, YAML[SYMBOL], ul).run()

    except Exception as e:
        logging.error(str(e))
        traceback.print_exc()
        SystemExit(0)


if __name__ == "__main__":
    main()
