import streamlit as st
import pandas as pd

st.title("Admin Upload")

uploaded = st.file_uploader("Upload updated MECCA Excel file", type=["xlsx"])

if uploaded:
    with open("MECCA_Financial_Data.xlsx", "wb") as f:
        f.write(uploaded.getbuffer())

    st.success("Excel file replaced successfully.")
