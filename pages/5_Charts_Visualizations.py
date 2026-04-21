import streamlit as st
import altair as alt
from utils.db_utils import load_data
from utils.data_utils import extract_subtotals

st.title("Charts & Visualizations")

df = load_data()
subtotals = extract_subtotals(df)

years = sorted(subtotals["Year"].unique())
selected_years = st.sidebar.multiselect("Years", years, default=years)

filtered = subtotals[subtotals["Year"].isin(selected_years)]

category = st.selectbox("Category", sorted(filtered["Category"].unique()))

cat_df = filtered[filtered["Category"] == category]

chart = alt.Chart(cat_df).mark_bar().encode(
    x="Year:O",
    y="Amount:Q",
    tooltip=["Year", "Amount"]
)

st.altair_chart(chart, use_container_width=True)

