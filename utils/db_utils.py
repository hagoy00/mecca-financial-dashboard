import pandas as pd

def load_data():
    """
    Loads the MECCA Excel file as a DataFrame.
    """
    file_path = "MECCA_Financial_Data.xlsx"
    df = pd.read_excel(file_path)
    return df
