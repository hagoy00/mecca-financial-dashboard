import pandas as pd

def extract_subtotals(df):
    """
    Extracts subtotal rows from the Excel data.
    Assumes the Excel file contains columns:
    Category, Subcategory, Amount, Year
    """
    subtotal_df = df.groupby(["Category", "Year"])["Amount"].sum().reset_index()
    return subtotal_df


def compute_yoy(df):
    """
    Computes YOY change for each category.
    """
    df = df.sort_values(["Category", "Year"])
    df["YOY_Change"] = df.groupby("Category")["Amount"].pct_change() * 100
    return df


def compute_six_category_yoy(df):
    """
    Computes YOY for the six board-level categories:
    - Total Revenue
    - Total Income
    - Total Expenses
    - Net Income
    - Payroll
    - Utilities
    """
    categories = [
        "Total Revenue",
        "Total Income",
        "Total Expenses",
        "Net Income",
        "Payroll",
        "Utilities"
    ]

    filtered = df[df["Category"].isin(categories)]
    filtered = filtered.groupby(["Category", "Year"])["Amount"].sum().reset_index()
    filtered = compute_yoy(filtered)

    return filtered
