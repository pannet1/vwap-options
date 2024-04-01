from omspy_brokers.finvasia import Finvasia
from random import randint
import pendulum as plum
import pandas as pd
from __init__ import DATA


def calc_m2m(pos):
    if pos["quantity"] > 0:
        sold = int(pos["quantity"]) * int(pos["last_price"])
        return sold - pos["bought"]
    elif pos["quantity"] < 0:
        return pos["sold"] - (abs(pos["quantity"]) * pos["last_price"])
    elif pos["quantity"] == 0:
        return 0


class Simulate:

    def __init__(self, exchtkn: list, dct_tokens: dict):
        self.exchtkn = exchtkn
        self.dct_tokens = dct_tokens

    @property
    def ltp(self):
        dct = {}
        for token in self.exchtkn:
            symbol = self.dct_tokens[token]
            dct[symbol] = randint(1, 200) * 0.05
        return dct


class Paper(Finvasia):
    cols = ["entry_time", "side", "filled_quantity",
            "symbol", "average_price", "remark"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._orders = pd.DataFrame()

    @property
    def orders(self):
        return self._orders

    def order_place(self, **position_dict):
        args = dict(
            broker_timestamp=plum.now().to_time_string(),
            side=position_dict["side"],
            filled_quantity=int(position_dict["quantity"]),
            symbol=position_dict["symbol"],
            status="COMPLETED",
            average_price=position_dict["price"],
            remarks=position_dict["tag"],
        )
        if not self._orders.empty:
            self._orders = pd.concat(
                [self._orders, pd.DataFrame([args])], ignore_index=True)
        else:
            self._orders = pd.DataFrame(columns=self.cols, data=[args])

    @property
    def positions(self):
        lst = []
        df = self.orders
        if not self.orders.empty:
            df_buy = df[df.side == "B"][[
                "symbol", "filled_quantity", "average_price"]]
            df_sell = df[df.side == "S"][[
                "symbol", "filled_quantity", "average_price"]]
            df = pd.merge(df_buy, df_sell,
                          on="symbol",
                          suffixes=("_buy", "_sell"),
                          how="outer"
                          ).fillna(0)
            df["bought"] = df.filled_quantity_buy * df.average_price_buy
            df["sold"] = df.filled_quantity_sell * df.average_price_sell
            df["quantity"] = df.filled_quantity_buy - df.filled_quantity_sell
            df = df.groupby("symbol").sum().reset_index()
            lst = df.to_dict(orient="records")
            for pos in lst:
                token = self.instrument_symbol(base["EXCHANGE"], pos["symbol"])
                resp = self.scriptinfo(base["EXCHANGE"], token)
                pos["last_price"] = float(resp["lp"])
                pos["urmtom"] = pos["quantity"]
                pos["urmtom"] = calc_m2m(pos)
                pos["rpnl"] = (pos["sold"] - pos["bought"]
                               ) if pos["quantity"] == 0 else 0
            keys = ['symbol', 'quantity', 'urmtom', 'rpnl', 'last_price']
            lst = [
                {k: d[k] for k in keys} for d in lst]
            df.to_csv(DATA + "positions.csv", index=False)
        return lst


if __name__ == "__main__":
    from __init__ import common
    from symbols import Symbols
    SYMBOL = common["base"]
    obj_sym = Symbols(base['EXCHANGE'], SYMBOL, base["EXPIRY"])
    obj_sym.get_exchange_token_map_finvasia()

    dct_tokens = obj_sym.get_tokens(20250)
    lst_tokens = list(dct_tokens.keys())
    """
    brkr = Simulate(lst_tokens, dct_tokens)

    args = dict(
        broker_timestamp=plum.now().to_time_string(),
        side="B",
        quantity="50",
        symbol=SYMBOL + base['EXPIRY'] + "C" + "23500",
        tag="paper",
    )
    brkr.order_place(**args)
    args.update({"side": "S", "symbol": SYMBOL +
                base['EXPIRY'] + "P" + "22400"})
    brkr.order_place(**args)
    args.update({"side": "S", "symbol": SYMBOL +
                base['EXPIRY'] + "P" + "22400"})
    brkr.order_place(**args)
    args.update({"side": "B", "symbol": SYMBOL +
                base['EXPIRY'] + "P" + "22400"})
    brkr.order_place(**args)

    kwargs = {
        "pos": brkr.positions
    }
    prettier(**kwargs)
    """
