import streamlit as st
from utils.db_utils import load_data
from utils.data_utils import extract_subtotals, compute_yoy

st.title("YOY — All Categories")

df = load_data()
subtotals = extract_subtotals(df)

years = sorted(subtotals["Year"].unique())
selected_years = st.sidebar.multiselect("Years", years, default=years)

yoy = compute_yoy(subtotals)
yoy = yoy[yoy["Year"].isin(selected_years)]

st.dataframe(yoy)

