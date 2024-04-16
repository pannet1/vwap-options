import pandas as pd

try:
    from blessed import Terminal
except ModuleNotFoundError:
    print("blessed module not found. Install it with 'pip install blessed'")
    __import__("os").system("pip install blessed")
    __import__("time").sleep(5)
    from blessed import Terminal


class Display:
    def __init__(self):
        self.term = Terminal()

    def show(self, data, line):
        with self.term.location(0, line):
            print(self.term.clear_eol(), data, end="")

    def at(self, line, data):
        if isinstance(data, pd.DataFrame):
            data = data.to_string(index=False)
        elif isinstance(data, list):
            for item in data:
                self.show(str(item), line)
                line += 1
            data = ""
        elif isinstance(data, dict):
            item = ""
            for key, val in data.items():
                item += key + " " + str(val) + " "
                if isinstance(val, dict):
                    item += "\n"
            data = item
        self.show(data, line)


if __name__ == "__main__":
    import pendulum as pdlm
    from __init__ import START

    display = Display()
    i = 1
    while True:
        data = {
            "key1": i + 1,
            "key2": i + 2,
        }
        timestr = "clock:", pdlm.now().format("HH:mm:ss"), "zzz for ", START
        display.at(1, timestr)
        display.at(2, data)
        i += 1
