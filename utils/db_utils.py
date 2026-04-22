import pandas as pd

EXCEL_PATH = "MECCA_Financial_Data.xlsx"

def init_db():
    """
    Placeholder function for compatibility.
    Historically used for database initialization.
    Now returns True to indicate Excel-based pipeline is active.
    """
    return True


def load_excel():
    """
    Loads the full Excel file and returns a dictionary of sheets.
    Each sheet is returned as a DataFrame.
    """
    try:
        xls = pd.ExcelFile(EXCEL_PATH)
        sheets = {}

        for sheet in xls.sheet_names:
            try:
                df = pd.read_excel(EXCEL_PATH, sheet_name=sheet)
                sheets[sheet] = df
            except Exception:
                continue

        return sheets

    except Exception as e:
        print("Error loading Excel:", e)
        return {}


def load_sheet(sheet_name: str) -> pd.DataFrame:
    """
    Loads a single sheet by name.
    """
    try:
        return pd.read_excel(EXCEL_PATH, sheet_name=sheet_name)
    except Exception:
        return pd.DataFrame()
