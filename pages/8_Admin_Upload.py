import streamlit as st
import pandas as pd
import os

from utils.data_utils import DATA_FILE, load_church_excel

st.set_page_config(page_title="Admin Upload", layout="wide")

st.title("🛠️ Admin – Upload New Financial Data")

st.info("""
Upload a new **MECCA_Financial_Data.xlsx** file to update the dashboard.
The file must follow the original church format:
- One sheet per year (2021, 2022, 2023, ...)
- Two columns: **Category** and **<YearValue>**
- Subtotals start with **'Total '**
""")

# ---------------------------------------------------------
# FILE UPLOADER
# ---------------------------------------------------------
uploaded_file = st.file_uploader(
    "Upload MECCA_Financial_Data.xlsx",
    type=["xlsx"]
)

if uploaded_file:
    try:
        # Save uploaded file to the same path used by the dashboard
        with open(DATA_FILE, "wb") as f:
            f.write(uploaded_file.getbuffer())

        st.success("✅ File uploaded successfully!")
        
        # Try loading the new file
        df = load_all_years()
        #df = load_church_excel()

        if df.empty:
            st.warning("The file was uploaded, but no valid data was found.")
        else:
            st.success("📊 New data loaded successfully!")
            st.dataframe(df.head(), use_container_width=True)

        st.info("Refresh the page to see updated dashboard results.")

    except Exception as e:
        st.error(f"❌ Error processing file: {e}")

st.divider()

# ---------------------------------------------------------
# SHOW CURRENT FILE STATUS
# ---------------------------------------------------------
st.subheader("📁 Current Data File Status")

if os.path.exists(DATA_FILE):
    st.success(f"Current data file found: **{DATA_FILE}**")
    df_preview = load_church_excel()

    if not df_preview.empty:
        st.dataframe(df_preview.head(), use_container_width=True)
    else:
        st.warning("The current file exists but contains no valid data.")
else:
    st.error("No data file found. Please upload MECCA_Financial_Data.xlsx.")
