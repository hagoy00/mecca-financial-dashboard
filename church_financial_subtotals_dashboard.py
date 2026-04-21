import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from io import BytesIO
import os

# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------
# Sets the title and layout of the Streamlit app
st.set_page_config(
    page_title="Church Financial Subtotals Dashboard",
    layout="wide"
)

# ---------------------------------------------------------
# UNIVERSAL FILE PATH (LOCAL + CLOUD)
# ---------------------------------------------------------
# Local path on your Mac
LOCAL_PATH = "/Users/yemanehagos/my_first_project/data/MECCA_Financial_Data.xlsx"

# Cloud path (file in GitHub repo root)
CLOUD_PATH = "MECCA_Financial_Data.xlsx"

def get_file_path():
    """
    Automatically selects the correct file path:
    - Uses local path if running on your Mac
    - Uses cloud path if running on Streamlit Cloud
    """
    if os.path.exists(LOCAL_PATH):
        return LOCAL_PATH
    return CLOUD_PATH


# ---------------------------------------------------------
# HELPER: Convert DataFrame to Excel bytes for download
# ---------------------------------------------------------
def df_to_excel_bytes(df, sheet_name="Sheet1"):
    """
    Converts a DataFrame into an Excel file in memory.
    Used for download buttons.
    """
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()


# ---------------------------------------------------------
# LOAD DATA FROM EXCEL
# ---------------------------------------------------------
@st.cache_data
def load_data():
    """
    Loads all sheets whose names are valid years (e.g., 2021, 2022).
    Cleans numeric values and returns a combined DataFrame.
    """
    file_path = get_file_path()
    xls = pd.ExcelFile(file_path)
    all_years = []

    for sheet in xls.sheet_names:
        # Only load sheets named like "2021", "2022", etc.
        try:
            year = int(sheet)
        except:
            continue

        df = pd.read_excel(file_path, sheet_name=sheet)
        df.columns = df.columns.str.strip()

        if "Category" not in df.columns:
            continue

        # Identify the numeric column (the year column)
        value_col = [c for c in df.columns if c != "Category"][0]
        df = df.rename(columns={value_col: "Amount"})

        # Clean numeric values
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
        all_years.append(df[["Category", "Year", "Amount"]])

    return pd.concat(all_years, ignore_index=True)


# ---------------------------------------------------------
# EXTRACT SUBTOTALS + AUTO TOTALS
# ---------------------------------------------------------
def extract_subtotals(df):
    """
    Extracts:
    - All "Total for ..." rows
    - Gross Profit
    - Net Income (if present)
    - Auto totals (Revenue, Income, Expenses, Net Income)

    Auto totals are used internally but hidden from the dashboard,
    except for the four main totals which are renamed and shown.
    """
    df = df.copy()

    # Manual subtotals from Excel
    mask = (
        df["Category"].str.startswith("Total for ")
        | (df["Category"] == "Gross Profit")
        | (df["Category"] == "Net Income")
        | (df["Category"] == "Net Operating Income")
    )

    subtotals = df[mask].reset_index(drop=True)

    # ------------------------------
    # AUTO TOTAL: Total Income
    # ------------------------------
    income_rows = subtotals[subtotals["Category"] == "Total for Income"]
    total_income = income_rows.groupby("Year")["Amount"].sum().reset_index()
    total_income["Category"] = "Total Income (Auto)"

    # ------------------------------
    # AUTO TOTAL: Total Expenses
    # ------------------------------
    expense_rows = subtotals[subtotals["Category"] == "Total for Expenses"]
    total_expenses = expense_rows.groupby("Year")["Amount"].sum().reset_index()
    total_expenses["Category"] = "Total Expenses (Auto)"

    # ------------------------------
    # AUTO TOTAL: Total Revenue = Income + abs(Expenses)
    # ------------------------------
    revenue_df = pd.merge(
        total_income,
        total_expenses,
        on="Year",
        suffixes=("_Income", "_Expenses")
    )
    revenue_df["Amount"] = revenue_df["Amount_Income"] + revenue_df["Amount_Expenses"].abs()
    revenue_df = revenue_df[["Year", "Amount"]]
    revenue_df["Category"] = "Total Revenue (Auto)"

    # ------------------------------
    # AUTO TOTAL: Net Income = Income - Expenses
    # ------------------------------
    net_income = pd.merge(
        total_income,
        total_expenses,
        on="Year",
        suffixes=("_Income", "_Expenses")
    )
    net_income["Amount"] = net_income["Amount_Income"] - net_income["Amount_Expenses"]
    net_income = net_income[["Year", "Amount"]]
    net_income["Category"] = "Net Income (Auto)"

    # Combine everything
    auto_totals = pd.concat(
        [total_income, total_expenses, revenue_df, net_income],
        ignore_index=True
    )

    return pd.concat([subtotals, auto_totals], ignore_index=True)

# ---------------------------------------------------------
# YEAR-OVER-YEAR CALCULATION
# ---------------------------------------------------------
def compute_yoy(subtotals):
    """
    Computes year-over-year change for each subtotal category.
    Auto totals are included internally but will be hidden later.
    """
    pivot = subtotals.pivot_table(
        index="Category",
        columns="Year",
        values="Amount",
        aggfunc="sum"
    ).sort_index(axis=1)

    yoy_list = []
    years = sorted(subtotals["Year"].unique())

    for i in range(1, len(years)):
        prev_y = years[i - 1]
        cur_y = years[i]

        diff = pivot[cur_y] - pivot[prev_y]
        pct = diff / pivot[prev_y].replace(0, np.nan) * 100

        tmp = pd.DataFrame({
            "Category": pivot.index,
            "Year": cur_y,
            "YoY Change": diff,
            "YoY %": pct
        })
        yoy_list.append(tmp)

    if not yoy_list:
        return pd.DataFrame(columns=["Category", "Year", "YoY Change", "YoY %"])

    return pd.concat(yoy_list, ignore_index=True)


# ---------------------------------------------------------
# SURPLUS / DEFICIT (Auto totals renamed + shown)
# ---------------------------------------------------------
def compute_surplus_deficit(subtotals):
    """
    Uses Auto totals internally but renames them to clean names:
    - Total Revenue
    - Total Income
    - Total Expenses
    - Net Income
    """
    auto = subtotals[subtotals["Category"].str.contains("(Auto)")]

    pivot = auto.pivot_table(
        index="Year",
        columns="Category",
        values="Amount",
        aggfunc="sum"
    ).reset_index()

    pivot = pivot.rename(columns={
        "Total Revenue (Auto)": "Total Revenue",
        "Total Income (Auto)": "Total Income",
        "Total Expenses (Auto)": "Total Expenses",
        "Net Income (Auto)": "Net Income",
    })

    return pivot[["Year", "Total Revenue", "Total Income", "Total Expenses", "Net Income"]]


# ---------------------------------------------------------
# FORECASTING (Linear Regression)
# ---------------------------------------------------------
def forecast_category(subtotals, category, forecast_years=3):
    """
    Forecasts future values using a simple linear regression.
    Works for both Auto totals and manual totals.
    """
    cat_df = subtotals[subtotals["Category"] == category].copy()
    if cat_df.empty:
        return pd.DataFrame(columns=["Year", "Amount", "Type"])

    cat_df = cat_df.sort_values("Year")
    cat_df = cat_df.dropna(subset=["Amount"])

    if len(cat_df) < 2:
        return pd.DataFrame(columns=["Year", "Amount", "Type"])

    years = cat_df["Year"].values.astype(float)
    amounts = cat_df["Amount"].values.astype(float)

    m, b = np.polyfit(years, amounts, 1)

    last_year = int(years.max())
    future_years = np.arange(last_year + 1, last_year + 1 + forecast_years)
    future_amounts = m * future_years + b

    actual_df = pd.DataFrame({
        "Year": years.astype(int),
        "Amount": amounts,
        "Type": "Actual"
    })

    forecast_df = pd.DataFrame({
        "Year": future_years.astype(int),
        "Amount": future_amounts,
        "Type": "Forecast"
    })

    return pd.concat([actual_df, forecast_df], ignore_index=True)


# ---------------------------------------------------------
# MAIN DASHBOARD
# ---------------------------------------------------------
def main():
    st.title("Church Financial Subtotals Dashboard")

    # Load data
    df = load_data()
    subtotals = extract_subtotals(df)

    # Sidebar year selection
    years_available = sorted(df["Year"].unique())
    selected_years = st.sidebar.multiselect(
        "Select Years",
        options=years_available,
        default=years_available
    )

    filtered = subtotals[subtotals["Year"].isin(selected_years)]

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "Subtotal Summary",
        "Year-over-Year Change",
        "Surplus / Deficit",
        "Forecasting"
    ])

    # -----------------------------------------------------
    # TAB 1 — SUBTOTAL SUMMARY
    # -----------------------------------------------------
    with tab1:
        st.subheader("Subtotal Summary")

        # Hide Auto totals EXCEPT the 4 main totals (renamed)
        visible = filtered.copy()

        # Promote Auto totals into visible totals
        visible["Category"] = visible["Category"].replace({
            "Total Revenue (Auto)": "Total Revenue",
            "Total Income (Auto)": "Total Income",
            "Total Expenses (Auto)": "Total Expenses",
            "Net Income (Auto)": "Net Income",
        })

        # Hide all other Auto totals
        visible = visible[~visible["Category"].str.contains("(Auto)")]

        subtotal_pivot = visible.pivot_table(
            index="Category",
            columns="Year",
            values="Amount",
            aggfunc="sum"
        ).sort_index(axis=1)

        # Desired ordering
        desired_order = [
            "Total Revenue",
            "Total Income",
            "Total Expenses",
            "Net Income",
            "Gross Profit",
        ]

        existing = [c for c in desired_order if c in subtotal_pivot.index]
        others = [c for c in subtotal_pivot.index if c not in existing]

        subtotal_pivot = subtotal_pivot.loc[existing + others]

        st.dataframe(subtotal_pivot.T)

    # -----------------------------------------------------
    # TAB 2 — YEAR-OVER-YEAR CHANGE
    # -----------------------------------------------------
    
    with tab2:
        st.subheader("Year-over-Year Change — Board + Payroll + Utilities")

        yoy_df = compute_yoy(subtotals)

        # Normalize Auto totals
        yoy_df["Category"] = yoy_df["Category"].replace({
        "Total Revenue (Auto)": "Total Revenue",
        "Total Income (Auto)": "Total Income",
        "Total Expenses (Auto)": "Total Expenses",
        "Net Income (Auto)": "Net Income",
        })

    # Filter selected years
    yoy_df = yoy_df[yoy_df["Year"].isin(selected_years)]

    # -------------------------------
    # 1. BOARD TOTALS
    # -------------------------------
    board_totals = yoy_df[yoy_df["Category"].isin([
        "Total Revenue",
        "Total Income",
        "Total Expenses",
        "Net Income"
    ])]

    # -------------------------------
    # 2. PAYROLL GROUP
    # -------------------------------
    PAYROLL_GROUP = ["Salaries & Wages", "Payroll Tax Expense"]

    payroll_df = yoy_df[yoy_df["Category"].isin(PAYROLL_GROUP)]
    if not payroll_df.empty:
        payroll_sum = payroll_df.groupby("Year")[["YoY Change", "YoY %"]].sum().reset_index()
        payroll_sum["Category"] = "Payroll"
    else:
        payroll_sum = pd.DataFrame()

    # -------------------------------
    # 3. UTILITIES GROUP
    # -------------------------------
    UTILITIES_GROUP = [c for c in yoy_df["Category"].unique() if "Utilit" in c]

    utilities_df = yoy_df[yoy_df["Category"].isin(UTILITIES_GROUP)]
    if not utilities_df.empty:
        utilities_sum = utilities_df.groupby("Year")[["YoY Change", "YoY %"]].sum().reset_index()
        utilities_sum["Category"] = "Utilities"
    else:
        utilities_sum = pd.DataFrame()

    # -------------------------------
    # COMBINE ALL SIX FIELDS
    # -------------------------------
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
                    yoy_pct.loc[row, col]
                )

        st.markdown(combined.to_html(escape=False), unsafe_allow_html=True)

    # -----------------------------------------------------
    # TAB 3 — SURPLUS / DEFICIT
    # -----------------------------------------------------
    with tab3:
        st.subheader("Surplus / Deficit")

        sd_df = compute_surplus_deficit(subtotals)
        sd_filtered = sd_df[sd_df["Year"].isin(selected_years)]

        if sd_filtered.empty:
            st.info("No Surplus/Deficit data available.")
        else:
            sd_filtered = sd_filtered.set_index("Year")

            desired_order = ["Total Revenue", "Total Income", "Total Expenses", "Net Income"]
            existing = [c for c in desired_order if c in sd_filtered.columns]
            others = [c for c in sd_filtered.columns if c not in existing]

            st.dataframe(sd_filtered[existing + others].T)

    # -----------------------------------------------------
    # TAB 4 — FORECASTING
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
            ).properties(width=800, height=400)

            st.altair_chart(chart, use_container_width=True)


if __name__ == "__main__":
    main()
