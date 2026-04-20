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

# -----------------------------------------------------
# UNIVERSAL LOCAL + CLOUD LOADER
# -----------------------------------------------------
@st.cache_data
def load_data():
    # Local path (your Mac)
    local_path = "/Users/yemanehagos/my_first_project/data/MECCA_Financial_Data.xlsx"

    # Cloud path (repo root)
    cloud_path = "MECCA_Financial_Data.xlsx"

    # Choose correct file depending on environment
    file_path = local_path if os.path.exists(local_path) else cloud_path

    df = pd.read_excel(file_path)
    return df


# -----------------------------------------------------
# DATA TRANSFORM HELPERS
# -----------------------------------------------------
def extract_subtotals(df: pd.DataFrame) -> pd.DataFrame:
    expected_cols = {"Year", "Category", "Amount"}
    if not expected_cols.issubset(df.columns):
        raise ValueError(f"Input data must contain columns: {expected_cols}")

    subtotals = (
        df.groupby(["Year", "Category"], as_index=False)["Amount"]
        .sum()
    )
    return subtotals


def compute_yoy(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.sort_values(["Category", "Year"])
    df["YoY Change"] = df.groupby("Category")["Amount"].diff()
    df["YoY %"] = df.groupby("Category")["Amount"].pct_change() * 100
    return df


def forecast_category(subtotals: pd.DataFrame, category: str, years_ahead: int = 3) -> pd.DataFrame:
    df_cat = subtotals[subtotals["Category"] == category].copy()
    if df_cat.empty or df_cat["Year"].nunique() < 2:
        return pd.DataFrame()

    df_cat = df_cat.sort_values("Year")
    x = df_cat["Year"].values.astype(float)
    y = df_cat["Amount"].values.astype(float)

    coeffs = np.polyfit(x, y, 1)
    m, b = coeffs

    last_year = int(df_cat["Year"].max())
    future_years = list(range(last_year + 1, last_year + 1 + years_ahead))
    y_pred = [m * fy + b for fy in future_years]

    forecast_df = pd.DataFrame({
        "Year": future_years,
        "Category": category,
        "Forecast Amount": y_pred
    })

    return forecast_df


# -----------------------------------------------------
# MAIN DASHBOARD
# -----------------------------------------------------
def main():
    st.title("Church Financial Subtotals Dashboard")

    df = load_data()
    subtotals = extract_subtotals(df)

    years_available = sorted(subtotals["Year"].unique())
    selected_years = st.sidebar.multiselect(
        "Select Years",
        options=years_available,
        default=years_available
    )

    filtered = subtotals[subtotals["Year"].isin(selected_years)]

    # -----------------------------------------------------
    # TABS
    # -----------------------------------------------------
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Subtotal Summary",
        "YOY (Board View)",
        "YOY (Detailed View)",
        "Surplus / Deficit",
        "Forecasting"
    ])

    # -----------------------------------------------------
    # TAB 1 — SUBTOTAL SUMMARY
    # -----------------------------------------------------
    with tab1:
        st.subheader("Subtotal Summary — Board Level")

        if filtered.empty:
            st.info("No data available for the selected years.")
        else:
            pivot = filtered.pivot_table(
                index="Year",
                columns="Category",
                values="Amount",
                aggfunc="sum"
            ).sort_index()

            st.dataframe(pivot)

            key_category = st.selectbox(
                "Select category to visualize",
                options=sorted(filtered["Category"].unique())
            )
            chart_data = filtered[filtered["Category"] == key_category]
            chart = alt.Chart(chart_data).mark_bar().encode(
                x="Year:O",
                y="Amount:Q",
                tooltip=["Year", "Amount"]
            ).properties(
                title=f"{key_category} by Year"
            )
            st.altair_chart(chart, use_container_width=True)

    # -----------------------------------------------------
    # TAB 2 — YOY (BOARD VIEW)
    # -----------------------------------------------------
    with tab2:
        st.subheader("Year-over-Year Change — Board View")

        yoy_df = compute_yoy(subtotals)

        yoy_df["Category"] = yoy_df["Category"].replace({
            "Total Revenue (Auto)": "Total Revenue",
            "Total Income (Auto)": "Total Income",
            "Total Expenses (Auto)": "Total Expenses",
            "Net Income (Auto)": "Net Income",
        })

        board_categories = [
            "Total Revenue",
            "Total Income",
            "Total Expenses",
            "Net Income"
        ]

        yoy_board = yoy_df[yoy_df["Category"].isin(board_categories)]
        yoy_board = yoy_board[yoy_board["Year"].isin(selected_years)]

        if yoy_board.empty:
            st.info("No YOY data available for board categories.")
        else:
            yoy_pivot = yoy_board.pivot_table(
                index="Year",
                columns="Category",
                values="YoY Change",
                aggfunc="sum"
            ).sort_index()

            yoy_pct = yoy_board.pivot_table(
                index="Year",
                columns="Category",
                values="YoY %",
                aggfunc="mean"
            ).sort_index()

            def short_number(n):
                if pd.isna(n):
                    return ""
                n = float(n)
                if abs(n) >= 1_000_000:
                    return f"{n/1_000_000:.1f}M"
                elif abs(n) >= 1_000:
                    return f"{n/1_000:.1f}K"
                else:
                    return f"{n:.0f}"

            def format_cell(change, pct):
                if pd.isna(change):
                    return ""
                arrow = "▲" if change > 0 else "▼" if change < 0 else ""
                color = "green" if change > 0 else "red" if change < 0 else "black"
                change_str = short_number(change)
                pct_str = f"{pct:.1f}%" if not pd.isna(pct) else ""
                return f"<span style='color:{color}; font-weight:bold'>{arrow} {change_str} ({pct_str})</span>"

            combined = yoy_pivot.copy().astype("object")
            for row in combined.index:
                for col in combined.columns:
                    combined.loc[row, col] = format_cell(
                        yoy_pivot.loc[row, col],
                        yoy_pct.loc[row, col]
                    )

            st.markdown(combined.to_html(escape=False), unsafe_allow_html=True)

    # -----------------------------------------------------
    # TAB 3 — YOY (DETAILED VIEW)
    # -----------------------------------------------------
    with tab3:
        st.subheader("Year-over-Year Change — Detailed View")

        yoy_df_full = compute_yoy(subtotals)
        yoy_df_full = yoy_df_full[yoy_df_full["Year"].isin(selected_years)]

        if yoy_df_full.empty:
            st.info("No YOY data available.")
        else:
            detailed_pivot = yoy_df_full.pivot_table(
                index=["Category", "Year"],
                values=["YoY Change", "YoY %"],
                aggfunc="sum"
            )
            st.dataframe(detailed_pivot)

    # -----------------------------------------------------
    # TAB 4 — SURPLUS / DEFICIT (BOARD YOY VIEW)
    # -----------------------------------------------------
    with tab4:
        st.subheader("Surplus / Deficit — Board YOY View")

        yoy_df = compute_yoy(subtotals)

        yoy_df["Category"] = yoy_df["Category"].replace({
            "Total Revenue (Auto)": "Total Revenue",
            "Total Income (Auto)": "Total Income",
            "Total Expenses (Auto)": "Total Expenses",
            "Net Income (Auto)": "Net Income",
        })

        PAYROLL_GROUP = ["Salaries & Wages", "Payroll Tax Expense"]

        # Dynamic Utilities detection (handles "Total for Utilities" and typos)
        UTILITIES_GROUP = [c for c in yoy_df["Category"].unique() if "Utilit" in c]

        payroll_df = yoy_df[yoy_df["Category"].isin(PAYROLL_GROUP)]
        if not payroll_df.empty:
            payroll_sum = payroll_df.groupby("Year")[["YoY Change", "YoY %"]].sum().reset_index()
            payroll_sum["Category"] = "Payroll"
        else:
            payroll_sum = pd.DataFrame()

        utilities_df = yoy_df[yoy_df["Category"].isin(UTILITIES_GROUP)]
        if not utilities_df.empty:
            utilities_sum = utilities_df.groupby("Year")[["YoY Change", "YoY %"]].sum().reset_index()
            utilities_sum["Category"] = "Utilities"
        else:
            utilities_sum = pd.DataFrame()

        main_yoy = yoy_df[yoy_df["Category"].isin([
            "Total Revenue",
            "Total Income",
            "Total Expenses",
            "Net Income"
        ])]

        final_yoy = pd.concat([main_yoy, payroll_sum, utilities_sum], ignore_index=True)
        final_yoy = final_yoy[final_yoy["Year"].isin(selected_years)]

        if final_yoy.empty:
            st.info("No Surplus/Deficit YOY data available.")
        else:
            pivot = final_yoy.pivot_table(
                index="Year",
                columns="Category",
                values="YoY Change",
                aggfunc="sum"
            ).sort_index()

            st.dataframe(pivot)

    # -----------------------------------------------------
    # TAB 5 — FORECASTING
    # -----------------------------------------------------
    with tab5:
        st.subheader("Forecasting")

        category_for_forecast = st.selectbox(
            "Select category to forecast",
            options=sorted(subtotals["Category"].unique())
        )
        years_ahead = st.slider("Years to forecast", 1, 5, 3)

        forecast_df = forecast_category(subtotals, category_for_forecast, years_ahead)

        if forecast_df.empty:
            st.info("Not enough data to forecast this category.")
        else:
            st.write("Forecasted values:")
            st.dataframe(forecast_df)

            hist = subtotals[subtotals["Category"] == category_for_forecast].copy()
            hist = hist.sort_values("Year")
            hist["Type"] = "Actual"

            forecast_df_plot = forecast_df.rename(columns={"Forecast Amount": "Amount"})
            forecast_df_plot["Type"] = "Forecast"

            combined = pd.concat([
                hist[["Year", "Amount", "Type"]],
                forecast_df_plot[["Year", "Amount", "Type"]]
            ])

            chart = alt.Chart(combined).mark_line(point=True).encode(
                x="Year:O",
                y="Amount:Q",
                color="Type:N",
                tooltip=["Year", "Amount", "Type"]
            ).properties(
                title=f"Forecast for {category_for_forecast}"
            )

            st.altair_chart(chart, use_container_width=True)


# -----------------------------------------------------
# ENTRY POINT
# -----------------------------------------------------
if __name__ == "__main__":
    main()




