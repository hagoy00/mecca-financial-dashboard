import streamlit as st
from utils.db_utils import load_data
from utils.data_utils import extract_subtotals, build_board_categories, pivot_report

st.title("Charts & Visualizations")

df = load_data()
long_df = extract_subtotals(df)
board_df = build_board_categories(long_df)
pivot = pivot_report(board_df)

category = st.selectbox("Select Category", 
                        [c for c in pivot.columns if c != "Year"])

st.subheader(f"{category} Over Time")
st.line_chart(pivot.set_index("Year")[category])

st.subheader("All Categories")
st.area_chart(pivot.set_index("Year"))
