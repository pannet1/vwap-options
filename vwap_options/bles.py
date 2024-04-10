from blessed import Terminal
import pandas as pd


def display_at(term, line, data):
    with term.location(0, line):
        print(term.clear_eol(), data, end="")


def display(term, data):
    display_at(term, term.height - 3, data)  # Display data dictionary


term = Terminal()
i = 1
while True:
    data = {
        "key1": i + 1,
        "key2": i + 2,
    }
    display(term, data)
    i += 1
