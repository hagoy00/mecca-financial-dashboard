from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors

def build_board_pdf(
    pdf_path: str,
    board_pivot,
    top5_income_by_year: dict,
    top5_expense_by_year: dict,
):
    """
    Builds the full board PDF report:
    - Church name
    - Board summary (2021–2025)
    - YOY summary
    - Forecast summary (placeholder)
    - Top 5 Income (2021–2025)
    - Top 5 Expenses (2021–2025)
    """

    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter

    # ============================================================
    # TITLE PAGE
    # ============================================================
    c.setFont("Helvetica-Bold", 20)
    c.drawString(1 * inch, height - 1.2 * inch, "Medhanialm Mekan Selam Ethiopian Church")
    c.setFont("Helvetica", 14)
    c.drawString(1 * inch, height - 1.6 * inch, "Board Financial Report (2021–2025)")
    c.showPage()

    # ============================================================
    # BOARD SUMMARY TABLE
    # ============================================================
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1 * inch, height - 1 * inch, "Board Summary (2021–2025)")

    y = height - 1.5 * inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1 * inch, y, "Year")
    c.drawString(2 * inch, y, "Total Income")
    c.drawString(3.5 * inch, y, "Total Expenses")
    c.drawString(5 * inch, y, "Net Income")

    c.setFont("Helvetica", 10)
    y -= 0.3 * inch

    for _, row in board_pivot.iterrows():
        c.drawString(1 * inch, y, str(int(row["Year"])))
        c.drawString(2 * inch, y, f"${row['Total Income']:,.2f}")
        c.drawString(3.5 * inch, y, f"${row['Total Expenses']:,.2f}")
        c.drawString(5 * inch, y, f"${row['Net Income']:,.2f}")
        y -= 0.25 * inch

    c.showPage()

    # ============================================================
    # TOP 5 INCOME (2021–2025)
    # ============================================================
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1 * inch, height - 1 * inch, "Top 5 Income (2021–2025)")

    y = height - 1.5 * inch

    for year, df in top5_income_by_year.items():
        c.setFont("Helvetica-Bold", 12)
        c.drawString(1 * inch, y, f"Year {year}")
        y -= 0.3 * inch

        if df.empty:
            c.setFont("Helvetica", 10)
            c.drawString(1 * inch, y, "No data available.")
            y -= 0.4 * inch
            continue

        c.setFont("Helvetica-Bold", 10)
        c.drawString(1 * inch, y, "Category")
        c.drawString(3.5 * inch, y, "Amount")
        y -= 0.25 * inch

        c.setFont("Helvetica", 10)
        for _, row in df.iterrows():
            c.drawString(1 * inch, y, str(row["Category"]))
            c.drawString(3.5 * inch, y, f"${row['Amount']:,.2f}")
            y -= 0.22 * inch

        y -= 0.3 * inch

        if y < 1 * inch:
            c.showPage()
            y = height - 1 * inch

    c.showPage()

    # ============================================================
    # TOP 5 EXPENSES (2021–2025)
    # ============================================================
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1 * inch, height - 1 * inch, "Top 5 Expenses (2021–2025)")

    y = height - 1.5 * inch

    for year, df in top5_expense_by_year.items():
        c.setFont("Helvetica-Bold", 12)
        c.drawString(1 * inch, y, f"Year {year}")
        y -= 0.3 * inch

        if df.empty:
            c.setFont("Helvetica", 10)
            c.drawString(1 * inch, y, "No data available.")
            y -= 0.4 * inch
            continue

        c.setFont("Helvetica-Bold", 10)
        c.drawString(1 * inch, y, "Category")
        c.drawString(3.5 * inch, y, "Amount")
        y -= 0.25 * inch

        c.setFont("Helvetica", 10)
        for _, row in df.iterrows():
            c.drawString(1 * inch, y, str(row["Category"]))
            c.drawString(3.5 * inch, y, f"${row['Amount']:,.2f}")
            y -= 0.22 * inch

        y -= 0.3 * inch

        if y < 1 * inch:
            c.showPage()
            y = height - 1 * inch

    c.showPage()

    # ============================================================
    # END OF REPORT
    # ============================================================
    c.setFont("Helvetica-Oblique", 12)
    c.drawString(1 * inch, height - 1 * inch, "End of Report")
    c.save()
