import streamlit as st
import pandas as pd
import altair as alt

from utils.data_utils import load_church_excel
from utils.style_utils import highlight_subtotals

st.set_page_config(page_title="Charts", layout="wide")

st.title("📊 Financial Charts & Visualizations")

# Load data
df = load_church_excel()

if df.empty:
    st.error("No financial data found. Please upload MECCA_Financial_Data.xlsx.")
    st.stop()

# --- YEAR SELECTOR ---
years = sorted(df["Year"].unique())
selected_year = st.selectbox("Select Year", years, index=len(years)-1)

df_year = df[df["Year"] == selected_year]

# Split types
df_items = df_year[df_year["Type"] != "Subtotal"]
df_subtotals = df_year[df_year["Type"] == "Subtotal"]

st.subheader(f"📘 Charts for {selected_year}")

# ---------------------------------------------------------
# 1. BAR CHART – Income, Expenses, Subtotals
# ---------------------------------------------------------
st.markdown("### 📊 Bar Chart – Income, Expenses, Subtotals")

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

st.divider()

# ---------------------------------------------------------
# 2. PIE CHART – Income vs Expense (Subtotals excluded)
# ---------------------------------------------------------
st.markdown("### 🥧 Pie Chart – Income vs Expense")

df_pie = df_items.groupby("Type")["Amount"].sum().reset_index()

pie_chart = alt.Chart(df_pie).mark_arc().encode(
    theta="Amount:Q",
    color="Type:N",
    tooltip=["Type", "Amount"]
)

st.altair_chart(pie_chart, use_container_width=True)

st.divider()

# ---------------------------------------------------------
# 3. STACKED BAR – Income vs Expense by Category
# ---------------------------------------------------------
st.markdown("### 📚 Stacked Bar – Income vs Expense by Category")

df_stack = df_items.copy()

stack_chart = alt.Chart(df_stack).mark_bar().encode(
    x="Category:N",
    y="Amount:Q",
    color="Type:N",
    tooltip=["Category", "Amount", "Type"]
)

st.altair_chart(stack_chart, use_container_width=True)

st.divider()

# ---------------------------------------------------------
# 4. LINE CHART – Multi‑Year Trend (Income, Expense, Surplus)
# ---------------------------------------------------------
st.markdown("### 📈 Multi‑Year Trend (Income, Expense, Surplus)")

df_all_items = df[df["Type"] != "Subtotal"]

trend = (
    df_all_items.groupby(["Year", "Type"])["Amount"]
    .sum()
    .reset_index()
    .pivot(index="Year", columns="Type", values="Amount")
    .fillna(0)
)

trend["Surplus"] = trend["Income"] - trend["Expense"]

trend_df = trend.reset_index().melt(
    id_vars="Year",
    value_vars=["Income", "Expense", "Surplus"],
    var_name="Metric",
    value_name="Amount"
)

line_chart = alt.Chart(trend_df).mark_line(point=True).encode(
    x="Year:O",
    y="Amount:Q",
    color="Metric:N",
    tooltip=["Year", "Metric", "Amount"]
)

st.altair_chart(line_chart, use_container_width=True)

st.divider()

# ---------------------------------------------------------
# 5. RAW DATA WITH SUBTOTAL HIGHLIGHTING
# ---------------------------------------------------------
st.subheader("📄 Raw Data (with Subtotals Highlighted)")

styled_df = df_year.style.apply(highlight_subtotals, axis=1)
st.dataframe(styled_df, use_container_width=True)
