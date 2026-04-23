import streamlit as st
import pandas as pd
import altair as alt

from utils.data_utils import load_all_years
#from utils.data_utils import load_church_excel
from utils.style_utils import highlight_subtotals

st.set_page_config(page_title="Surplus / Deficit", layout="wide")

st.title("💰 Surplus / Deficit Summary")

# Load data
df = load_all_years()
#df = load_church_excel()

if df.empty:
    st.error("No financial data found. Please upload MECCA_Financial_Data.xlsx.")
    st.stop()

# --- YEAR SELECTOR ---
years = sorted(df["Year"].unique())
selected_year = st.selectbox("Select Year", years, index=len(years)-1)

df_year = df[df["Year"] == selected_year]

# --- SPLIT TYPES ---
df_income = df_year[df_year["Type"] == "Income"]
df_expense = df_year[df_year["Type"] == "Expense"]
df_subtotals = df_year[df_year["Type"] == "Subtotal"]

# --- METRICS (exclude subtotals) ---
total_income = df_income["Amount"].sum()
total_expense = df_expense["Amount"].sum()
surplus = total_income - total_expense

col1, col2, col3 = st.columns(3)
col1.metric("Total Income", f"${total_income:,.2f}")
col2.metric("Total Expenses", f"${total_expense:,.2f}")
col3.metric("Surplus / Deficit", f"${surplus:,.2f}")

st.divider()

# --- FULL TABLE WITH SUBTOTAL HIGHLIGHTING ---
st.subheader(f"📄 Detailed Breakdown – {selected_year}")

styled_df = df_year.style.apply(highlight_subtotals, axis=1)
st.dataframe(styled_df, use_container_width=True)

st.divider()

# --- SURPLUS / DEFICIT TREND ACROSS YEARS ---
st.subheader("📈 Surplus / Deficit Trend (All Years)")

df_items = df[df["Type"] != "Subtotal"]

trend = (
    df_items.groupby(["Year", "Type"])["Amount"]
    .sum()
    .reset_index()
    .pivot(index="Year", columns="Type", values="Amount")
    .fillna(0)
)

trend["Surplus"] = trend["Income"] - trend["Expense"]

trend_chart = alt.Chart(trend.reset_index()).mark_line(point=True).encode(
    x="Year:O",
    y="Surplus:Q",
    tooltip=["Year", "Surplus"]
)

st.altair_chart(trend_chart, use_container_width=True)

st.divider()

# --- INCOME VS EXPENSE BAR CHART ---
st.subheader("📊 Income vs Expenses")

bar_chart = alt.Chart(trend.reset_index()).mark_bar().encode(
    x="Year:O",
    y="Income:Q",
    color=alt.value("#4C72B0"),
    tooltip=["Year", "Income"]
)

bar_chart_exp = alt.Chart(trend.reset_index()).mark_bar().encode(
    x="Year:O",
    y="Expense:Q",
    color=alt.value("#C44E52"),
    tooltip=["Year", "Expense"]
)

st.altair_chart(bar_chart + bar_chart_exp, use_container_width=True)
