from __init__ import DATA
import pandas as pd
from login import get_api


def run():
    api = get_api()
    df = pd.read_csv(DATA + "orders.csv")
    df = api._ord_to_pos(df)
    print(df)
    df.to_csv(DATA + "positions.csv", index=False)


run()
