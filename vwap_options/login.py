
from omspy_brokers.finvasia import Finvasia
from paper import Paper
from __init__ import CMMN, CNFG, logging


def get_api():
    if CMMN["live"]:
        api = Finvasia(**CNFG)
    else:
        api = Paper(**CNFG)
    if not api.authenticate():
        logging.error("Failed to authenticate")
        SystemExit()
    return api
