import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from io import BytesIO

from utils.data_utils import load_all_years
#from utils.data_utils import load_church_excel
from utils.style_utils import highlight_subtotals

st.set_page_config(page_title="PDF Generator", layout="wide")

st.title("📄 PDF Report Generator")

# Load data
#df = load_church_excel()
df = load_all_years()

if df.empty:
    st.error("No financial data found. Please upload MECCA_Financial_Data.xlsx.")
    st.stop()

# --- YEAR SELECTOR ---
years = sorted(df["Year"].unique())
selected_year = st.selectbox("Select Year", years, index=len(years)-1)

df_year = df[df["Year"] == selected_year]

# Split types
df_income = df_year[df_year["Type"] == "Income"]
df_expense = df_year[df_year["Type"] == "Expense"]
df_subtotals = df_year[df_year["Type"] == "Subtotal"]

# Totals (exclude subtotals)
total_income = df_income["Amount"].sum()
total_expense = df_expense["Amount"].sum()
surplus = total_income - total_expense

st.subheader(f"📘 Summary for {selected_year}")

col1, col2, col3 = st.columns(3)
col1.metric("Total Income", f"${total_income:,.2f}")
col2.metric("Total Expenses", f"${total_expense:,.2f}")
col3.metric("Surplus / Deficit", f"${surplus:,.2f}")

st.divider()

# --- RAW DATA PREVIEW ---
st.subheader("📄 Data Preview (with Subtotals Highlighted)")

styled_df = df_year.style.apply(highlight_subtotals, axis=1)
st.dataframe(styled_df, use_container_width=True)

st.divider()

# ---------------------------------------------------------
# PDF GENERATION FUNCTION
# ---------------------------------------------------------
def generate_pdf(df_year, year, total_income, total_expense, surplus):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    styles = getSampleStyleSheet()
    story = []

    # Title
    title = Paragraph(f"<b>MECCA Financial Report – {year}</b>", styles["Title"])
    story.append(title)
    story.append(Spacer(1, 12))

    # Summary
    summary_text = f"""
    <b>Total Income:</b> ${total_income:,.2f}<br/>
    <b>Total Expenses:</b> ${total_expense:,.2f}<br/>
    <b>Surplus / Deficit:</b> ${surplus:,.2f}<br/>
    """
    story.append(Paragraph(summary_text, styles["Normal"]))
    story.append(Spacer(1, 12))

    # Table Data
    table_data = [["Category", "Amount", "Type"]]

    for _, row in df_year.iterrows():
        table_data.append([
            row["Category"],
            f"${row['Amount']:,.2f}",
            row["Type"]
        ])

    # Table Styling
    table = Table(table_data, colWidths=[250, 100, 100])

    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
    ])

    # Apply subtotal highlighting
    for i, row in enumerate(df_year.itertuples(), start=1):
        if row.Type == "Subtotal":
            style.add("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f0f0f0"))
            style.add("FONTNAME", (0, i), (-1, i), "Helvetica-Bold")

    table.setStyle(style)
    story.append(table)

    doc.build(story)
    buffer.seek(0)
    return buffer

# ---------------------------------------------------------
# DOWNLOAD BUTTON
# ---------------------------------------------------------
if st.button("📥 Generate PDF Report"):
    pdf_buffer = generate_pdf(df_year, selected_year, total_income, total_expense, surplus)
    st.download_button(
        label="Download PDF",
        data=pdf_buffer,
        file_name=f"MECCA_Financial_Report_{selected_year}.pdf",
        mime="application/pdf"
    )
