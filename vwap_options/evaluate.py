from __init__ import logging


def evaluate_conditions(conditions, info):
    # Function to evaluate conditions
    is_any_condition = False
    exceptions = []
    for condition in conditions:
        try:
            if eval(condition, {}, info):
                print(f"{condition} met")
                is_any_condition = True
                break
        except Exception as e:
            print(f"Error evaluating condition: {condition}, Error: {e}")
            exceptions.append(str(e))
            # Continue evaluating other conditions
            is_any_condition = False
    return is_any_condition, exceptions


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
        entry_result, entry_exceptions = evaluate_conditions(entry_conditions, info)
        assert entry_result, "Entry conditions should be met"
        assert (
            entry_exceptions == []
        ), "No exceptions should be raised for entry conditions"

    # Test the evaluation of exit conditions
    def test_exit_conditions():
        exit_result, exit_exceptions = evaluate_conditions(exit_conditions, info)
        assert not exit_result, "Exit conditions should not be met"
        assert (
            exit_exceptions == []
        ), "No exceptions should be raised for exit conditions"

    test_entry_conditions()
    test_exit_conditions()
