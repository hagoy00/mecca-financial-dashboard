import streamlit as st
import pandas as pd
import altair as alt

from utils.data_utils import load_church_excel
from utils.style_utils import highlight_subtotals

st.set_page_config(page_title="Subtotals", layout="wide")

st.title("🧮 Subtotals Overview")

# Load data
df = load_church_excel()

if df.empty:
    st.error("No financial data found. Please upload MECCA_Financial_Data.xlsx.")
    st.stop()

# --- FILTER SUBTOTALS ONLY ---
df_subtotals = df[df["Type"] == "Subtotal"]

if df_subtotals.empty:
    st.warning("No subtotal rows found in the dataset.")
    st.stop()

# --- YEAR SELECTOR ---
years = sorted(df["Year"].unique())
selected_year = st.selectbox("Select Year", years, index=len(years)-1)

df_year = df_subtotals[df_subtotals["Year"] == selected_year]

st.subheader(f"📘 Subtotals for {selected_year}")

styled_df = df_year.style.apply(highlight_subtotals, axis=1)
st.dataframe(styled_df, use_container_width=True)

st.divider()

# --- SUBTOTAL TREND ACROSS YEARS ---
st.subheader("📈 Subtotal Trend Across Years")

trend = (
    df_subtotals.groupby(["Year", "Category"])["Amount"]
    .sum()
    .reset_index()
)

chart = alt.Chart(trend).mark_bar(color="#2ECC71").encode(
    x="Year:O",
    y="Amount:Q",
    color=alt.value("#2ECC71"),
    tooltip=["Year", "Category", "Amount"]
)

st.altair_chart(chart, use_container_width=True)

st.divider()

# --- SUBTOTALS BY CATEGORY (ALL YEARS) ---
st.subheader("📊 Subtotals by Category (All Years)")

pivot = trend.pivot_table(
    index="Category",
    columns="Year",
    values="Amount",
    aggfunc="sum"
).fillna(0)

st.dataframe(pivot, use_container_width=True)

st.divider()

# --- RAW DATA WITH HIGHLIGHTING ---
st.subheader("📄 Raw Data (with Subtotals Highlighted)")

styled_raw = df.style.apply(highlight_subtotals, axis=1)
st.dataframe(styled_raw, use_container_width=True)
