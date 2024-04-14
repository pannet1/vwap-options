import pandas as pd

try:
    from blessed import Terminal
except ModuleNotFoundError:
    print("blessed module not found. Install it with 'pip install blessed'")
    __import__("os").system("pip install blessed")
    __import__("time").sleep(5)
    from blessed import Terminal


def display_at(term, line, data):
    with term.location(0, line):
        print(term.clear_eol(), data, end="")


def display(term, data):
    # display_at(term, term.height - 3, data)  # Display data dictionary
    display_at(term, 1, data)  # Display data dictionary
    display_at(
        term, 3, pd.DataFrame([data]).to_string(index=False)
    )  # Display DataFrame content


term = Terminal()
i = 1
while True:
    data = {
        "key1": i + 1,
        "key2": i + 2,
    }
    display(term, data)
    i += 1
