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
# PAGE CONFIG
# ---------------------------------------------------------
st.set_page_config(
    page_title="Church Financial Subtotals Dashboard",
    layout="wide"
)

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
    if c in [ "expenses", "net income", "net operating income"]:
        return "Header"
    return "Detail"


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
# ASSIGN Income / Expense / Subtotal
# ---------------------------------------------------------
# ---------------------------------------------------------
# ASSIGN Income / Expense / Subtotal (Corrected)
# ---------------------------------------------------------
def assign_income_expense(df):
    df = df.copy()
    df["Type"] = None

    for year, group in df.groupby("Year"):
        # Find subtotal boundaries
        income_total_idx = group[group["Category"].str.lower() == "total for income"].index
        expense_total_idx = group[group["Category"].str.lower() == "total for expenses"].index

        # Skip if sheet is malformed
        if len(income_total_idx) == 0 or len(expense_total_idx) == 0:
            continue

        income_end = income_total_idx[0]      # row of "Total for Income"
        expense_end = expense_total_idx[0]    # row of "Total for Expenses"

        # 1. INCOME BLOCK (exclude "Total for Income")
        df.loc[group.index.min():income_end - 1, "Type"] = "Income"

        # 2. EXPENSE BLOCK (exclude both totals)
        df.loc[income_end + 1:expense_end - 1, "Type"] = "Expense"

        # 3. SUBTOTALS override everything
        subtotal_idx = group.index[group["Category"].str.lower().str.startswith("total for ")]
        df.loc[subtotal_idx, "Type"] = "Subtotal"

    return df
# ---------------------------------------------------------
# EXTRACT SUBTOTALS + AUTO TOTALS
# ---------------------------------------------------------
def extract_subtotals(df):
    df = df.copy()

    mask = (
        df["Category"].str.startswith("Total for ")
        #| (df["Category"] == "Gross Profit")
        | (df["Category"] == "Net Income")
        | (df["Category"] == "Net Operating Income")
    )
    subtotals = df[mask].reset_index(drop=True)

    income_rows = subtotals[subtotals["Category"] == "Total for Income"]
    total_income = income_rows.groupby("Year")["Amount"].sum().reset_index()
    total_income["Category"] = "Total Income (Auto)"

    expense_rows = subtotals[subtotals["Category"] == "Total for Expenses"]
    total_expenses = expense_rows.groupby("Year")["Amount"].sum().reset_index()
    total_expenses["Category"] = "Total Expenses (Auto)"

    # Revenue = Total for Income
    revenue_df = total_income.copy()
    revenue_df["Category"] = "Total Revenue (Auto)"

    net_income = pd.merge(
        total_income,
        total_expenses,
        on="Year",
        suffixes=("_Income", "_Expenses")
    )
    net_income["Amount"] = net_income["Amount_Income"] - net_income["Amount_Expenses"]
    net_income = net_income[["Year", "Amount"]]
    net_income["Category"] = "Net Income (Auto)"

    auto_totals = pd.concat(
        [total_income, total_expenses, revenue_df, net_income],
        ignore_index=True
    )

    return pd.concat([subtotals, auto_totals], ignore_index=True)


# ---------------------------------------------------------
# YOY CALC
# ---------------------------------------------------------
def compute_yoy(subtotals):
    df = subtotals.copy()
    df = df.sort_values(["Category", "Year"])
    df["YoY Change"] = df.groupby("Category")["Amount"].diff()
    df["YoY %"] = df.groupby("Category")["Amount"].pct_change() * 100
    return df


# ---------------------------------------------------------
# SURPLUS / DEFICIT
# ---------------------------------------------------------
def compute_surplus_deficit(subtotals):
    df = subtotals.copy()

    total_income = df[df["Category"] == "Total Income (Auto)"][["Year", "Amount"]]
    total_income = total_income.rename(columns={"Amount": "Total Income"})

    total_expenses = df[df["Category"] == "Total Expenses (Auto)"][["Year", "Amount"]]
    total_expenses = total_expenses.rename(columns={"Amount": "Total Expenses"})

    revenue = df[df["Category"] == "Total Revenue (Auto)"][["Year", "Amount"]]
    revenue = revenue.rename(columns={"Amount": "Total Revenue"})

    net_income = df[df["Category"] == "Net Income (Auto)"][["Year", "Amount"]]
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
def forecast_category(df, category, periods=3):
    data = df[df["Category"] == category].groupby("Year")["Amount"].sum().reset_index()
    if len(data) < 2:
        return pd.DataFrame()

    x = data["Year"].values
    y = data["Amount"].values

    coeffs = np.polyfit(x, y, 1)
    m, b = coeffs

    last_year = x.max()
    future_years = np.arange(last_year + 1, last_year + 1 + periods)
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
    return d.groupby(["Year", "Category"])["Amount"].sum().reset_index()


def get_top_expense(df, n=5):
    d = df.copy()
    d = d[d["Type"] == "Expense"]
    d = d[~d["Category"].str.startswith("Total for ")]
    return d.groupby(["Year", "Category"])["Amount"].sum().reset_index()


# ---------------------------------------------------------
# PDF GENERATION
# ---------------------------------------------------------
def generate_pdf(subtotals, year):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title = Paragraph(f"<b>MECCA Financial Subtotals Report – {year}</b>", styles["Title"])
    story.append(title)
    story.append(Spacer(1, 12))

    df_year = subtotals[subtotals["Year"] == year].copy()
    df_year = df_year[["Category", "Amount"]]

    table_data = [["Category", "Amount"]]
    for _, row in df_year.iterrows():
        table_data.append([row["Category"], f"${row['Amount']:,.2f}"])

    table = Table(table_data, colWidths=[300, 150])
    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
    ])

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
# Add the same style function (reuse it everywhere)
# ---------------------------------------------------------
def style_top5(df):
    # df index = Category rows
    n = len(df)

    def highlight(row_index):
        if row_index < 3:   # top 3
            return "background-color: #d4edda;"   # light green
        else:               # bottom 2
            return "background-color: #fff3cd;"   # light yellow

    return df.style.apply(
        lambda row: [highlight(row.name)] * len(df.columns),
        axis=1
    ).format("{:,.2f}")

def add_rank_icons(df):
    df = df.copy()
    n = len(df)

    base_icons = ["🥇", "🥈", "🥉", "⭐", "⭐"]

    # If df has more than 5 rows, extend icons
    if n > 5:
        icons = base_icons + ["⭐"] * (n - 5)
    else:
        icons = base_icons[:n]

    df.insert(0, "Rank", icons)
    return df


def add_summary_icons(df):
    df = df.copy()
    n = len(df)

    # Top 3 = ▲, rest = ▼
    icons = ["▲"] * min(3, n) + ["▼"] * max(0, n - 3)

    df.insert(0, "Trend", icons)
    return df
    
def add_yoy_icons(df):
    df = df.copy()
    icons = []

    for change in df["YoY Change"]:
        if pd.isna(change):
            icons.append("⏺️")
        elif change > 0:
            icons.append("📈")
        elif change < 0:
            icons.append("📉")
        else:
            icons.append("⏺️")

    df.insert(0, "Trend", icons)
    return df

def add_forecast_icons(df):
    df = df.copy()
    mean_val = df["Amount"].mean()

    icons = ["🔼" if amt > mean_val else "🔽" for amt in df["Amount"]]
    df.insert(0, "Trend", icons)
    return df

# ---------------------------------------------------------
# MAIN APP
# ---------------------------------------------------------
def main():
    st.title("📊 MekanSelam Medhanialem Ethiopian Orthodox Church->> Financial Dashboard")

      # Load data
    df = load_data()
    subtotals = extract_subtotals(df)
    yoy_df = compute_yoy(subtotals)
    sd_df = compute_surplus_deficit(subtotals)

    years = sorted(df["Year"].unique())
    selected_years = st.multiselect("Select Years", years, default=years)

    # Tabs
    tab1, tab2, tab_top, tab3, tab4, tab_pdf = st.tabs([
        "Subtotal Summary",
        "YOY Summary",
        "Top Income & Expenses",
        "Surplus / Deficit",
        "Forecasting",
        "Board PDF"
    ])

    # -----------------------------------------------------
    # TAB 1 — UNIFIED SUBTOTAL SUMMARY (NEW)
    # -----------------------------------------------------
    with tab1:
        st.subheader("📘 Unified Subtotal Summary (Pivot View)")

        # --- 1. BUILD MAIN SUMMARY PIVOT ---
        summary_rows = []

        for year, group in subtotals.groupby("Year"):

            # Revenue = Total for Income
            revenue = group.loc[
                group["Category"].str.lower() == "total for income",
                "Amount"
            ].sum()

            total_income = revenue

            total_expenses = group.loc[
                group["Category"].str.lower() == "total for expenses",
                "Amount"
            ].sum()

            net_income = total_income - total_expenses

            payroll = df[
                (df["Year"] == year) &
                (df["Category"].isin(["Salaries & Wages", "Payroll Tax Expense"]))
            ]["Amount"].sum()

            utilities = df[
                (df["Year"] == year) &
                (df["Category"].str.contains("Utilit", case=False))
            ]["Amount"].sum()

            summary_rows.append(["Total Revenue", year, revenue])
            summary_rows.append(["Total Income", year, total_income])
            summary_rows.append(["Total Expenses", year, total_expenses])
            summary_rows.append(["Net Income", year, net_income])
            summary_rows.append(["Payroll", year, payroll])
            summary_rows.append(["Utilities", year, utilities])

        summary_df = pd.DataFrame(summary_rows, columns=["Category", "Year", "Amount"])
        summary_pivot = summary_df.pivot_table(
            index="Category",
            columns="Year",
            values="Amount",
            aggfunc="sum"
        ).fillna(0)

        st.markdown("### 📘 Main Financial Summary")
        #st.dataframe(summary_pivot.style.format("{:,.2f}"), use_container_width=True)
        st.dataframe(style_top5(add_rank_icons(summary_pivot)), use_container_width=True)

        st.divider()

        # -----------------------------------------------------
        # TOP 5 INCOME PIVOT (Corrected)
        # -----------------------------------------------------
        st.markdown("### 💰 Top 5 Income Categories (All Years)")

        income_df = df[
            (df["Type"] == "Income") &
            (~df["Category"].str.lower().str.startswith("total for"))
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

        #st.dataframe(top_income_pivot.style.format("{:,.2f}"), use_container_width=True)
        st.dataframe(style_top5(add_rank_icons(top_income_pivot)), use_container_width=True)

        st.divider()

        # -----------------------------------------------------
        # TOP 5 EXPENSE PIVOT (Corrected)
        # -----------------------------------------------------
        st.markdown("### 📉 Top 5 Expense Categories (All Years)")

        expense_df = df[
            (df["Type"] == "Expense") &
            (~df["Category"].str.lower().str.startswith("total for"))
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

        #st.dataframe(top_expense_pivot.style.format("{:,.2f}"), use_container_width=True)
        st.dataframe(style_top5(add_rank_icons(top_expense_pivot)), use_container_width=True)

    # -----------------------------------------------------
    # TAB 2 — YOY SUMMARY
    # -----------------------------------------------------
    with tab2:
        st.subheader("YOY Summary")

        yoy_filtered = yoy_df[yoy_df["Year"].isin(selected_years)]

        PAYROLL_GROUP = ["Salaries & Wages", "Payroll Tax Expense"]
        payroll_df = yoy_filtered[yoy_filtered["Category"].isin(PAYROLL_GROUP)]
        if not payroll_df.empty:
            payroll_sum = payroll_df.groupby("Year")[["YoY Change", "YoY %"]].sum().reset_index()
            payroll_sum["Category"] = "Payroll"
        else:
            payroll_sum = pd.DataFrame()

        UTILITIES_GROUP = [c for c in yoy_filtered["Category"].unique() if "Utilit" in c]
        utilities_df = yoy_filtered[yoy_filtered["Category"].isin(UTILITIES_GROUP)]
        if not utilities_df.empty:
            utilities_sum = utilities_df.groupby("Year")[["YoY Change", "YoY %"]].sum().reset_index()
            utilities_sum["Category"] = "Utilities"
        else:
            utilities_sum = pd.DataFrame()

        board_totals = yoy_filtered[
            yoy_filtered["Category"].isin([
                "Total Income (Auto)",
                "Total Expenses (Auto)",
                "Total Revenue (Auto)",
                "Net Income (Auto)"
            ])
        ]

        final_yoy = pd.concat([board_totals, payroll_sum, utilities_sum], ignore_index=True)

        if final_yoy.empty:
            st.info("No YOY data available.")
        else:
            yoy_pivot = final_yoy.pivot_table(
                index="Year",
                columns="Category",
                values="YoY Change",
                aggfunc="sum"
            ).sort_index()

            yoy_pct = final_yoy.pivot_table(
                index="Year",
                columns="Category",
                values="YoY %",
                aggfunc="mean"
            ).sort_index()

            def format_cell(change, pct):
                if pd.isna(change):
                    return ""
                arrow = "▲" if change > 0 else "▼" if change < 0 else ""
                color = "green" if change > 0 else "red" if change < 0 else "black"
                pct_str = f"{pct:.1f}%" if not pd.isna(pct) else ""
                return f"<span style='color:{color}; font-weight:bold'>{arrow} {change:.0f} ({pct_str})</span>"

            combined = yoy_pivot.copy().astype("object")
            for row in combined.index:
                for col in combined.columns:
                    combined.loc[row, col] = format_cell(
                        yoy_pivot.loc[row, col],
                        yoy_pct.loc[row, col] if col in yoy_pct.columns else np.nan
                    )

            st.markdown(combined.to_html(escape=False), unsafe_allow_html=True)

    # -----------------------------------------------------
    # TAB 3 — TOP INCOME & EXPENSES (FORECASTING)
    # -----------------------------------------------------
    with tab_top:
        st.subheader("Top Income & Top Expenses")

        top_income = get_top_income(df)
        top_expense = get_top_expense(df)

        year = st.selectbox("Select Year", years)

        inc_year = top_income[top_income["Year"] == year].sort_values("Amount", ascending=False).head(5)
        exp_year = top_expense[top_expense["Year"] == year].sort_values("Amount", ascending=False).head(5)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Top Income Categories")
            st.dataframe(inc_year, use_container_width=True)

            if not inc_year.empty:
                selected_inc = st.selectbox("Forecast Income Category", inc_year["Category"])
                inc_forecast = forecast_category(df, selected_inc)
                if not inc_forecast.empty:
                    chart = alt.Chart(inc_forecast).mark_line(point=True).encode(
                        x=alt.X("Year:O"),
                        y=alt.Y("Amount:Q"),
                        color="Type:N",
                        tooltip=["Year", "Amount", "Type"]
                    ).properties(title=f"Forecast — {selected_inc}", width=400, height=300)
                    st.altair_chart(chart, use_container_width=True)

        with col2:
            st.markdown("### Top Expense Categories")
            st.dataframe(exp_year, use_container_width=True)

            if not exp_year.empty:
                selected_exp = st.selectbox("Forecast Expense Category", exp_year["Category"])
                exp_forecast = forecast_category(df, selected_exp)
                if not exp_forecast.empty:
                    chart = alt.Chart(exp_forecast).mark_line(point=True).encode(
                        x=alt.X("Year:O"),
                        y=alt.Y("Amount:Q"),
                        color="Type:N",
                        tooltip=["Year", "Amount", "Type"]
                    ).properties(title=f"Forecast — {selected_exp}", width=400, height=300)
                    st.altair_chart(chart, use_container_width=True)

    # -----------------------------------------------------
    # TAB 4 — SURPLUS / DEFICIT
    # -----------------------------------------------------
    with tab3:
        st.subheader("Surplus / Deficit")

        sd_filtered = sd_df[sd_df["Year"].isin(selected_years)]
        if sd_filtered.empty:
            st.info("No Surplus/Deficit data available.")
        else:
            sd_filtered = sd_filtered.set_index("Year")
            desired_order = ["Total Revenue", "Total Income", "Total Expenses", "Net Income"]
            existing = [c for c in desired_order if c in sd_filtered.columns]
            others = [c for c in sd_filtered.columns if c not in existing]
            st.dataframe(sd_filtered[existing + others].T, use_container_width=True)

    # -----------------------------------------------------
    # TAB 5 — FORECASTING
    # -----------------------------------------------------
    with tab4:
        st.subheader("Forecasting")

        forecast_mode = st.radio(
            "Forecast Mode",
            ["Totals Only", "Auto Totals Only", "All Categories"],
            horizontal=True
        )

        if forecast_mode == "Totals Only":
            category_list = sorted([
                c for c in subtotals["Category"].unique()
                if c.startswith("Total for ") or c == "Gross Profit"
            ])
        elif forecast_mode == "Auto Totals Only":
            category_list = sorted([
                c for c in subtotals["Category"].unique()
                if "(Auto)" in c
            ])
        else:
            category_list = sorted([
                c for c in subtotals["Category"].unique()
                if not c.endswith("(Auto)")
            ])

        selected_category = st.selectbox("Select Category", category_list)
        forecast_df = forecast_category(subtotals, selected_category)

        if forecast_df.empty:
            st.warning("Not enough data to forecast.")
        else:
            chart = alt.Chart(forecast_df).mark_line(point=True).encode(
                x=alt.X("Year:O"),
                y=alt.Y("Amount:Q"),
                color="Type:N",
                tooltip=["Year", "Amount", "Type"]
            ).properties(width=800, height=400, title=f"Forecast — {selected_category}")
            st.altair_chart(chart, use_container_width=True)

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
                file_name=f"MECCA_Financial_Subtotals_{year_for_pdf}.pdf",
                mime="application/pdf"
            )
if __name__ == "__main__":
    main()
