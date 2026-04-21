import streamlit as st
from utils.db_utils import load_data
from utils.data_utils import extract_subtotals, build_board_categories, pivot_report
from utils.pdf_utils import generate_board_pdf

st.title("Board Report PDF Generator")

df = load_data()
long_df = extract_subtotals(df)
board_df = build_board_categories(long_df)
pivot = pivot_report(board_df)

if st.button("Generate PDF"):
    path = generate_board_pdf(board_df)
    st.success(f"PDF generated: {path}")
