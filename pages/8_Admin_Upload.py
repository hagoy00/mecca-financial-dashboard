

import streamlit as st
import pandas as pd
import os

from utils.db_utils import load_data

st.title("Admin Upload")

uploaded = st.file_uploader("Upload updated MECCA Excel file", type=["xlsx"])

if uploaded:
    with open("MECCA_Financial_Data.xlsx", "wb") as f:
        f.write(uploaded.getbuffer())

    st.success("Excel file replaced successfully.")
    
