import streamlit as st
import pandas as pd
from utils.db_utils import init_db
from utils.data_utils import load_excel

st.title("Admin — Data Upload & DB Refresh")

uploaded_file = st.file_uploader("Upload new MECCA_Financial_Data.xlsx", type=["xlsx"])

if uploaded_file is not None:
    df_new = pd.read_excel(uploaded_file)
    st.dataframe(df_new.head())

    if st.button("Replace Excel and rebuild DB"):
        with open("MECCA_Financial_Data.xlsx", "wb") as f:
            f.write(uploaded_file.getbuffer())

        init_db()
        st.success("Database refreshed.")
