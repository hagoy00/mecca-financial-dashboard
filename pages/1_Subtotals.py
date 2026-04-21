import streamlit as st
from utils.db_utils import load_data
from utils.data_utils import extract_subtotals

st.title("Subtotal Summary")

df = load_data()
subtotals = extract_subtotals(df)

years = sorted(subtotals["Year"].unique())
selected_years = st.sidebar.multiselect("Years", years, default=years)

filtered = subtotals[subtotals["Year"].isin(selected_years)]

pivot = filtered.pivot_table(
    index="Category", columns="Year", values="Amount", aggfunc="sum"
)

st.dataframe(pivot)

