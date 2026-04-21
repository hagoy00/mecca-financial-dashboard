import streamlit as st
from utils.db_utils import load_data
from utils.data_utils import extract_subtotals, build_board_categories, pivot_report

st.title("Surplus / Deficit Report")

df = load_data()
long_df = extract_subtotals(df)
board_df = build_board_categories(long_df)
pivot = pivot_report(board_df)

pivot["Surplus/Deficit"] = pivot["Total Income"] - pivot["Total Expenses"]

st.subheader("Surplus / Deficit by Year")
st.dataframe(pivot[["Year", "Surplus/Deficit"]])

st.line_chart(pivot.set_index("Year")["Surplus/Deficit"])
