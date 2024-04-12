from omspy_brokers.finvasia import Finvasia
from random import randint
import pendulum as plum
import pandas as pd
from api_helper import ApiHelper
from __init__ import DATA, FILS


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
    cols = [
        "broker_timestamp",
        "side",
        "filled_quantity",
        "symbol",
        "remarks",
        "average_price",
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._orders = pd.DataFrame()
        if FILS.is_file_not_2day(DATA + "orders.csv"):
            FILS.nuke_file(DATA + "orders.csv")

    @property
    def orders(self):
        return self._orders

    def order_place(self, **position_dict):
        try:
            args = dict(
                broker_timestamp=plum.now().format("YYYY-MM-DD HH:mm:ss"),
                side=position_dict["side"],
                filled_quantity=int(position_dict["quantity"]),
                symbol=position_dict["symbol"],
                remarks=position_dict["tag"],
                average_price=0,
            )
            ret = self.finvasia.searchscrip("NFO", position_dict["symbol"])
            if ret is not None:
                token = ret["values"][0]["token"]
                args["average_price"] = ApiHelper().scriptinfo(self, "NFO", token)

            df = pd.DataFrame(columns=self.cols, data=[args])

            if not self._orders.empty:
                df = pd.concat([self._orders, df], ignore_index=True)
            self._orders = df
        except Exception as e:
            print(e)

    def _ord_to_pos(self, df):
        # Filter DataFrame to include only 'B' (Buy) side transactions
        buy_df = df[df["side"] == "B"]

        # Filter DataFrame to include only 'S' (Sell) side transactions
        sell_df = df[df["side"] == "S"]

        # Group by 'symbol' and sum 'filled_quantity' for 'B' side transactions
        buy_grouped = (
            buy_df.groupby("symbol")
            .agg({"filled_quantity": "sum", "average_price": "sum"})
            .reset_index()
        )
        # Group by 'symbol' and sum 'filled_quantity' for 'S' side transactions
        sell_grouped = (
            sell_df.groupby("symbol")
            .agg({"filled_quantity": "sum", "average_price": "sum"})
            .reset_index()
        )
        # Merge the two DataFrames on 'symbol' column with a left join
        result_df = pd.merge(
            buy_grouped,
            sell_grouped,
            on="symbol",
            suffixes=("_buy", "_sell"),
            how="outer",
        )

        result_df.fillna(0, inplace=True)
        # Calculate the net filled quantity by subtracting 'Sell' side quantity from 'Buy' side quantity

        result_df["quantity"] = (
            result_df["filled_quantity_buy"] - result_df["filled_quantity_sell"]
        )
        result_df["urmtom"] = result_df.apply(
            lambda row: 0
            if row["quantity"] == 0
            else (row["average_price_buy"] - row["filled_quantity_sell"])
            * row["quantity"],
            axis=1,
        )
        result_df["rpnl"] = result_df.apply(
            lambda row: row["average_price_sell"] - row["average_price_buy"]
            if row["quantity"] == 0
            else 0,
            axis=1,
        )
        result_df.drop(
            columns=[
                "filled_quantity_buy",
                "filled_quantity_sell",
                "average_price_buy",
                "average_price_sell",
            ],
            inplace=True,
        )
        return result_df

    @property
    def positions(self):
        lst = []
        df = self.orders
        df.to_csv(DATA + "orders.csv", index=False)
        if not self.orders.empty:
            df = self._ord_to_pos(df)
            lst = df.to_dict(orient="records")
            """
            for pos in lst:
                token = self.instrument_symbol(
                    SYMBOL["EXCHANGE"], pos["symbol"])
                resp = self.scriptinfo(SYMBOL["EXCHANGE"], token)
                pos["last_price"] = float(resp["lp"])
                pos["urmtom"] = pos["quantity"]
                pos["urmtom"] = calc_m2m(pos)
                pos["rpnl"] = (pos["sold"] - pos["bought"]
                               ) if pos["quantity"] == 0 else 0
            keys = ['symbol', 'quantity', 'urmtom', 'rpnl', 'last_price']
            lst = [
                {k: d[k] for k in keys} for d in lst]
            """
        return lst


if __name__ == "__main__":
    from __init__ import YAML, SYMBOL
    from symbols import Symbols

    base = YAML[SYMBOL]

    obj_sym = Symbols(base["exchange"], SYMBOL, base["expiry"])
    obj_sym.get_exchange_token_map_finvasia()

    dct_tokens = obj_sym.get_tokens(20250)
    lst_tokens = list(dct_tokens.keys())
    df = pd.read_csv(DATA + "orders.csv")
    # Filter DataFrame to include only 'B' (Buy) side transactions
    buy_df = df[df["side"] == "B"]

    # Filter DataFrame to include only 'S' (Sell) side transactions
    sell_df = df[df["side"] == "S"]

    # Group by 'symbol' and sum 'filled_quantity' for 'B' side transactions
    buy_grouped = (
        buy_df.groupby("symbol")
        .agg({"filled_quantity": "sum", "average_price": "sum"})
        .reset_index()
    )
    # Group by 'symbol' and sum 'filled_quantity' for 'S' side transactions
    sell_grouped = (
        sell_df.groupby("symbol")
        .agg({"filled_quantity": "sum", "average_price": "sum"})
        .reset_index()
    )
    # Merge the two DataFrames on 'symbol' column with a left join
    result_df = pd.merge(
        buy_grouped, sell_grouped, on="symbol", suffixes=("_buy", "_sell"), how="outer"
    )

    result_df.fillna(0, inplace=True)

    """
    brkr = Simulate(lst_tokens, dct_tokens)

    args = dict(
        broker_timestamp=plum.now().to_time_string(),
        side="B",
        quantity="50",
        symbol=SYMBOL + SYMBOL['EXPIRY'] + "C" + "23500",
        tag="paper",
    )
    brkr.order_place(**args)
    args.update({"side": "S", "symbol": SYMBOL +
                SYMBOL['EXPIRY'] + "P" + "22400"})
    brkr.order_place(**args)
    args.update({"side": "S", "symbol": SYMBOL +
                SYMBOL['EXPIRY'] + "P" + "22400"})
    brkr.order_place(**args)
    args.update({"side": "B", "symbol": SYMBOL +
                SYMBOL['EXPIRY'] + "P" + "22400"})
    brkr.order_place(**args)

    kwargs = {
        "pos": brkr.positions
    }
    prettier(**kwargs)
    """
