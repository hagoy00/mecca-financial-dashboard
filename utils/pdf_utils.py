from fpdf import FPDF

def generate_board_pdf(yoy_df, output_path="Board_Report.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="MECCA Board Report", ln=True, align="C")
    pdf.ln(10)

    for _, row in yoy_df.iterrows():
        line = f"{row['Category']} | {row['Year']} | ${row['Amount']:.2f} | YOY: {row['YOY_Change']:.2f}%"
        pdf.cell(200, 10, txt=line, ln=True)

    pdf.output(output_path)
    return output_path
