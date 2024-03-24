import logging
import time


class Wserver:
    # flag to tell us if the websocket is open
    socket_opened = False
    ltp = {}

    def __init__(self, broker, tokens, dct_tokens):
        self.api = broker.finvasia
        self.tokens = tokens
        self.dct_tokens = dct_tokens
        ret = self.api.start_websocket(
            order_update_callback=self.event_handler_order_update,
            subscribe_callback=self.event_handler_quote_update,
            socket_open_callback=self.open_callback,
        )
        if ret:
            logging.debug(f"{ret} ws started")

    def open_callback(self):
        self.socket_opened = True
        print("app is connected")
        self.api.subscribe(self.tokens, feed_type="d")
        # api.subscribe(['NSE|22', 'BSE|522032'])

    # application callbacks
    def event_handler_order_update(self, message):
        logging.info("order event: " + str(message))

    def event_handler_quote_update(self, message):
        # e   Exchange
        # tk  Token
        # lp  LTP
        # pc  Percentage change
        # v   volume
        # o   Open price
        # h   High price
        # l   Low price
        # c   Close price
        # ap  Average trade price
        #
        logging.debug(
            "quote event: {0}".format(time.strftime(
                "%d-%m-%Y %H:%M:%S")) + str(message)
        )
        val = message.get("lp", False)
        if val:
            exch_tkn = message["e"] + "|" + message["tk"]
            self.ltp[self.dct_tokens[exch_tkn]] = float(val)


if __name__ == "__main__":
    from omspy_brokers.finvasia import Finvasia
    from constants import base, logging, common, cnfg, data, fils
    from symbols import Symbols
    from paper import Paper
    from time import sleep
    import sys

    PAPER_ATM = 47500
    slp = 2
    SYMBOL = common["base"]

    obj_sym = Symbols(base['EXCHANGE'], SYMBOL, base["EXPIRY"])
    obj_sym.get_exchange_token_map_finvasia()

    def get_brkr_and_wserver():
        if common["live"]:
            brkr = Finvasia(**cnfg)
            if not brkr.authenticate():
                logging.error("Failed to authenticate")
                sys.exit(0)
            else:
                dct_tokens = obj_sym.get_tokens(PAPER_ATM)
                lst_tokens = list(dct_tokens.keys())
                wserver = Wserver(brkr, lst_tokens, dct_tokens)
        else:
            dct_tokens = obj_sym.get_tokens(PAPER_ATM)
            lst_tokens = list(dct_tokens.keys())
            brkr = Paper(lst_tokens, dct_tokens)
            wserver = brkr
        return brkr, wserver

    if common["live"]:
        broker = Finvasia(**cnfg)
        if not broker.authenticate():
            logging.error("Failed to authenticate")
            sys.exit(0)
    wserver = Wserver(
        broker,
        ["NSE|26000", "NFO|43156"],
        {"NSE|26000": "NIFTY 50", "NFO|43156": "DUMMY"},
    )
    while True:
        print(wserver.ltp)
        time.sleep(1)
