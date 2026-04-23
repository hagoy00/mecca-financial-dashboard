import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

from utils.data_utils import load_all_years
#from utils.data_utils import load_church_excel
from utils.style_utils import highlight_subtotals

st.set_page_config(page_title="Forecasting", layout="wide")

st.title("📈 Financial Forecasting")

# Load data
df = load_all_years()
#df = load_church_excel()

if df.empty:
    st.error("No financial data found. Please upload MECCA_Financial_Data.xlsx.")
    st.stop()

# --- EXCLUDE SUBTOTALS FROM FORECASTING ---
df_items = df[df["Type"] != "Subtotal"]

# --- AGGREGATE BY YEAR ---
year_summary = (
    df_items.groupby(["Year", "Type"])["Amount"]
    .sum()
    .reset_index()
    .pivot(index="Year", columns="Type", values="Amount")
    .fillna(0)
)

year_summary["Surplus"] = year_summary["Income"] - year_summary["Expense"]

st.subheader("📘 Historical Summary (Income, Expense, Surplus)")
st.dataframe(year_summary, use_container_width=True)

st.divider()

# --- FORECASTING FUNCTION ---
def linear_forecast(series, years_ahead=3):
    """
    Simple linear regression forecast for financial trends.
    """
    x = np.arange(len(series))
    y = series.values

    # Fit linear model
    coef = np.polyfit(x, y, 1)
    poly = np.poly1d(coef)

    # Forecast future points
    future_x = np.arange(len(series), len(series) + years_ahead)
    forecast_values = poly(future_x)

    return forecast_values

# --- FORECAST NEXT 3 YEARS ---
years = list(year_summary.index)
last_year = years[-1]
future_years = [last_year + i for i in range(1, 4)]

income_forecast = linear_forecast(year_summary["Income"])
expense_forecast = linear_forecast(year_summary["Expense"])
surplus_forecast = income_forecast - expense_forecast

forecast_df = pd.DataFrame({
    "Year": future_years,
    "Income": income_forecast,
    "Expense": expense_forecast,
    "Surplus": surplus_forecast
})

st.subheader("🔮 Forecast for Next 3 Years")
st.dataframe(forecast_df, use_container_width=True)

st.divider()

# --- FORECAST CHART ---
st.subheader("📊 Forecast Chart")

combined = pd.concat([
    year_summary.reset_index()[["Year", "Income", "Expense", "Surplus"]],
    forecast_df
])

combined["Type"] = combined.apply(
    lambda row: "Forecast" if row["Year"] in future_years else "Actual",
    axis=1
)

chart = alt.Chart(combined).mark_line(point=True).encode(
    x="Year:O",
    y="Surplus:Q",
    color="Type:N",
    tooltip=["Year", "Income", "Expense", "Surplus", "Type"]
)

st.altair_chart(chart, use_container_width=True)

st.divider()

# --- RAW DATA WITH SUBTOTAL HIGHLIGHTING ---
st.subheader("📄 Raw Data (with Subtotals Highlighted)")

styled_df = df.style.apply(highlight_subtotals, axis=1)
st.dataframe(styled_df, use_container_width=True)
