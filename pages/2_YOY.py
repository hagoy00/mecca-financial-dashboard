import streamlit as st
from utils.db_utils import load_data
from utils.data_utils import extract_subtotals, build_board_categories, pivot_report

st.title("Year‑Over‑Year (YOY) Report")

df = load_data()
long_df = extract_subtotals(df)
board_df = build_board_categories(long_df)
pivot = pivot_report(board_df)

st.subheader("Board‑Level Pivot Table")
st.dataframe(pivot)

st.subheader("YOY Change by Category")
for category in pivot.columns:
    if category != "Year":
        st.line_chart(pivot.set_index("Year")[category])
