import streamlit as st
import pandas as pd
from utils.data_utils import (
    load_all_years,
    build_board_categories,
    get_board_pivot,
)

st.title("YOY Summary — Medhanialm Mekan Selam Ethiopian Church")

DATA_PATH = "MECCA_Financial_Data.xlsx"


@st.cache_data
def load_data():
    long_df = load_all_years(DATA_PATH)
    board_df = build_board_categories(long_df)
    board_pivot = get_board_pivot(board_df)
    return board_pivot


df = load_data()

if df.empty:
    st.warning("No data available.")
    st.stop()

df["Year"] = df["Year"].astype(int)
df = df.sort_values("Year")

# =========================
# YOY CALCULATIONS
# =========================
df["Income YOY %"] = df["Total Income"].pct_change() * 100
df["Expense YOY %"] = df["Total Expenses"].pct_change() * 100
df["Net Income YOY %"] = df["Net Income"].pct_change() * 100

# =========================
# YOY TABLE
# =========================
st.subheader("Year‑Over‑Year Percentage Change")

yoy_table = df[[
    "Year",
    "Income YOY %",
    "Expense YOY %",
    "Net Income YOY %",
]]

st.dataframe(
    yoy_table.style.format({
        "Income YOY %": "{:,.2f}%",
        "Expense YOY %": "{:,.2f}%",
        "Net Income YOY %": "{:,.2f}%",
    }),
    use_container_width=True,
)

st.markdown("---")

# =========================
# YOY BAR CHART
# =========================
st.subheader("YOY % Change — Bar Chart")

chart_df = yoy_table.set_index("Year")
st.bar_chart(chart_df, use_container_width=True)

st.markdown("---")

# =========================
# YOY HEATMAP
# =========================
st.subheader("YOY Heatmap (Income, Expenses, Net Income)")

heatmap_df = chart_df.copy()

# Color scale: red (negative) → yellow (neutral) → green (positive)
def heatmap_color(val):
    if pd.isna(val):
        return ""
    if val > 0:
        return f"background-color: rgba(0, 200, 0, {min(val/100, 0.8)})"
    if val < 0:
        return f"background-color: rgba(255, 0, 0, {min(abs(val)/100, 0.8)})"
    return "background-color: rgba(255, 255, 0, 0.3)"


st.dataframe(
    heatmap_df.style.applymap(heatmap_color).format("{:,.2f}%"),
    use_container_width=True,
)
