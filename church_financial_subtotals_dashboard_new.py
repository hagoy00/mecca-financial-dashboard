import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

from io import BytesIO
import os

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
    padding: 15px 0 18px 0;
    font-size: 36px !important;   /* MAKE IT BIG */
    font-weight: 900 !important;
    color: #1E90FF !important;
    text-align: center;
    border-bottom: 2px solid #1E90FF;
}

/* Push Streamlit app down so title doesn't overlap */
body {
    padding-top: 34px !important;
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
# GLOBAL FONT OVERRIDE — 26px
# ---------------------------------------------------------
st.markdown("""
<style>
html, body, div, span, p, label, h1, h2, h3, h4, h5, h6 {
    font-size: 38px !important;
}
.stMarkdown, .stText, .stDataFrame, .stTable, .stMetric, .stNumberInput, .stSlider {
    font-size: 80px !important;
    font-weight: bold !important;
}
.dataframe tbody tr td {
    font-size: 80px !important;
}
.dataframe thead tr th {
    font-size: 80px !important;
    font-weight: bold !important;
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
    font-size: 40px !important;
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
    if c in ["expenses", "net income", "net operating income"]:
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
# ASSIGN Income / Expense / Subtotal
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

        # 1. INCOME BLOCK (exclude "Total for Income")
        df.loc[group.index.min():income_end - 1, "Type"] = "Income"

        # 2. EXPENSE BLOCK (exclude both totals)
        df.loc[income_end + 1:expense_end - 1, "Type"] = "Expense"

        # 3. SUBTOTALS override everything
        subtotal_idx = group.index[group["Category"].str.lower().str.startswith("total for ")]
        df.loc[subtotal_idx, "Type"] = "Subtotal"

    return df


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------
@st.cache_data
def load_data():
    file_path = get_file_path()
    xls = pd.ExcelFile(file_path)
    all_years = []

    for sheet in xls.sheet_names:
        try:
            year = int(sheet)
        except Exception:
            continue

        df = pd.read_excel(file_path, sheet_name=sheet)
        df.columns = df.columns.str.strip()

        if "Category" not in df.columns:
            continue

        value_col = [c for c in df.columns if c != "Category"][0]
        df = df.rename(columns={value_col: "Amount"})

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
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")

        df["Year"] = year
        df["Kind"] = df["Category"].apply(classify_row_kind)

        all_years.append(df[["Category", "Year", "Amount", "Kind"]])

    full_df = pd.concat(all_years, ignore_index=True)
    full_df = assign_income_expense(full_df)
    return full_df


# ---------------------------------------------------------
# EXTRACT SUBTOTALS + AUTO TOTALS (with Payroll + Utilities)
# ---------------------------------------------------------
def extract_subtotals(df):
    df = df.copy()

    # 1. Extract subtotal rows INCLUDING Excel Net Income
    mask = (
        df["Category"].str.startswith("Total for ")
        | (df["Category"] == "Net Income")   # ← keep Excel Net Income
        | (df["Category"] == "Net Operating Income")
    )
    subtotals = df[mask].reset_index(drop=True)

    # 2. AUTO TOTALS (Income, Expenses, Revenue)
    income_rows = subtotals[subtotals["Category"] == "Total for Income"]
    total_income = income_rows.groupby("Year")["Amount"].sum().reset_index()
    total_income["Category"] = "Total Income"

    expense_rows = subtotals[subtotals["Category"] == "Total for Expenses"]
    total_expenses = expense_rows.groupby("Year")["Amount"].sum().reset_index()
    total_expenses["Category"] = "Total Expenses"

    revenue_df = total_income.copy()
    revenue_df["Category"] = "Total Revenue"

    # ❌ REMOVE Python Net Income calculation completely
    # (We keep Excel Net Income exactly as-is)

    auto_totals = pd.concat(
        [total_income, total_expenses, revenue_df],
        ignore_index=True
    )

    # 3. Payroll subtotal
    payroll_rows = df[df["Category"].isin(["Salaries & Wages", "Payroll Tax Expense"])]
    payroll_sum = payroll_rows.groupby("Year")["Amount"].sum().reset_index()
    payroll_sum["Category"] = "Payroll"

    # 4. Utilities subtotal
    util_rows = df[df["Category"].str.contains("Utilit", case=False, na=False)]
    util_sum = util_rows.groupby("Year")["Amount"].sum().reset_index()
    util_sum["Category"] = "Utilities"

    # 5. Return everything (Excel Net Income preserved)
    return pd.concat(
        [subtotals, auto_totals, payroll_sum, util_sum],
        ignore_index=True
    )


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
# SURPLUS / DEFICIT (using auto totals)
# ---------------------------------------------------------
def compute_surplus_deficit(subtotals):
    df = subtotals.copy()

    total_income = df[df["Category"] == "Total Income"][["Year", "Amount"]]
    total_income = total_income.rename(columns={"Amount": "Total Income"})

    total_expenses = df[df["Category"] == "Total Expenses"][["Year", "Amount"]]
    total_expenses = total_expenses.rename(columns={"Amount": "Total Expenses"})

    revenue = df[df["Category"] == "Total Revenue"][["Year", "Amount"]]
    revenue = revenue.rename(columns={"Amount": "Total Revenue"})

    net_income = df[df["Category"] == "Net Income"][["Year", "Amount"]]
    net_income = net_income.rename(columns={"Amount": "Net Income"})

    merged = (
        revenue.merge(total_income, on="Year", how="outer")
        .merge(total_expenses, on="Year", how="outer")
        .merge(net_income, on="Year", how="outer")
        .sort_values("Year")
    )

    return merged


# ---------------------------------------------------------
# FORECASTING
# ---------------------------------------------------------
def forecast_category(df, category):
    # Filter category and aggregate by year
    df_cat = (
        df[df["Category"] == category]
        .groupby("Year")["Amount"]
        .sum()
        .reset_index()
        .sort_values("Year")
    )

    if df_cat.empty:
        return pd.DataFrame()

    # Prepare regression using numpy (no sklearn needed)
    X = df_cat["Year"].values
    y = df_cat["Amount"].values

    # Fit linear regression: y = m*x + b
    m, b = np.polyfit(X, y, 1)

    # Forecast next 5 years
    last_year = X.max()
    future_years = np.arange(last_year + 1, last_year + 6)
    future_amounts = m * future_years + b

    # Build forecast dataframe
    forecast_df = pd.DataFrame({
        "Year": future_years,
        "Amount": future_amounts,
        "Type": "Forecast"
    })

    # Label actuals
    df_cat["Type"] = "Actual"

    # Combine actual + forecast
    return pd.concat([df_cat, forecast_df], ignore_index=True)

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

    
#-----------------------------------------------
# Main 
#-----------------------------------------------
def main():

    df = load_data()
    subtotals = extract_subtotals(df)
    yoy_df = compute_yoy(subtotals)

    years = sorted(df["Year"].unique())
    selected_years = st.multiselect("Select Years", years, default=years)

    # -----------------------------------------
    # Tabs (must NOT be indented deeper)
    # -----------------------------------------
    tab1, tab2, tab_top, tab3, tab4, tab_pdf = st.tabs([
        "Subtotal Summary",
        "YOY Summary",
        "Top Income & Expenses",
        "Surplus / Deficit",
        "Forecasting",
        "Board PDF"
    ]) 
    
    # -----------------------------------------------------
    # TAB 1 — UNIFIED SUBTOTAL SUMMARY (FINAL STABLE VERSION)
    # -----------------------------------------------------
    with tab1:
        st.subheader("📘 Unified Subtotal Summary (Pivot View)")
    
        summary_rows = []
    
        for year, group in subtotals.groupby("Year"):
    
            revenue = group.loc[
                group["Category"].str.lower() == "total for income",
                "Amount"
            ].sum()
    
            total_expenses = group.loc[
                group["Category"].str.lower() == "total for expenses",
                "Amount"
            ].sum()
    
            net_income = revenue - total_expenses
    
            payroll = df[
                (df["Year"] == year) &
                (df["Category"].isin(["Salaries & Wages", "Payroll Tax Expense"]))
            ]["Amount"].sum()
    
            utilities = df[
                (df["Year"] == year) &
                (df["Category"].str.contains("Utilit", case=False, na=False))
            ]["Amount"].sum()
    
            summary_rows.append(["Total Revenue", year, revenue])
            summary_rows.append(["Total Expenses", year, total_expenses])
            summary_rows.append(["Net Income", year, net_income])
            summary_rows.append(["Payroll", year, payroll])
            summary_rows.append(["Utilities", year, utilities])
    
        summary_df = pd.DataFrame(summary_rows, columns=["Category", "Year", "Amount"])
    
        # SAFE formatting
        if not summary_df.empty:
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
        sd_filtered = sd_filtered.reset_index(drop=True)
        st.dataframe(summary_pivot, use_container_width=True)
    
        st.divider()
    
        # -----------------------------------------------------
        # TOP 5 INCOME PIVOT
        # -----------------------------------------------------
        st.markdown("### 💰 Top 5 Income Categories (All Years)")
    
        income_df = df[
            (df["Type"] == "Income") &
            (~df["Category"].str.lower().str.startswith("total for"))
        ]
    
        income_grouped = income_df.groupby(["Category", "Year"])["Amount"].sum().reset_index()
        income_grouped["Amount"] = income_grouped["Amount"].astype(int)
    
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
    
        # GUARANTEE DataFrame
        if isinstance(top_income_pivot, pd.Series):
            top_income_pivot = top_income_pivot.to_frame()
    
        # SAFE formatting — no applymap()
        for col in top_income_pivot.columns:
            top_income_pivot[col] = (
                top_income_pivot[col]
                .fillna(0)
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
    
        expense_df = df[
            (df["Type"] == "Expense") &
            (~df["Category"].str.lower().str.startswith("total for")) &
            (~df["Category"].str.contains("depreciat", case=False, na=False))
        ]
    
        expense_grouped = expense_df.groupby(["Category", "Year"])["Amount"].sum().reset_index()
        expense_grouped["Amount"] = expense_grouped["Amount"].astype(int)
    
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
    
        # GUARANTEE DataFrame
        if isinstance(top_expense_pivot, pd.Series):
            top_expense_pivot = top_expense_pivot.to_frame()
    
        # SAFE formatting — no applymap()
        for col in top_expense_pivot.columns:
            top_expense_pivot[col] = (
                top_expense_pivot[col]
                .fillna(0)
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
        "Total Revenue",
        "Total Expenses",
        "Net Income",
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

        #yoy_clean = add_yoy_icons(yoy_clean)

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
    
        # RAW numeric data (all years)
        raw_top_income = get_top_income(df)
        raw_top_expense = get_top_expense(df)
    
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
    
        # -----------------------------------------------------
        # FORECAST CHARTS (STACKED VERTICALLY)
        # -----------------------------------------------------
    
        st.markdown("### Income Forecast")
    
        if not inc_year.empty:
            selected_inc = st.selectbox("Forecast Income Category", inc_year["Category"])
            inc_forecast = forecast_category(df, selected_inc)
    
            if not inc_forecast.empty:
                chart = (
                    alt.Chart(inc_forecast)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X("Year:O", title="Year"),
                        #y=alt.Y("Amount:Q", title="Amount"),
                        y=alt.Y(
                        "Amount:Q",
                        title="Amount",
                        axis=alt.Axis(
                            tickCount=5,
                            labelOverlap=False
                        ),
                        scale=alt.Scale(
                            nice=False
                        )
                    ),

                        color="Type:N",
                        tooltip=["Year", "Amount", "Type"]
                    )
                    .properties(
                        title=f"Forecast — {selected_inc}",
                        width=600,
                        height=350
                    )
                )
                st.altair_chart(chart, use_container_width=True)
    
        st.markdown("### Expense Forecast")
    
        if not exp_year.empty:
            selected_exp = st.selectbox("Forecast Expense Category", exp_year["Category"])
            exp_forecast = forecast_category(df, selected_exp)
    
            if not exp_forecast.empty:
                chart = (
                    alt.Chart(exp_forecast)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X("Year:O", title="Year"),
                        #y=alt.Y("Amount:Q", title="Amount"),
                        y=alt.Y(
                        "Amount:Q",
                        title="Amount",
                        axis=alt.Axis(
                            tickCount=5,
                            labelOverlap=False
                        ),
                        scale=alt.Scale(
                            nice=False
                        )
                    ),

                        color="Type:N",
                        tooltip=["Year", "Amount", "Type"]
                    )
                    .properties(
                        title=f"Forecast — {selected_exp}",
                        width=600,
                        height=350
                    )
                )
                st.altair_chart(chart, use_container_width=True)
        
    # -----------------------------------------------------
    # TAB 4 — SURPLUS / DEFICIT
    # -----------------------------------------------------
    with tab3:
        st.subheader("📉 Surplus / Deficit Summary")
    
        income_df_sd = subtotals[subtotals["Category"] == "Total Income"].sort_values("Year")
        expense_df_sd = subtotals[subtotals["Category"] == "Total Expenses"].sort_values("Year")
    
        years_income = income_df_sd["Year"].tolist()
        income_vals = income_df_sd["Amount"].tolist()
        expense_vals = expense_df_sd["Amount"].tolist()
    
        sd_rows = []
    
        for i in range(len(years_income)):
            year = years_income[i]
            inc = income_vals[i]
            exp = expense_vals[i]
            surplus = inc - exp
    
            if i == 0:
                yoy_change = 0
            else:
                prev_surplus = income_vals[i - 1] - expense_vals[i - 1]
                yoy_change = surplus - prev_surplus
    
            sd_rows.append([year, inc, exp, surplus, yoy_change])
    
        sd_df = pd.DataFrame(sd_rows, columns=[
            "Year", "Total Income", "Total Expenses", "Surplus/Deficit", "YoY Change"
        ])
    
        # 🔥 SAFE FILTER — sd_filtered ALWAYS exists
        try:
            if "selected_years" in locals() and selected_years:
                sd_filtered = sd_df[sd_df["Year"].isin(selected_years)]
            else:
                sd_filtered = sd_df.copy()
    
            # 🔥 Reset index ONLY after sd_filtered exists
            sd_filtered = sd_filtered.reset_index(drop=True)
    
        except Exception:
            # 🔥 Absolute fallback — cannot fail
            sd_filtered = sd_df.copy().reset_index(drop=True)
    
        st.dataframe(
            sd_filtered.style.format({
                "Total Income": "{:,.0f}",
                "Total Expenses": "{:,.0f}",
                "Surplus/Deficit": "{:,.0f}",
                "YoY Change": "{:,.0f}"
            }),
            use_container_width=True
        )
        
    # -----------------------------------------------------
    # TAB 5 — FORECASTING
    # -----------------------------------------------------
    with tab4:
        st.subheader("📈 Forecasting Through 2030")

        FORECAST_TARGETS = [
            "Total Revenue",
            "Total Expenses",
            "Net Income",
            "Payroll",
            "Utilities"
        ]

        for category in FORECAST_TARGETS:
            st.markdown(f"### 🔮 {category} Forecast (to 2030)")

            fc = forecast_category(subtotals, category)

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
