import streamlit as st
import pandas as pd
from utils.db_utils import load_data
from utils.data_utils import extract_subtotals, build_board_categories, pivot_report

st.title("Forecasting")

df = load_data()
long_df = extract_subtotals(df)
board_df = build_board_categories(long_df)
pivot = pivot_report(board_df)

category = st.selectbox("Select Category to Forecast", 
                        [c for c in pivot.columns if c != "Year"])

data = pivot[["Year", category]].copy()
data = data.set_index("Year")

# Simple linear forecast
data["Forecast"] = pd.Series(
    pd.Series(data[category]).rolling(window=2).mean(),
    index=data.index
).fillna(method="bfill")

st.subheader(f"Forecast for {category}")
st.line_chart(data)
