import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from io import BytesIO

st.set_page_config(page_title="Church Financial Subtotals Dashboard", layout="wide")

# ---------------------------------------------------------
# Helper: Convert DataFrame to Excel bytes for download
# ---------------------------------------------------------
def df_to_excel_bytes(df, sheet_name="Sheet1"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()

# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------
@st.cache_data
def load_data():
    file_path = "MECCA_Financial_Data.xlsx"

    xls = pd.ExcelFile(file_path)
    all_years = []

    for sheet in xls.sheet_names:
        try:
            year = int(sheet)
        except Exception:
            continue

        df = pd.read_excel(file_path, sheet_name=sheet)

        df.columns = df.columns.str.strip()

        # Normalize Category
        df["Category"] = (
            df["Category"]
            .astype(str)
            .str.strip()
            .str.replace("\u00A0", " ", regex=False)
        )

        if "Category" not in df.columns:
            continue

        value_col = [c for c in df.columns if c != "Category"][0]
        df = df.rename(columns={value_col: "Amount"})

        df["Amount"] = (
            df["Amount"]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("$", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace("(", "-", regex=False)
            .str.replace(")", "", regex=False)
        )

        df["Amount"] = df["Amount"].replace("", 0)
        df["Amount"] = df["Amount"].fillna(0)
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")

        df["Year"] = year

        all_years.append(df[["Category", "Year", "Amount"]])

    return pd.concat(all_years, ignore_index=True)

# ---------------------------------------------------------
# EXTRACT SUBTOTALS
# ---------------------------------------------------------
def extract_subtotals(df):
    df = df.copy()

    df["Category"] = (
        df["Category"]
        .astype(str)
        .str.strip()
        .str.replace("\u00A0", " ", regex=False)
    )

    mask = df["Category"].str.startswith("Total for ")
    subtotals = df[mask].reset_index(drop=True)

    income_rows = subtotals[subtotals["Amount"] >= 0]
    expense_rows = subtotals[subtotals["Amount"] < 0]

    total_income = income_rows.groupby("Year")["Amount"].sum().reset_index()
    total_income["Category"] = "Total Income (Auto)"

    total_expenses = expense_rows.groupby("Year")["Amount"].sum().reset_index()
    total_expenses["Category"] = "Total Expenses (Auto)"

    revenue_df = pd.merge(
        total_income,
        total_expenses,
        on="Year",
        suffixes=("_Income", "_Expenses")
    )
    revenue_df["Amount"] = revenue_df["Amount_Income"] + revenue_df["Amount_Expenses"].abs()
    revenue_df = revenue_df[["Year", "Amount"]]
    revenue_df["Category"] = "Total Revenue (Auto)"

    net_income = pd.merge(
        total_income,
        total_expenses,
        on="Year",
        suffixes=("_Income", "_Expenses")
    )
    net_income["Amount"] = net_income["Amount_Income"] - net_income["Amount_Expenses"]
    net_income = net_income[["Year", "Amount"]]
    net_income["Category"] = "Net Income (Auto)"

    auto_totals = pd.concat(
        [total_income, total_expenses, revenue_df, net_income],
        ignore_index=True
    )

    return pd.concat([subtotals, auto_totals], ignore_index=True)

# ---------------------------------------------------------
# MAIN APP
# ---------------------------------------------------------

# Load data
df = load_data()

# Compute subtotals
subtotals = extract_subtotals(df)

# Build UI tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "Subtotal Summary",
    "Year-over-Year Change",
    "Surplus / Deficit",
    "Forecasting"
])

# ---------------------------------------------------------
# TAB 1 — Subtotal Summary
# ---------------------------------------------------------
with tab1:
    st.header("Subtotal Summary")
    st.dataframe(subtotals)

    excel_bytes = df_to_excel_bytes(subtotals, "Subtotals")
    st.download_button(
        "Download All Dashboard Results",
        data=excel_bytes,
        file_name="Dashboard_Results.xlsx"
    )

# ---------------------------------------------------------
# TAB 2 — YOY Change
# ---------------------------------------------------------
with tab2:
    st.header("Year-over-Year Change")

    yoy = subtotals.pivot_table(
        index="Category",
        columns="Year",
        values="Amount",
        aggfunc="sum"
    )

    st.dataframe(yoy)

# ---------------------------------------------------------
# TAB 3 — Surplus / Deficit
# ---------------------------------------------------------
with tab3:
    st.header("Surplus / Deficit")

    net = subtotals[subtotals["Category"] == "Net Income (Auto)"]
    st.dataframe(net)

# ---------------------------------------------------------
# TAB 4 — Forecasting
# ---------------------------------------------------------
with tab4:
    st.header("Forecasting")

    category_list = sorted(subtotals["Category"].unique())
    selected = st.selectbox("Select Category", category_list)

    cat_df = subtotals[subtotals["Category"] == selected].sort_values("Year")

    st.line_chart(cat_df.set_index("Year")["Amount"])
