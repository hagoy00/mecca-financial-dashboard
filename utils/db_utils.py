from sqlalchemy import create_engine
import pandas as pd
from utils.data_utils import load_excel

def get_engine():
    return create_engine("sqlite:///mecca_finance.db")

def init_db():
    df = load_excel()
    engine = get_engine()
    df.to_sql("transactions", engine, if_exists="replace", index=False)

def load_data():
    engine = get_engine()
    return pd.read_sql("SELECT * FROM transactions", engine)

