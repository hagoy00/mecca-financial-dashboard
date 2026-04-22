import pandas as pd

DATA_FILE = "MECCA_Financial_Data.xlsx"

def load_church_excel():
    """
    Loads the ORIGINAL church Excel format:

    Sheet name = Year (2021, 2022, ...)
    Columns:
        Category | <YearValue>

    Returns a unified DataFrame:
        Year | Category | Amount | Type (Income/Expense/Subtotal)
    """

    xls = pd.ExcelFile(DATA_FILE)
    all_years = []

    for sheet in xls.sheet_names:
        # Sheet name must be a year
        try:
            year = int(sheet)
        except:
            continue

        df = pd.read_excel(DATA_FILE, sheet_name=sheet)

        if "Category" not in df.columns:
            continue

        # The second column is the year value
        value_col = [c for c in df.columns if c != "Category"][0]

        df_long = pd.DataFrame({
            "Year": year,
            "Category": df["Category"].astype(str),
            "Amount": df[value_col]
        })

        # Classification logic
        def classify(cat):
            cat_lower = str(cat).lower()

            # Subtotals: "Total Something"
            if cat_lower.startswith("total "):
                return "Subtotal"

            # Expense keywords
            expense_keywords = [
                "rent", "mortgage", "loan", "insurance", "repair",
                "maintenance", "utility", "utilities", "fuel",
                "cleaning", "janitorial", "supplies", "office",
                "payroll", "salary", "salaries", "wages",
                "service", "contract", "professional", "tax",
                "internet", "phone", "security", "equipment",
                "printing", "postage", "transport", "travel"
            ]

            if any(word in cat_lower for word in expense_keywords):
                return "Expense"

            # Everything else is Income
            return "Income"

        df_long["Type"] = df_long["Category"].apply(classify)

        all_years.append(df_long)

    if not all_years:
        return pd.DataFrame()

    return pd.concat(all_years, ignore_index=True)
