import pandas as pd

def compute_yoy(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes YOY % and YOY absolute change for:
    - Total Income
    - Total Expenses
    - Net Income
    - Payroll (Salaries & Wages + Payroll Tax Expense)
    - Utilities (Total for Utilities)

    Expects long_df format:
    Year | Type | Category | Amount
    """

    if df.empty:
        return pd.DataFrame()

    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)

    # ============================================================
    # BUILD PAYROLL (combined)
    # ============================================================
    payroll_df = df[
        df["Category"].isin(["Salaries & Wages", "Payroll Tax Expense"])
    ].groupby("Year")["Amount"].sum().reset_index()
    payroll_df = payroll_df.rename(columns={"Amount": "Payroll"})

    # ============================================================
    # BUILD UTILITIES (Total for Utilities)
    # ============================================================
    utilities_df = df[
        df["Category"] == "Total for Utilities"
    ].groupby("Year")["Amount"].sum().reset_index()
    utilities_df = utilities_df.rename(columns={"Amount": "Utilities"})

    # ============================================================
    # BUILD INCOME + EXPENSE TOTALS
    # ============================================================
    totals = (
        df.groupby(["Year", "Type"])["Amount"]
        .sum()
        .reset_index()
        .pivot(index="Year", columns="Type", values="Amount")
        .fillna(0)
    )

    totals = totals.rename(columns={
        "Income": "Total Income",
        "Expense": "Total Expenses",
    })

    totals["Net Income"] = totals["Total Income"] - totals["Total Expenses"]

    # ============================================================
    # MERGE ALL CATEGORIES
    # ============================================================
    merged = totals.merge(payroll_df, on="Year", how="left")
    merged = merged.merge(utilities_df, on="Year", how="left")

    merged = merged.fillna(0)
    merged = merged.sort_values("Year")

    # ============================================================
    # YOY ABSOLUTE CHANGE
    # ============================================================
    merged["Income YOY"] = merged["Total Income"].diff()
    merged["Expense YOY"] = merged["Total Expenses"].diff()
    merged["Net Income YOY"] = merged["Net Income"].diff()
    merged["Payroll YOY"] = merged["Payroll"].diff()
    merged["Utilities YOY"] = merged["Utilities"].diff()

    # ============================================================
    # YOY PERCENT CHANGE
    # ============================================================
    merged["Income YOY %"] = merged["Total Income"].pct_change() * 100
    merged["Expense YOY %"] = merged["Total Expenses"].pct_change() * 100
    merged["Net Income YOY %"] = merged["Net Income"].pct_change() * 100
    merged["Payroll YOY %"] = merged["Payroll"].pct_change() * 100
    merged["Utilities YOY %"] = merged["Utilities"].pct_change() * 100

    return merged.reset_index()
