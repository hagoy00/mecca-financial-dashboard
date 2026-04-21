import streamlit as st
import numpy as np
from utils.db_utils import load_data
from utils.data_utils import extract_subtotals

st.title("Forecasting")

df = load_data()
subtotals = extract_subtotals(df)

category = st.selectbox("Category", sorted(subtotals["Category"].unique()))
years_ahead = st.slider("Years Ahead", 1, 5, 3)

df_cat = subtotals[subtotals["Category"] == category].sort_values("Year")

if df_cat["Year"].nunique() < 2:
    st.warning("Not enough data.")
else:
    x = df_cat["Year"].values
    y = df_cat["Amount"].values
    m, b = np.polyfit(x, y, 1)

    future_years = list(range(x.max() + 1, x.max() + 1 + years_ahead))
    forecast = [m * fy + b for fy in future_years]

    st.dataframe({"Year": future_years, "Forecast": forecast})

