import streamlit as st
from utils.db_utils import load_data
from utils.data_utils import extract_subtotals

st.title("Surplus / Deficit")

df = load_data()
subtotals = extract_subtotals(df)

pivot = subtotals.pivot_table(
    index="Year", columns="Category", values="Amount", aggfunc="sum"
)

st.dataframe(pivot)

