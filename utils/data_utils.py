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

#def extract_subtotals(df):
    #return df.groupby(["Year", "Category"], as_index=False)["Amount"].sum()
import pandas as pd

def extract_subtotals(df):
    """
    Converts wide Excel format into long format:
    Category | 2021 | 2022 | 2023 | 2024 | 2025
    → Category | Year | Amount
    """

    # Identify year columns (numeric column names)
    year_cols = [col for col in df.columns if str(col).isdigit()]

    # Melt wide → long
    long_df = df.melt(
        id_vars=["Category"],
        value_vars=year_cols,
        var_name="Year",
        value_name="Amount"
    )

    # Convert Year to integer
    long_df["Year"] = long_df["Year"].astype(int)

    # Replace NaN with 0
    long_df["Amount"] = long_df["Amount"].fillna(0)

    return long_df


def compute_yoy(df):
    df = df.copy().sort_values(["Category", "Year"])
    df["YoY Change"] = df.groupby("Category")["Amount"].diff()
    df["YoY %"] = df.groupby("Category")["Amount"].pct_change() * 100
    return df
