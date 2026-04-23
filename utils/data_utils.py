import pandas as pd

DATA_FILE = "MECCA_Financial_Data.xlsx"

# ---------------------------------------------------------
# 1. CLASSIFY ROW KIND (Detail, Header, Subtotal)
# ---------------------------------------------------------
def classify_row_kind(cat):
    c = str(cat).strip().lower()

    if c.startswith("total for "):
        return "Subtotal"

    if c in ["gross profit", "expenses"]:
        return "Header"

    return "Detail"


# ---------------------------------------------------------
# 2. MAIN LOADER — READ ALL YEAR SHEETS
# ---------------------------------------------------------
def load_all_years(path=DATA_FILE):
    xls = pd.ExcelFile(path)
    all_years = []

    for sheet in xls.sheet_names:
        # Only load sheets that are numeric years
        try:
            year = int(sheet)
        except:
            continue

        df = pd.read_excel(path, sheet_name=sheet)

        if "Category" not in df.columns:
            continue

        # The value column is the only non-Category column
        value_col = [c for c in df.columns if c != "Category"][0]

        df_long = pd.DataFrame({
            "Year": year,
            "Category": df["Category"].astype(str),
            "Amount": df[value_col]
        })

        df_long["Kind"] = df_long["Category"].apply(classify_row_kind)

        all_years.append(df_long)

    df = pd.concat(all_years, ignore_index=True)

    # Assign Income / Expense / Subtotal
    df = assign_income_expense(df)

    return df


# ---------------------------------------------------------
# 3. ASSIGN Income / Expense / Subtotal
# ---------------------------------------------------------
def assign_income_expense(df):
    df = df.copy()
    df["Type"] = None

    for year, group in df.groupby("Year"):
        # Income block ends at "Total for Income"
        income_end = group[group["Category"].str.lower() == "total for income"].index
        if len(income_end) > 0:
            end_idx = income_end[0]
            df.loc[group.index[0]:end_idx, "Type"] = "Income"

        # Expense block ends at "Total for Expenses"
        expense_end = group[group["Category"].str.lower() == "total for expenses"].index
        if len(expense_end) > 0:
            end_idx = expense_end[0]
            df.loc[group.index[0]:end_idx, "Type"] = "Expense"

        # Subtotals override the above
        df.loc[group.index[group["Kind"] == "Subtotal"], "Type"] = "Subtotal"
#df.loc[group["Kind"] == "Subtotal", "Type"] = "Subtotal"
        

    return df


# ---------------------------------------------------------
# 4. BOARD CATEGORY BUILDER
# ---------------------------------------------------------
def build_board_categories(df):
    df = df.copy()

    board_rows = []

    for year, group in df.groupby("Year"):
        total_income = group.loc[
            group["Category"].str.strip().str.lower() == "total for income",
            "Amount"
        ].sum()

        total_expenses = group.loc[
            group["Category"].str.strip().str.lower() == "total for expenses",
            "Amount"
        ].sum()

        net_income = total_income - total_expenses

        board_rows.append({"Year": year, "Board Category": "Total Income", "Amount": total_income})
        board_rows.append({"Year": year, "Board Category": "Total Expenses", "Amount": total_expenses})
        board_rows.append({"Year": year, "Board Category": "Net Income", "Amount": net_income})

    board_df = pd.DataFrame(board_rows)
    return board_df


# ---------------------------------------------------------
# 5. YOY PIVOT
# ---------------------------------------------------------
def get_board_pivot(board_df):
    pivot = board_df.pivot_table(
        index="Year",
        columns="Board Category",
        values="Amount",
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    for col in ["Total Income", "Total Expenses", "Net Income"]:
        if col not in pivot.columns:
            pivot[col] = 0

    return pivot
