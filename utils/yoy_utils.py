import pandas as pd
from utils.data_utils import compute_yoy

def compute_six_category_yoy(subtotals, selected_years):
    yoy = compute_yoy(subtotals)
    yoy = yoy[yoy["Year"].isin(selected_years)]

    yoy["Category"] = yoy["Category"].replace({
        "Total Revenue (Auto)": "Total Revenue",
        "Total Income (Auto)": "Total Income",
        "Total Expenses (Auto)": "Total Expenses",
        "Net Income (Auto)": "Net Income",
    })

    board = yoy[yoy["Category"].isin([
        "Total Revenue", "Total Income", "Total Expenses", "Net Income"
    ])]

    PAYROLL = ["Salaries & Wages", "Payroll Tax Expense"]
    UTILITIES = [c for c in yoy["Category"].unique() if "Utilit" in c]

    payroll_df = yoy[yoy["Category"].isin(PAYROLL)]
    utilities_df = yoy[yoy["Category"].isin(UTILITIES)]

    if not payroll_df.empty:
        payroll_sum = payroll_df.groupby("Year")[["YoY Change", "YoY %"]].sum().reset_index()
        payroll_sum["Category"] = "Payroll"
    else:
        payroll_sum = pd.DataFrame()

    if not utilities_df.empty:
        utilities_sum = utilities_df.groupby("Year")[["YoY Change", "YoY %"]].sum().reset_index()
        utilities_sum["Category"] = "Utilities"
    else:
        utilities_sum = pd.DataFrame()

    return pd.concat([board, payroll_sum, utilities_sum], ignore_index=True)

