from omspy_brokers.finvasia import Finvasia
from paper import Paper
from __init__ import CMMN, CNFG, logging, DATA
import pandas as pd


def get_api():
    if CMMN["live"]:
        api = Finvasia(**CNFG)
    else:
        api = Paper(**CNFG)
    if not api.authenticate():
        logging.error("Failed to authenticate")
        SystemExit()
    return api


if __name__ == "__main__":
    api = get_api()
    ord = api.orders
    print(ord)
    pd.DataFrame(ord).to_csv(DATA + "orders.csv", index=False)
    pos = api.positions
    print(pos)
    pd.DataFrame(pos).to_csv(DATA + "positions.csv", index=False)
