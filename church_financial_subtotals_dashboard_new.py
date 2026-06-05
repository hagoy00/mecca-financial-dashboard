import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

from io import BytesIO
import os

# -----------------------------------------------------
# COLOR FUNCTION FOR SURPLUS / DEFICIT (FINAL VERSION)
# -----------------------------------------------------
def color_surplus(col):
    return [
        "color: green; font-weight: 600;" if v > 0
        else "color: red; font-weight: 600;" if v < 0
        else ""
        for v in col
    ]


from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# ---------------------------------------------------------
# REAL STICKY TITLE (OUTSIDE STREAMLIT APP)
# ---------------------------------------------------------
st.markdown("""
<style>
#outside-sticky-title {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    z-index: 999999;
    background-color: white;
    padding: 20px 0 26px 0;
    font-size: 34px !important;   /* MAKE IT BIG */
    font-weight: 900 !important;
    color: #1E90FF !important;
    text-align: center;
    border-bottom: 2px solid #1E90FF;
}

/* Push Streamlit app down so title doesn't overlap */
body {
    padding-top: 30px !important;
}
</style>

<div id="outside-sticky-title">
    📊 Mekan Selam Medhanialem Ethiopian Orthodox Church → Financial Dashboard
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------
st.set_page_config(
    page_title="📊 Mekan Selam Medhanialem Ethiopian Orthodox Church → Financial Dashboard",
    layout="wide"
)
# ---------------------------------------------------------
# REMOVE STREAMLIT DEFAULT TITLE BAR
# ---------------------------------------------------------
st.markdown("""
<style>
header[data-testid="stHeader"] {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# GLOBAL FONT OVERRIDE — CLEAN + CONTROLLED
# ---------------------------------------------------------
st.markdown("""
<style>

/* -----------------------------------------
   BASE FONT SIZE FOR NORMAL TEXT
----------------------------------------- */
html, body, div, span, p, label {
    font-size: 32px !important;
}

/* -----------------------------------------
   HEADERS (bigger but not huge)
----------------------------------------- */
h1, h2, h3, h4, h5, h6 {
    font-size: 32px !important;
    font-weight: 700 !important;
}

/* -----------------------------------------
   PIVOT TABLES — MAKE THESE BIGGER
----------------------------------------- */
.dataframe tbody td {
    font-size: 190px !important;
}

.dataframe thead th {
    font-size: 10px !important;
    font-weight: bold !important;
}

/* Streamlit table widget */
.stTable {
    font-size: 10px !important;
}

/* Streamlit dataframe widget */
.stDataFrame {
    font-size: 10px !important;
}

/* -----------------------------------------
   SLIDERS, METRICS, INPUTS — NORMAL SIZE
----------------------------------------- */
.stSlider, .stNumberInput, .stMetric {
    font-size: 32px !important;
}

</style>
""", unsafe_allow_html=True)
# ---------------------------------------------------------
# SAFE STICKY TITLE (DOES NOT FREEZE STREAMLIT)
# ---------------------------------------------------------
st.markdown("""
<style>
.big-dashboard-title {
    position: sticky;
    top: 0;
    z-index: 10;
    background-color: white;
    padding: 14px 0 18px 0;
    font-size: 60px !important;
    font-weight: 900 !important;
    color: #1E90FF !important;
    text-align: center;
    border-bottom: 2px solid #1E90FF;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# FILE PATHS (LOCAL + CLOUD)
# ---------------------------------------------------------
LOCAL_PATH = "/Users/yemanehagos/my_first_project/data/MECCA_Financial_Data.xlsx"
CLOUD_PATH = "MECCA_Financial_Data.xlsx"

def get_file_path():
    if os.path.exists(LOCAL_PATH):
        return LOCAL_PATH
    return CLOUD_PATH

# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
def df_to_excel_bytes(df, sheet_name="Sheet1"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()

def classify_row_kind(cat):
    c = str(cat).strip().lower()
    if c.startswith("total for "):
        return "Subtotal"
    if c in ["expenses", "Net_Income", "net operating income"]:
        return "Header"
    return "Detail"

def format_numbers(df, exclude_cols=None):
    """
    Format numeric columns with commas and no decimals.
    exclude_cols: list of column names to leave untouched (e.g., ['Year'])
    """
    df = df.copy()
    exclude_cols = exclude_cols or []

    for col in df.columns:
        if col not in exclude_cols and pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].apply(lambda x: f"{x:,.0f}")
    return df

# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------
@st.cache_data
def load_data():
    file_path = get_file_path()

    # Load Excel file
    try:
        xls = pd.ExcelFile(file_path)
    except Exception as e:
        st.error(f"❌ Could not open Excel file: {e}")
        return pd.DataFrame()

    all_years = []

    for sheet in xls.sheet_names:
        # Only process sheets named as years (e.g., "2021")
        if not sheet.isdigit():
            continue

        year = int(sheet)

        try:
            df = pd.read_excel(file_path, sheet_name=sheet)
        except Exception:
            continue

        # Clean column names
        df.columns = df.columns.str.strip()

        # Must have Category column
        if "Category" not in df.columns:
            continue

        # The amount column is the year column (e.g., "2021")
        value_cols = [c for c in df.columns if c != "Category"]
        if not value_cols:
            continue

        value_col = value_cols[0]

        # Rename to Amount
        df = df.rename(columns={value_col: "Amount"})

        # Clean Amount values
        df["Amount"] = (
            df["Amount"]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("$", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace("(", "-", regex=False)
            .str.replace(")", "", regex=False)
        )

        df["Amount"] = df["Amount"].replace("", 0)
        df["Amount"] = df["Amount"].fillna(0)
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)

        # Add Year + Kind
        df["Year"] = year
        df["Kind"] = df["Category"].apply(classify_row_kind)

        # Keep only needed columns
        all_years.append(df[["Category", "Year", "Amount", "Kind"]])

    # ⭐ Prevent crash if no sheets were processed
    if not all_years:
        return pd.DataFrame()

    # Combine all years
    full_df = pd.concat(all_years, ignore_index=True)

    # Assign Income / Expense / Subtotal
    full_df = assign_income_expense(full_df)

    return full_df

# ---------------------------------------------------------
# ASSIGN Income / Expense / Subtotal  (FINAL CLEAN VERSION)
# ---------------------------------------------------------
def assign_income_expense(df):
    df = df.copy()
    df["Type"] = None

    for year, group in df.groupby("Year"):
        income_total_idx = group[group["Category"].str.lower() == "total for income"].index
        expense_total_idx = group[group["Category"].str.lower() == "total for expenses"].index

        if len(income_total_idx) == 0 or len(expense_total_idx) == 0:
            continue

        income_end = income_total_idx[0]
        expense_end = expense_total_idx[0]

        # 1. INCOME BLOCK
        df.loc[group.index.min():income_end - 1, "Type"] = "Income"

        # 2. EXPENSE BLOCK
        df.loc[income_end + 1:expense_end - 1, "Type"] = "Expense"

        # 3. SUBTOTALS override everything
        subtotal_idx = group.index[group["Category"].str.lower().str.startswith("total for ")]
        df.loc[subtotal_idx, "Type"] = "Subtotal"

    return df

# ---------------------------------------------------------
# EXTRACT SUBTOTALS + AUTO TOTALS (FINAL DEDUPED VERSION)
# ---------------------------------------------------------
def extract_subtotals(df):
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()
    df["Category"] = df["Category"].astype(str).str.strip()

    # 1. Extract existing subtotal rows
    mask = (
        df["Category"].str.startswith("Total for ")
        | (df["Category"] == "Net_Income")
        | (df["Category"] == "Net Operating Income")
    )
    subtotals = df[mask].copy()
    subtotals["Source"] = "Excel"

    # Helper
    def make_df(rows, name):
        out = rows.groupby("Year")["Amount"].sum().reset_index()
        out["Category"] = name
        out["Source"] = "Excel"
        return out

    # 2. Auto totals
    total_income = make_df(
        subtotals[subtotals["Category"].str.contains("Total for Income", case=False)],
        "Total_Income"
    )

    total_expenses = make_df(
        subtotals[subtotals["Category"].str.contains("Total for Expenses", case=False)],
        "Total_Expenses"
    )

    revenue_df = total_income.copy()
    revenue_df["Category"] = "Total_Revenue"

    net_income = pd.merge(
        total_income,
        total_expenses,
        on="Year",
        how="outer",
        suffixes=("_Income", "_Expenses")
    )
    net_income["Amount"] = (
        net_income["Amount_Income"].fillna(0)
        - net_income["Amount_Expenses"].fillna(0)
    )
    net_income = net_income[["Year", "Amount"]]
    net_income["Category"] = "Net_Income"
    net_income["Source"] = "Excel"

    # 3. Payroll
    payroll_rows = df[
        df["Category"].str.contains("salary|wage|payroll", case=False, na=False)
    ]
    payroll_sum = make_df(payroll_rows, "Payroll")

    # 4. Utilities
    util_rows = df[
        df["Category"].str.contains("utilit|garbage|gas|electric|water", case=False, na=False)
    ]
    util_sum = make_df(util_rows, "Utilities")

    # -----------------------------------------------------
    # FIX: REMOVE DUPLICATES (Category + Year)
    # -----------------------------------------------------
    combined = pd.concat(
        [
            subtotals[["Category", "Year", "Amount", "Source"]],
            total_income,
            total_expenses,
            revenue_df,
            net_income,
            payroll_sum,
            util_sum,
        ],
        ignore_index=True
    )

    # Deduplicate by summing duplicates
    combined = combined.groupby(["Category", "Year"], as_index=False)["Amount"].sum()

    return combined
# ---------------------------------------------------------
# YOY CALC (generic)
# ---------------------------------------------------------
def compute_yoy(subtotals):
    df = subtotals.copy()
    df = df.sort_values(["Category", "Year"])
    df["YoY Change"] = df.groupby("Category")["Amount"].diff()
    df["YoY %"] = df.groupby("Category")["Amount"].pct_change() * 100
    return df

# ---------------------------------------------------------
# COMPUTE - SURPLUS — CATEGORY 
# ---------------------------------------------------------

def compute_surplus_deficit(subtotals):
    df = subtotals.copy()

    # Extract each subtotal category with unique column names
    total_income = df[df["Category"] == "Total_Income"][["Year", "Amount"]]
    total_income = total_income.rename(columns={"Amount": "Total_Income"})

    total_expenses = df[df["Category"] == "Total_Expenses"][["Year", "Amount"]]
    total_expenses = total_expenses.rename(columns={"Amount": "Total_Expenses"})

    revenue = df[df["Category"] == "Total_Revenue"][["Year", "Amount"]]
    revenue = revenue.rename(columns={"Amount": "Total_Revenue"})

    net_income = df[df["Category"] == "Net_Income"][["Year", "Amount"]]
    net_income = net_income.rename(columns={"Amount": "Net_Income"})

    # Merge safely — no overwriting
    merged = (
        revenue.merge(total_income, on="Year", how="outer")
               .merge(total_expenses, on="Year", how="outer")
               .merge(net_income, on="Year", how="outer")
               .sort_values("Year")
    )

    # Final clean-up
    merged = merged.groupby("Year", as_index=False).first()

    return merged
# ---------------------------------------------------------
# FORECASTING — CATEGORY LEVEL (NO SOURCE COLUMN)
# ---------------------------------------------------------

def forecast_category(df_subtotals, category, end_year=2030):
    data = df_subtotals[df_subtotals["Category"] == category] \
            .groupby("Year")["Amount"].sum().reset_index()

    if len(data) < 2:
        return pd.DataFrame()

    x = data["Year"].values
    y = data["Amount"].values

    m, b = np.polyfit(x, y, 1)

    last_year = x.max()
    future_years = np.arange(last_year + 1, end_year + 1)
    future_amounts = m * future_years + b

    hist = data.copy()
    hist["Type"] = "Actual"

    fut = pd.DataFrame({"Year": future_years, "Amount": future_amounts})
    fut["Type"] = "Forecast"

    return pd.concat([hist, fut], ignore_index=True)

# ---------------------------------------------------------
# TOP INCOME / EXPENSE
# ---------------------------------------------------------
def get_top_income(df, n=5):
    d = df.copy()
    d = d[d["Type"] == "Income"]
    d = d[~d["Category"].str.startswith("Total for ")]
    grouped = d.groupby(["Year", "Category"])["Amount"].sum().reset_index()

    grouped["Rank"] = grouped.groupby("Year")["Amount"].rank(method="first", ascending=False)
    return grouped[grouped["Rank"] <= n].drop(columns="Rank")


def get_top_expense(df, n=5):
    d = df.copy()
    d = d[
    (d["Type"] == "Expense") &
    (~d["Category"].str.lower().str.startswith("total for")) &
    (~d["Category"].str.contains("depreciat", case=False, na=False))
]

    #d = d[d["Type"] == "Expense"]
    #d = d[~d["Category"].str.startswith("Total for ")]
    grouped = d.groupby(["Year", "Category"])["Amount"].sum().reset_index()

    grouped["Rank"] = grouped.groupby("Year")["Amount"].rank(method="first", ascending=False)
    return grouped[grouped["Rank"] <= n].drop(columns="Rank")


# ---------------------------------------------------------
# PDF GENERATION
# ---------------------------------------------------------
def generate_pdf(subtotals, year):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title = Paragraph(f"<b>MSMAEOC Financial Subtotals Report – {year}</b>", styles["Title"])
    story.append(title)
    story.append(Spacer(1, 12))

    df_year = subtotals[subtotals["Year"] == year].copy()
    df_year = df_year[["Category", "Amount"]]

    table_data = [["Category", "Amount"]]
    for _, row in df_year.iterrows():
        table_data.append([row["Category"], f"${row['Amount']:,.0f}"])
    table = Table(table_data, colWidths=[300, 150])
    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
    ])

    table.setStyle(TableStyle([
    ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 16),   # ← bigger font
    ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ("TOPPADDING", (0, 0), (-1, -1), 8),
]))

    for i, row in enumerate(df_year.itertuples(), start=1):
        if str(row.Category).lower().startswith("total for "):
            style.add("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f0f0f0"))
            style.add("FONTNAME", (0, i), (-1, i), "Helvetica-Bold")

    table.setStyle(style)
    story.append(table)

    doc.build(story)
    buffer.seek(0)
    return buffer


# ---------------------------------------------------------
# STYLING HELPERS
# ---------------------------------------------------------
def style_top5(df):
    df = df.copy()

    numeric_cols = df.select_dtypes(include=["number"]).columns
    index_positions = {idx: pos for pos, idx in enumerate(df.index)}

    def highlight(row):
        pos = index_positions[row.name]
        color = "background-color: #d4edda" if pos < 3 else "background-color: #fff3cd"
        return [color] * len(row)

    styler = df.style.apply(highlight, axis=1)
    styler = styler.format("{:,.0f}", subset=numeric_cols)

    return styler

# ---------------------------------------------------------
# FORECASTING — TOTALS (USES SOURCE COLUMN)
# ---------------------------------------------------------
def forecast_totals(df_subtotals, category, end_year=2030):
    df_cat = df_subtotals[df_subtotals["Category"] == category].copy()
    df_cat = df_cat.sort_values("Year")
    df_cat["Type"] = "Actual"

    if df_cat.empty or len(df_cat) < 2:
        return pd.DataFrame()

    x = df_cat["Year"].values
    y = df_cat["Amount"].values

    m, b = np.polyfit(x, y, 1)

    last_year = x.max()
    future_years = np.arange(last_year + 1, end_year + 1)
    future_amounts = m * future_years + b

    df_forecast = pd.DataFrame({"Year": future_years, "Amount": future_amounts, "Type": "Forecast"})
    return pd.concat([df_cat, df_forecast], ignore_index=True)

#-----------------------------------------------
# Main 
#-----------------------------------------------
def main():
    st.title("Church Financial Dashboard")

    # Load full detailed data (multi-sheet Excel)
    df_raw = load_data()

    if df_raw.empty:
        st.error("❌ No data loaded from Excel. Check sheet names and file path.")
        st.stop()
    
    # Extract subtotals (includes Source column)
    df_subtotals = extract_subtotals(df_raw)
    
    if df_subtotals.empty:
        st.error("❌ extract_subtotals() returned an empty DataFrame — cannot continue.")
        st.stop()

    # Subtotals for YOY, Forecast, Surplus/Deficit
    subtotals = df_subtotals
    yoy_df = compute_yoy(df_subtotals)

    # ---------------------------------------------------------
    # FIXED: Surplus/Deficit + Forecasts MUST use df_subtotals
    # ---------------------------------------------------------
    surplus_df = compute_surplus_deficit(df_subtotals)
    payroll_forecast = forecast_category(df_subtotals, "Payroll")
    utilities_forecast = forecast_category(df_subtotals, "Utilities")

    # Years for filters (use raw data)
    years = sorted(df_raw["Year"].unique())
    selected_years = st.multiselect("Select Years", years, default=years)

    #-----------------------------------------------
    # Tabs
    #-----------------------------------------------
    tab1, tab2, tab_top, tab3, tab4, tab_pdf = st.tabs([
        "Subtotal Summary",
        "YOY Summary",
        "Top Income & Expenses",
        "Surplus / Deficit",
        "Forecasting",
        "Board PDF"
    ])

    # -----------------------------------------------------
    # TAB 1 — UNIFIED SUBTOTAL SUMMARY
    # -----------------------------------------------------
    with tab1:
        st.subheader("📘 Unified Subtotal Summary (Pivot View)")

        summary_rows = []
    
        # Loop through ALL years in df_subtotals
        for year, group in df_subtotals.groupby("Year"):
    
            revenue = group.loc[
                group["Category"].str.lower() == "total for income",
                "Amount"
            ].sum()
    
            total_expenses = group.loc[
                group["Category"].str.lower() == "total for expenses",
                "Amount"
            ].sum()
    
            net_income = revenue - total_expenses
    
            # Use df_raw for detailed category rows
            payroll = df_raw[
                (df_raw["Year"] == year) &
                (df_raw["Category"].isin(["Salaries & Wages", "Payroll Tax Expense"]))
            ]["Amount"].sum()
    
            utilities = df_raw[
                (df_raw["Year"] == year) &
                (df_raw["Category"].str.contains("Utilit", case=False, na=False))
            ]["Amount"].sum()
    
            summary_rows.append(["Total_Revenue", year, revenue])
            summary_rows.append(["Total_Expenses", year, total_expenses])
            summary_rows.append(["Net_Income", year, net_income])
            summary_rows.append(["Payroll", year, payroll])
            summary_rows.append(["Utilities", year, utilities])
    
        summary_df = pd.DataFrame(summary_rows, columns=["Category", "Year", "Amount"])
    
        # SAFE formatting
        summary_df["Amount"] = (
            summary_df["Amount"]
            .fillna(0)
            .astype(float)
            .round(0)
            .astype(int)
            .apply(lambda x: f"{x:,}")
        )
    
        summary_pivot = summary_df.pivot_table(
            index="Category",
            columns="Year",
            values="Amount",
            aggfunc="first"
        ).fillna("0")
    
        summary_pivot.index.name = None
    
        st.markdown("### 📘 Main Financial Summary")
        st.dataframe(summary_pivot, use_container_width=True)
    
        st.divider()
    
        # -----------------------------------------------------
        # TOP 5 INCOME PIVOT
        # -----------------------------------------------------
        st.markdown("### 💰 Top 5 Income Categories (All Years)")
    
        income_df = df_raw[
            (df_raw["Type"] == "Income") &
            (~df_raw["Category"].str.lower().str.startswith("total for"))
        ]
    
        income_grouped = income_df.groupby(["Category", "Year"])["Amount"].sum().reset_index()
    
        top_income_categories = (
            income_grouped.groupby("Category")["Amount"]
            .sum()
            .sort_values(ascending=False)
            .head(5)
            .index
        )
    
        top_income_pivot = income_grouped[
            income_grouped["Category"].isin(top_income_categories)
        ].pivot_table(
            index="Category",
            columns="Year",
            values="Amount",
            aggfunc="sum"
        ).fillna(0)
    
        for col in top_income_pivot.columns:
            top_income_pivot[col] = (
                top_income_pivot[col]
                .astype(float)
                .round(0)
                .astype(int)
                .apply(lambda x: f"{x:,}")
            )
    
        st.dataframe(top_income_pivot, use_container_width=True)
    
        st.divider()
    
        # -----------------------------------------------------
        # TOP 5 EXPENSE PIVOT
        # -----------------------------------------------------
        st.markdown("### 📉 Top 5 Expense Categories (All Years)")
    
        expense_df = df_raw[
            (df_raw["Type"] == "Expense") &
            (~df_raw["Category"].str.lower().str.startswith("total for")) &
            (~df_raw["Category"].str.contains("depreciat", case=False, na=False))
        ]
    
        expense_grouped = expense_df.groupby(["Category", "Year"])["Amount"].sum().reset_index()
    
        top_expense_categories = (
            expense_grouped.groupby("Category")["Amount"]
            .sum()
            .sort_values(ascending=False)
            .head(5)
            .index
        )
    
        top_expense_pivot = expense_grouped[
            expense_grouped["Category"].isin(top_expense_categories)
        ].pivot_table(
            index="Category",
            columns="Year",
            values="Amount",
            aggfunc="sum"
        ).fillna(0)
    
        for col in top_expense_pivot.columns:
            top_expense_pivot[col] = (
                top_expense_pivot[col]
                .astype(float)
                .round(0)
                .astype(int)
                .apply(lambda x: f"{x:,}")
            )
    
        st.dataframe(top_expense_pivot, use_container_width=True)
            
    # -----------------------------------------------------
    # TAB 2 — CLEAN YOY SUMMARY
    # -----------------------------------------------------
    with tab2:
        st.subheader("📘 Year‑Over‑Year (YOY) Summary")
    
        TARGET_ORDER = [
            "Total_Revenue",
            "Total_Expenses",
            "Net_Income",
            "Payroll",
            "Utilities"
        ]
    
        yoy_rows = []
    
        for cat in TARGET_ORDER:
            cat_data = subtotals[subtotals["Category"] == cat].sort_values("Year")
            years_cat = cat_data["Year"].tolist()
            amounts = cat_data["Amount"].tolist()
    
            for i in range(len(years_cat)):
                year = years_cat[i]
                amount = amounts[i]
    
                prev_year = year - 1
    
                if prev_year not in years_cat:
                    yoy_change = 0
                    yoy_pct = 0
                else:
                    prev_index = years_cat.index(prev_year)
                    prev = amounts[prev_index]
    
                    yoy_change = amount - prev
                    yoy_pct = (yoy_change / prev * 100) if prev != 0 else 0
    
                yoy_rows.append([cat, year, amount, yoy_change, yoy_pct])
    
        yoy_clean = pd.DataFrame(yoy_rows, columns=[
            "Category", "Year", "Amount", "YoY Change", "YoY %"
        ])
    
        yoy_pivot = yoy_clean.pivot_table(
            index="Category",
            columns="Year",
            values="YoY Change",
            aggfunc="sum"
        ).fillna(0)
    
        st.dataframe(yoy_pivot.style.format("{:,.0f}"), use_container_width=True)
        
    # -----------------------------------------------------
    # TAB 3 — TOP INCOME & EXPENSES (FORECASTING)
    # -----------------------------------------------------
    with tab_top:
        st.subheader("Top Income & Top Expenses")
    
        # RAW numeric data (all years) — use df_raw
        raw_top_income = get_top_income(df_raw)
        raw_top_expense = get_top_expense(df_raw)
    
        # Year selector
        year_sel = st.selectbox("Select Year", years)
    
        # Filter for selected year (Top 5 only)
        inc_year = (
            raw_top_income[raw_top_income["Year"] == year_sel]
            .sort_values("Amount", ascending=False)
            .head(5)
        )
    
        exp_year = (
            raw_top_expense[raw_top_expense["Year"] == year_sel]
            .sort_values("Amount", ascending=False)
            .head(5)
        )
    
        # Format AFTER filtering
        inc_year_display = format_numbers(inc_year, exclude_cols=["Category", "Year"])
        exp_year_display = format_numbers(exp_year, exclude_cols=["Category", "Year"])
    
        # Display Top 5
        st.markdown(f"### 💰 Top 5 Income Categories — {year_sel}")
        st.dataframe(inc_year_display, use_container_width=True)
    
        st.markdown(f"### 📉 Top 5 Expense Categories — {year_sel}")
        st.dataframe(exp_year_display, use_container_width=True)
    
        st.divider()
    
        # -----------------------------------------------------
        # FORECAST CHARTS — FIXED TO USE df_raw
        # -----------------------------------------------------
    
        st.markdown(f"### Income Forecast — {year_sel}")
    
        if not inc_year.empty:
            selected_inc = st.selectbox("Forecast Income Category", inc_year["Category"])
            inc_forecast = forecast_category(df_raw, selected_inc)  # FIXED
    
            if inc_forecast.empty:
                st.info(f"No forecast available — '{selected_inc}' has fewer than 2 years of data.")
            else:
                chart = (
                    alt.Chart(inc_forecast)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X("Year:O", title="Year"),
                        y=alt.Y("Amount:Q", title="Amount"),
                        color="Type:N",
                        tooltip=["Year", "Amount", "Type"]
                    )
                    .properties(
                        title=f"Income Forecast — {selected_inc} ({year_sel})",
                        width=600,
                        height=350
                    )
                )
                st.altair_chart(chart, use_container_width=True)
    
        st.markdown(f"### Expense Forecast — {year_sel}")
    
        if not exp_year.empty:
            selected_exp = st.selectbox("Forecast Expense Category", exp_year["Category"])
            exp_forecast = forecast_category(df_raw, selected_exp)  # FIXED
    
            if exp_forecast.empty:
                st.info(f"No forecast available — '{selected_exp}' has fewer than 2 years of data.")
            else:
                chart = (
                    alt.Chart(exp_forecast)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X("Year:O", title="Year"),
                        y=alt.Y("Amount:Q", title="Amount"),
                        color="Type:N",
                        tooltip=["Year", "Amount", "Type"]
                    )
                    .properties(
                        title=f"Expense Forecast — {selected_exp} ({year_sel})",
                        width=600,
                        height=350
                )
                )
                st.altair_chart(chart, use_container_width=True)
            
    # -----------------------------------------------------
    # TAB 4 — SURPLUS / DEFICIT (FINAL WITH COMMAS)
    # -----------------------------------------------------
    with tab3:
    
        st.subheader("📉 Surplus / Deficit Summary")
    
        df_sd = surplus_df.copy()
    
        if df_sd.empty:
            st.warning("No Surplus/Deficit data available.")
            st.stop()
    
        # Year slider
        min_year = int(df_sd["Year"].min())
        max_year = int(df_sd["Year"].max())
    
        yr_range = st.slider(
            "Select Year Range",
            min_year,
            max_year,
            (min_year, max_year)
        )
    
        filtered = df_sd[
            (df_sd["Year"] >= yr_range[0]) &
            (df_sd["Year"] <= yr_range[1])
        ].copy()
    
        # YoY % calculation
        filtered["YoY_%"] = filtered["Net_Income"].pct_change() * 100
        filtered["YoY_%"] = filtered["YoY_%"].round(0)
    
        # -----------------------------------------------------
        # BOARD SUMMARY CARD
        # -----------------------------------------------------
        latest = filtered.iloc[-1]
        surplus_color = "green" if latest["Net_Income"] > 0 else "red"
    
        board_html = f"""
        <div style="
            background-color:#f8f9fa;
            padding:18px;
            border-radius:10px;
            border-left: 8px solid {surplus_color};
            margin-bottom:20px;
            font-size:18px;
            line-height:1.6;
        ">
            <h3 style="margin:0; color:{surplus_color};">
                📌 Board Summary — {int(latest['Year'])}
            </h3>
            <p style="margin:6px 0 0 0; font-size:16px;">
                <b>Total Income:</b> ${latest['Total_Income']:,.0f}<br>
                <b>Total Expenses:</b> ${latest['Total_Expenses']:,.0f}<br>
                <b>Net Income (Surplus/Deficit):</b>
                <span style="color:{surplus_color}; font-weight:700;">
                    ${latest['Net_Income']:,.0f}
                </span><br>
                <b>YoY Change:</b> {latest['YoY_%']:.0f}%
            </p>
        </div>
        """
    
        st.markdown(board_html, unsafe_allow_html=True)
    
        # -----------------------------------------------------
        # FINANCIAL HEALTH SCORE (CLEAN)
        # -----------------------------------------------------
        last3 = filtered.tail(3).copy()
    
        margin = last3["Net_Income"].iloc[-1] / last3["Total_Income"].iloc[-1]
        margin_score = max(0, min(1, margin)) * 40
    
        yoy = last3["Net_Income"].pct_change().iloc[-1]
        yoy_score = max(0, min(1, yoy)) * 30
    
        efficiency = last3["Total_Expenses"].iloc[-1] / last3["Total_Income"].iloc[-1]
        eff_score = (1 - max(0, min(1, efficiency))) * 20
    
        stability = 1 - (last3["Net_Income"].std() / abs(last3["Net_Income"].mean()))
        stab_score = max(0, min(1, stability)) * 10
    
        health_score = round(margin_score + yoy_score + eff_score + stab_score, 1)
    
        if health_score >= 80:
            score_color = "green"
        elif health_score >= 60:
            score_color = "blue"
        elif health_score >= 40:
            score_color = "orange"
        else:
            score_color = "red"
    
        st.markdown(f"""
        <div style="
            background-color:#ffffff;
            padding:18px;
            border-radius:10px;
            border-left: 8px solid {score_color};
            margin-bottom:20px;
        ">
            <h3 style="margin:0; color:{score_color};">
                🏛️ Financial Health Score: {health_score}/100
            </h3>
            <p style="margin:6px 0 0 0; font-size:16px;">
                <b>Net Income Margin:</b> {margin:.1%}<br>
                <b>YoY Growth:</b> {yoy:.1%}<br>
                <b>Expense Efficiency:</b> {efficiency:.1%}<br>
                <b>Stability (3‑yr):</b> {stability:.1%}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
        # -----------------------------------------------------
        # SURPLUS / DEFICIT TABLE (WITH COMMAS)
        # -----------------------------------------------------
        st.markdown("### 📄 Detailed Surplus / Deficit Table")
    
        filtered_styled = (
            filtered.style.format({
                "Total_Revenue": "{:,.0f}",
                "Total_Income": "{:,.0f}",
                "Total_Expenses": "{:,.0f}",
                "Net_Income": "{:,.0f}",
                "YoY_%": "{:.0f}%"
            })
            .apply(lambda s: ["color: green" if v > 0 else "color: red" for v in s], subset=["Net_Income"])
        )
    
        st.dataframe(filtered_styled, use_container_width=True)
    
        # -----------------------------------------------------
        # SURPLUS / DEFICIT CHART
        # -----------------------------------------------------
        st.markdown("### 📈 Surplus / Deficit Trend (Net_Income)")
    
        chart = (
            alt.Chart(filtered)
            .mark_line(point=True)
            .encode(
                x="Year:O",
                y="Net_Income:Q",
                color=alt.condition(
                    alt.datum.Net_Income > 0,
                    alt.value("green"),
                    alt.value("red")
                ),
                tooltip=["Year", "Net_Income", "YoY_%"]
            )
            .properties(width=800, height=400)
        )
    
        st.altair_chart(chart, use_container_width=True)
    
    # -----------------------------------------------------
    # TAB 5 — FORECASTING (FINAL FIXED VERSION)
    # -----------------------------------------------------
    with tab4:
        st.subheader("📈 Forecasting Through 2030")
    
        FORECAST_TARGETS = [
            "Total_Revenue",
            "Total_Expenses",
            "Net_Income",
            "Payroll",
            "Utilities"
        ]
    
        for category in FORECAST_TARGETS:
            st.markdown(f"### 🔮 {category} Forecast (to 2030)")
    
            # TOTALS use df_subtotals
            if category in ["Total_Revenue", "Total_Expenses", "Net_Income"]:
                fc = forecast_category(df_subtotals, category)
    
            # CATEGORY-LEVEL ALSO uses df_subtotals (FIXED)
            else:
                fc = forecast_category(df_subtotals, category)
    
            if fc.empty:
                st.warning(f"No data available to forecast {category}")
                continue
    
            chart = (
                alt.Chart(fc)
                .mark_line(point=True)
                .encode(
                    x="Year:O",
                    y="Amount:Q",
                    color="Type:N",
                    tooltip=["Year", "Amount", "Type"]
                )
                .properties(width=800, height=400)
            )
    
            st.altair_chart(chart, use_container_width=True)
    
            st.dataframe(
                fc.pivot_table(index="Year", columns="Type", values="Amount")
                  .fillna(0)
                  .style.format("{:,.0f}"),
                use_container_width=True
            )
    
            st.divider()

    # -----------------------------------------------------
    # TAB 6 — BOARD PDF
    # -----------------------------------------------------
    with tab_pdf:
        st.subheader("Board PDF Report")

        year_for_pdf = st.selectbox("Select Year for PDF", years)

        if st.button("Generate PDF"):
            pdf_buffer = generate_pdf(subtotals, year_for_pdf)
            st.download_button(
                label="Download PDF",
                data=pdf_buffer,
                file_name=f"Mekan Selam Medhanialem Ethiopian Orthodox Church → Financial Dashboard.pdf",
                mime="application/pdf"
            )
# ---------------------------------------------------------
# RUN APP
# ---------------------------------------------------------
if __name__ == "__main__":
    main()
