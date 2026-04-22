import streamlit as st
import pandas as pd
import altair as alt

from utils.data_utils import load_church_excel
from utils.style_utils import highlight_subtotals

st.set_page_config(page_title="Board YOY Summary", layout="wide")

st.title("📈 Year‑Over‑Year Board Summary")

# Load data
df = load_church_excel()

if df.empty:
    st.error("No financial data found. Please upload MECCA_Financial_Data.xlsx.")
    st.stop()

# --- EXCLUDE SUBTOTALS FROM YOY CALCULATIONS ---
df_items = df[df["Type"] != "Subtotal"]

# Pivot: Category × Year
pivot = df_items.pivot_table(
    index="Category",
    columns="Year",
    values="Amount",
    aggfunc="sum"
).fillna(0)

# Compute YOY %
yoy = pivot.pct_change(axis=1) * 100
yoy = yoy.round(2)

st.subheader("📊 YOY % Change by Category")
st.dataframe(yoy, use_container_width=True)

st.divider()

# --- YOY BAR CHART ---
st.subheader("📈 YOY Bar Chart")

# Melt for charting
df_yoy = yoy.reset_index().melt(
    id_vars="Category",
    var_name="Year",
    value_name="YOY"
)

chart = alt.Chart(df_yoy).mark_bar().encode(
    x="Category:N",
    y="YOY:Q",
    color=alt.Color("YOY:Q", scale=alt.Scale(scheme="redyellowgreen")),
    tooltip=["Category", "Year", "YOY"]
)

st.altair_chart(chart, use_container_width=True)

st.divider()

# --- YOY HEATMAP ---
st.subheader("🔥 YOY Heatmap")

heatmap = alt.Chart(df_yoy).mark_rect().encode(
    x="Year:O",
    y="Category:N",
    color=alt.Color("YOY:Q", scale=alt.Scale(scheme="redyellowgreen")),
    tooltip=["Category", "Year", "YOY"]
)

st.altair_chart(heatmap, use_container_width=True)

st.divider()

# --- SHOW RAW DATA WITH SUBTOTAL HIGHLIGHTING ---
st.subheader("📘 Raw Data (with Subtotals Highlighted)")

styled_df = df.style.apply(highlight_subtotals, axis=1)
st.dataframe(styled_df, use_container_width=True)
