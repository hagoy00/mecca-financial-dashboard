import streamlit as st
from utils.db_utils import load_data
from utils.data_utils import extract_subtotals, build_board_categories, pivot_report

st.title("Board YOY Summary")

df = load_data()
long_df = extract_subtotals(df)
board_df = build_board_categories(long_df)
pivot = pivot_report(board_df)

st.subheader("Board Summary Table")
st.dataframe(pivot)

st.subheader("YOY Change")
yoy = pivot.copy()
for col in yoy.columns:
    if col != "Year":
        yoy[col] = yoy[col].pct_change() * 100

st.dataframe(yoy)
