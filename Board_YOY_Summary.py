import streamlit as st
from utils.db_utils import load_data
from utils.data_utils import extract_subtotals
from utils.yoy_utils import compute_six_category_yoy

st.title("Board YOY Summary (Six Categories)")

df = load_data()
subtotals = extract_subtotals(df)

years = sorted(subtotals["Year"].unique())
selected_years = st.sidebar.multiselect("Years", years, default=years)

final_yoy = compute_six_category_yoy(subtotals, selected_years)

pivot = final_yoy.pivot_table(
    index="Year", columns="Category", values="YoY Change", aggfunc="sum"
)

st.dataframe(pivot)

