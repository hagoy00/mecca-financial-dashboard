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

    long_df["Year"] = long_df["Year"].astype(int)

    return long_df


def build_board_categories(long_df):
    """
    Creates board-level categories:
    - Total Income
    - Total Expenses
    - Net Income (already in Excel)
    - Payroll (Salaries + Payroll Tax)
    - Utilities
    - Revenue = Income - Expenses
    """

    # --- Extract Income ---
    income = long_df[long_df["Category"] == "Total for Income"]

    # --- Extract Expenses ---
    expenses = long_df[long_df["Category"] == "Total for Expenses"]

    # --- Extract Utilities ---
    utilities = long_df[long_df["Category"] == "Total for Utilities"].copy()
    utilities["Category"] = "Utilities"

    # --- Extract Payroll (two categories combined) ---
    payroll_items = long_df[
        long_df["Category"].isin(["Salaries & Wages", "Payroll Tax Expense"])
    ]

    payroll = payroll_items.groupby("Year")["Amount"].sum().reset_index()
    payroll["Category"] = "Payroll"

    # --- Extract Net Income (already exists) ---
    net_income = long_df[long_df["Category"] == "Net Income"]

    # --- Compute Revenue = Income - Expenses ---
    merged = pd.merge(
        income[["Year", "Amount"]],
        expenses[["Year", "Amount"]],
        on="Year",
        suffixes=("_Income", "_Expenses")
    )

    merged["Amount"] = merged["Amount_Income"] - merged["Amount_Expenses"]
    revenue = merged[["Year", "Amount"]].copy()
    revenue["Category"] = "Total Revenue"

    # --- Combine all board categories ---
    board_df = pd.concat([
        income.assign(Category="Total Income"),
        expenses.assign(Category="Total Expenses"),
        revenue,
        net_income.assign(Category="Net Income"),
        payroll,
        utilities
    ], ignore_index=True)

    return board_df


def pivot_report(board_df):
    """
    Produces final board report:
    Rows = Year
    Columns = Category
    Values = Amount
    """

    pivot = board_df.pivot_table(
        index="Year",
        columns="Category",
        values="Amount",
        aggfunc="sum"
    ).reset_index()

    return pivot
