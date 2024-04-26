from __init__ import logging
from display import Display


def evaluate_conditions(conditions, info, name="unknown condtion"):
    is_any_condition = False
    for condition in conditions:
        try:
            if eval(condition, {}, info):
                Display().at(0, f"{name}: {condition} met")
                is_any_condition = True
                break
        except Exception as e:
            logging.error(
                f"Error evaluating condition: {condition}, Error: {e}")
    return is_any_condition


if __name__ == "__main__":
    # Sample data
    info = {
        "pnl": -50,
        "vwap": 550,
        "price": 600,
        "entry": 600,
    }
    exit_conditions = ["pnl < -10", "price > vwap"]
    entry_conditions = ["price < vwap"]

    # Test the evaluation of entry conditions
    def test_entry_conditions():
        entry_result = evaluate_conditions(entry_conditions, info)
        assert entry_result, "Entry conditions should be met"

    # Test the evaluation of exit conditions
    def test_exit_conditions():
        exit_result = evaluate_conditions(exit_conditions, info)
        assert not exit_result, "Exit conditions should not be met"

    test_entry_conditions()
    test_exit_conditions()
