import pandas as pd

def extract_subtotals(df):
    """
    Converts wide Excel format into long format:
    Category | 2021 | 2022 | 2023 | 2024 | 2025
    → Category | Year | Amount
    """

    # Identify year columns (numeric column names)
    year_cols = [col for col in df.columns if str(col).isdigit()]

    # Convert all year columns to numeric
    for col in year_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Melt wide → long
    long_df = df.melt(
        id_vars=["Category"],
        value_vars=year_cols,
        var_name="Year",
        value_name="Amount"
    )

    # Convert Year to integer
    long_df["Year"] = long_df["Year"].astype(int)

    return long_df


def compute_yoy(long_df):
    """
    Computes YOY change for each category.
    """
    long_df = long_df.sort_values(["Category", "Year"])
    long_df["YOY_Change"] = long_df.groupby("Category")["Amount"].pct_change() * 100
    return long_df


def compute_six_category_yoy(long_df):
    """
    Computes YOY for the six board-level categories.
    """

    categories = [
        "Total Revenue",
        "Total Income",
        "Total Expenses",
        "Net Income",
        "Payroll",
        "Utilities"
    ]

    filtered = long_df[long_df["Category"].isin(categories)]
    filtered = filtered.groupby(["Category", "Year"])["Amount"].sum().reset_index()
    filtered = compute_yoy(filtered)

    return filtered
