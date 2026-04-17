import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from io import BytesIO

st.set_page_config(page_title="Church Financial Subtotals Dashboard", layout="wide")


# ---------------------------------------------------------
# Helper: Convert DataFrame to Excel bytes for download
# ---------------------------------------------------------
def df_to_excel_bytes(df, sheet_name="Sheet1"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------
@st.cache_data
def load_data():
    file_path = file_path = "MECCA_Financial_Data.xlsx"

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

        all_years.append(df[["Category", "Year", "Amount"]])

    return pd.concat(all_years, ignore_index=True)


# ---------------------------------------------------------
# EXTRACT SUBTOTALS + AUTO TOTALS
# ---------------------------------------------------------
def extract_subtotals(df):
    df = df.copy()

    mask = (
        df["Category"].str.startswith("Total for ")
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

    # Revenue = Income + abs(Expenses)
    revenue_df = pd.merge(
        total_income,
        total_expenses,
        on="Year",
        suffixes=("_Income", "_Expenses")
    )
    revenue_df["Amount"] = revenue_df["Amount_Income"] + revenue_df["Amount_Expenses"].abs()
    revenue_df = revenue_df[["Year", "Amount"]]
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

    auto_totals = auto_totals[["Category", "Year", "Amount"]]

    return pd.concat([subtotals, auto_totals], ignore_index=True)


# ---------------------------------------------------------
# YEAR-OVER-YEAR
# ---------------------------------------------------------
def compute_yoy(subtotals):
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
# SURPLUS / DEFICIT
# ---------------------------------------------------------
def compute_surplus_deficit(subtotals):
    auto = subtotals[subtotals["Category"].isin(
        ["Total Income (Auto)", "Total Expenses (Auto)", "Net Income (Auto)", "Total Revenue (Auto)"]
    )]

    pivot = auto.pivot_table(
        index="Year",
        columns="Category",
        values="Amount",
        aggfunc="sum"
    ).reset_index()

    if "Total Income (Auto)" not in pivot.columns:
        pivot["Total Income (Auto)"] = np.nan
    if "Total Expenses (Auto)" not in pivot.columns:
        pivot["Total Expenses (Auto)"] = np.nan
    if "Total Revenue (Auto)" not in pivot.columns:
        pivot["Total Revenue (Auto)"] = (
            pivot["Total Income (Auto)"] + pivot["Total Expenses (Auto)"].abs()
        )
    if "Net Income (Auto)" not in pivot.columns:
        pivot["Net Income (Auto)"] = (
            pivot["Total Income (Auto)"] - pivot["Total Expenses (Auto)"]
        )

    pivot = pivot.rename(columns={
        "Total Income (Auto)": "Total Income",
        "Total Expenses (Auto)": "Total Expenses",
        "Total Revenue (Auto)": "Total Revenue",
        "Net Income (Auto)": "Net Income",
    })

    return pivot[["Year", "Total Income", "Total Expenses", "Total Revenue", "Net Income"]]


# ---------------------------------------------------------
# FORECASTING
# ---------------------------------------------------------
def forecast_category(subtotals, category, forecast_years=3):
    cat_df = subtotals[subtotals["Category"] == category].copy()
    if cat_df.empty:
        return pd.DataFrame(columns=["Year", "Amount", "Type"])

    cat_df = cat_df.sort_values("Year")
    cat_df = cat_df.dropna(subset=["Amount"])

    if cat_df["Amount"].isna().all() or len(cat_df) < 2:
        return pd.DataFrame(columns=["Year", "Amount", "Type"])

    years = cat_df["Year"].values.astype(float)
    amounts = cat_df["Amount"].values.astype(float)

    coeffs = np.polyfit(years, amounts, 1)
    m, b = coeffs

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

    df = load_data()
    subtotals = extract_subtotals(df)

    years_available = sorted(df["Year"].unique())
    selected_years = st.sidebar.multiselect(
        "Select Years",
        options=years_available,
        default=years_available
    )

    filtered_subtotals = subtotals[subtotals["Year"].isin(selected_years)]

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

        subtotal_pivot = filtered_subtotals.pivot_table(
            index="Category",
            columns="Year",
            values="Amount",
            aggfunc="sum"
        ).sort_index(axis=1)

        st.dataframe(subtotal_pivot.T)

        excel_bytes = df_to_excel_bytes(subtotal_pivot.T.reset_index(), sheet_name="Subtotal Summary")
        st.download_button(
            "Download Subtotal Summary (Excel)",
            data=excel_bytes,
            file_name="subtotal_summary.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # -----------------------------------------------------
    # TAB 2 — YOY WITH ARROWS + COLOR + %
    # -----------------------------------------------------
    with tab2:
        st.subheader("Year-over-Year Change")

        yoy_df = compute_yoy(subtotals)
        yoy_filtered = yoy_df[yoy_df["Year"].isin(selected_years)]

        if not yoy_filtered.empty:
            yoy_pivot = yoy_filtered.pivot_table(
                index="Year",
                columns="Category",
                values="YoY Change",
                aggfunc="sum"
            ).sort_index()

            yoy_pct = yoy_filtered.pivot_table(
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

            excel_bytes_yoy = df_to_excel_bytes(
                yoy_filtered.sort_values(["Category", "Year"]),
                sheet_name="YOY"
            )
            st.download_button(
                "Download YOY (Excel)",
                data=excel_bytes_yoy,
                file_name="yoy_change.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("No YOY data available for selected years.")

    # -----------------------------------------------------
    # TAB 3 — SURPLUS / DEFICIT
    # -----------------------------------------------------
    with tab3:
        st.subheader("Surplus / Deficit")

        sd_df = compute_surplus_deficit(subtotals)
        sd_filtered = sd_df[sd_df["Year"].isin(selected_years)]

        if not sd_filtered.empty:
            st.dataframe(sd_filtered.set_index("Year").T)

            excel_bytes_sd = df_to_excel_bytes(sd_filtered, sheet_name="Surplus Deficit")
            st.download_button(
                "Download Surplus-Deficit (Excel)",
                data=excel_bytes_sd,
                file_name="surplus_deficit.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("No Surplus/Deficit data available.")

    # -----------------------------------------------------
    # TAB 4 — FORECASTING
    # -----------------------------------------------------
    with tab4:
        st.subheader("Forecasting")

        forecast_mode = st.radio(
            "Forecast Mode",
            ["Totals Only", "Auto Totals Only", "All Categories"],
            horizontal=True,
            key="forecast_mode_selector"
        )

        if forecast_mode == "Totals Only":
            category_list = sorted([
                c for c in subtotals["Category"].unique()
                if c.startswith("Total for ")
            ])
        elif forecast_mode == "Auto Totals Only":
            category_list = sorted([
                c for c in subtotals["Category"].unique()
                if "(Auto)" in c
            ])
        else:
            category_list = sorted(subtotals["Category"].unique())

        selected_category = st.selectbox(
            "Select Category",
            category_list,
            index=0,
            key="forecast_category_selector"
        )

        forecast_df = forecast_category(subtotals, selected_category, forecast_years=3)

        if forecast_df.empty:
            st.warning(f"No sufficient numeric data to forecast for '{selected_category}'.")
        else:
            chart = alt.Chart(forecast_df).mark_line(point=True).encode(
                x=alt.X("Year:O", title="Year"),
                y=alt.Y("Amount:Q", title="Amount"),
                color=alt.Color("Type:N", title=""),
                tooltip=["Year", "Amount", "Type"]
            ).properties(
                width=800,
                height=400,
                title=f"Actual vs Forecast for {selected_category}"
            )

            st.altair_chart(chart, width="stretch")

            excel_bytes_fc = df_to_excel_bytes(forecast_df, sheet_name="Forecast")
            st.download_button(
                "Download Forecast (Excel)",
                data=excel_bytes_fc,
                file_name=f"forecast_{selected_category}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    # -----------------------------------------------------
    # DOWNLOAD EVERYTHING AS ONE EXCEL FILE
    # -----------------------------------------------------
    st.subheader("Download All Dashboard Results")

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:

        # 1. Subtotal Summary
        subtotal_pivot.T.reset_index().to_excel(
            writer, sheet_name="Subtotal Summary", index=False
        )

        # 2. YOY
        if not yoy_filtered.empty:
            yoy_filtered.sort_values(["Category", "Year"]).to_excel(
                writer, sheet_name="YOY", index=False
            )
        else:
            pd.DataFrame({"Message": ["No YOY data available"]}).to_excel(
                writer, sheet_name="YOY", index=False
            )

        # 3. Surplus / Deficit
        if not sd_filtered.empty:
            sd_filtered.to_excel(
                writer, sheet_name="Surplus Deficit", index=False
            )
        else:
            pd.DataFrame({"Message": ["No Surplus/Deficit data available"]}).to_excel(
                writer, sheet_name="Surplus Deficit", index=False
            )

        # 4. Forecasts for ALL categories
        all_forecasts = []
        for cat in sorted(subtotals["Category"].unique()):
            fc = forecast_category(subtotals, cat, forecast_years=3)
            if not fc.empty:
                fc["Category"] = cat
                all_forecasts.append(fc)

        if all_forecasts:
            all_fc_df = pd.concat(all_forecasts, ignore_index=True)
            all_fc_df.to_excel(writer, sheet_name="All Forecasts", index=False)
        else:
            pd.DataFrame({"Message": ["No forecast data available"]}).to_excel(
                writer, sheet_name="All Forecasts", index=False
            )

    excel_bytes_all = output.getvalue()

    st.download_button(
        "⬇️ Download FULL Dashboard (Excel)",
        data=excel_bytes_all,
        file_name="full_dashboard_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


if __name__ == "__main__":
    main()
