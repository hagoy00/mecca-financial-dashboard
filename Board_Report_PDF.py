import streamlit as st
from utils.db_utils import load_data
from utils.data_utils import extract_subtotals
from utils.yoy_utils import compute_six_category_yoy
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

st.title("Board Report PDF Generator")

df = load_data()
subtotals = extract_subtotals(df)

years = sorted(subtotals["Year"].unique())
selected_years = st.multiselect("Years", years, default=years[-2:])

if st.button("Generate PDF"):
    six_yoy = compute_six_category_yoy(subtotals, selected_years)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, height - 72, "MECCA Board Financial Report")

    y = height - 120
    for _, row in six_yoy.iterrows():
        c.drawString(72, y, f"{row['Year']} - {row['Category']}: Δ {row['YoY Change']:.0f}")
        y -= 14

    c.save()
    buffer.seek(0)

    st.download_button(
        "Download PDF",
        buffer,
        "MECCA_Board_Report.pdf",
        "application/pdf"
    )

