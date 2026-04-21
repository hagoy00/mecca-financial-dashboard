import streamlit as st
import pandas as pd
import numpy as np
import os

@st.cache_data
def load_excel():
    local_path = "/Users/yemanehagos/my_first_project/data/MECCA_Financial_Data.xlsx"
    cloud_path = "MECCA_Financial_Data.xlsx"
    file_path = local_path if os.path.exists(local_path) else cloud_path
    return pd.read_excel(file_path)

def extract_subtotals(df):
    return df.groupby(["Year", "Category"], as_index=False)["Amount"].sum()

def compute_yoy(df):
    df = df.copy().sort_values(["Category", "Year"])
    df["YoY Change"] = df.groupby("Category")["Amount"].diff()
    df["YoY %"] = df.groupby("Category")["Amount"].pct_change() * 100
    return df
