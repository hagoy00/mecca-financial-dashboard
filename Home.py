import streamlit as st
import pandas as pd
import altair as alt

from utils.data_utils import load_church_excel
from utils.style_utils import highlight_subtotals

st.set_page_config(page_title="MECCA Financial Dashboard", layout="wide")

st.title("📊 MECCA Financial Dashboard – Home")

# Load data
df = load_church_excel()

if df.empty:
    st.error("No financial data found. Please upload MECCA_Financial_Data.xlsx.")
    st.stop()

# --- SUMMARY METRICS (exclude subtotals) ---
df_income = df[(df["Type"] == "Income")]
df_expense = df[(df["Type"] == "Expense")]

total_income = df_income["Amount"].sum()
total_expense = df_expense["Amount"].sum()
surplus = total_income - total_expense

col1, col2, col3 = st.columns(3)
col1.metric("Total Income", f"${total_income:,.2f}")
col2.metric("Total Expenses", f"${total_expense:,.2f}")
col3.metric("Surplus / Deficit", f"${surplus:,.2f}")

st.divider()

# --- FULL TABLE WITH SUBTOTAL HIGHLIGHTING ---
st.subheader("📘 Full Financial Table (with Subtotals)")

styled_df = df.style.apply(highlight_subtotals, axis=1)
st.dataframe(styled_df, use_container_width=True)

st.divider()

# --- CHART: INCLUDE SUBTOTALS (GREEN) ---
st.subheader("📈 Income, Expenses, and Subtotals")

df_items = df[df["Type"] != "Subtotal"]
df_subtotals = df[df["Type"] == "Subtotal"]

chart_items = alt.Chart(df_items).mark_bar(color="#4C72B0").encode(
    x="Category:N",
    y="Amount:Q",
    tooltip=["Category", "Amount", "Type"]
)

chart_subtotals = alt.Chart(df_subtotals).mark_bar(color="#2ECC71").encode(
    x="Category:N",
    y="Amount:Q",
    tooltip=["Category", "Amount", "Type"]
)

st.altair_chart(chart_items + chart_subtotals, use_container_width=True)
