import pandas as pd

def highlight_subtotals(row):
    """
    Highlights subtotal rows:
    - Bold text
    - Light gray background (#f0f0f0)
    """
    if "total " in str(row["Category"]).lower():
        return ["font-weight: bold; background-color: #f0f0f0"] * len(row)
    return [""] * len(row)
