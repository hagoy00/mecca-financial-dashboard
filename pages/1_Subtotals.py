import streamlit as st
from utils.db_utils import load_data
from utils.data_utils import extract_subtotals

st.title("Subtotals Report")

# Load Excel data
df = load_data()

# Convert wide → long
long_df = extract_subtotals(df)

# Year selector
years = sorted(long_df["Year"].unique())
selected_year = st.selectbox("Select Year", years)

# Filter for selected year
filtered = long_df[long_df["Year"] == selected_year]

st.subheader(f"Subtotals for {selected_year}")
st.dataframe(filtered)
