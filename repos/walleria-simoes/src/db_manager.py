import sqlite3
import pandas as pd
from datetime import datetime
import os
import json

DB_PATH = "data/equity_research.db"

def get_connection():
    os.makedirs("data", exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS valid_tickers (ticker TEXT PRIMARY KEY, last_updated DATE)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS companies (ticker TEXT PRIMARY KEY, name TEXT, sector TEXT, segment TEXT, business_model TEXT)''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT, collection_date DATE, current_price REAL, pe_ratio REAL, roe REAL, debt_ebitda TEXT, net_margin REAL, div_yield REAL,
            FOREIGN KEY (ticker) REFERENCES companies(ticker)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS saved_dashboards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT,
            generated_at DATETIME,
            dashboard_data TEXT,
            FOREIGN KEY (ticker) REFERENCES companies(ticker)
        )
    ''')

    conn.commit()
    conn.close()

def get_cached_tickers():
    conn = get_connection()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor = conn.cursor()
    cursor.execute("SELECT ticker FROM valid_tickers WHERE last_updated = ?", (today,))
    rows = cursor.fetchall()
    conn.close()
    return {row[0] for row in rows} if rows else None

def save_cached_tickers(tickers):
    conn = get_connection()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM valid_tickers")
    cursor.executemany("INSERT INTO valid_tickers (ticker, last_updated) VALUES (?, ?)", [(t, today) for t in tickers])
    conn.commit()
    conn.close()

def get_company_static_data(ticker):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, sector, segment, business_model FROM companies WHERE ticker = ?", (ticker,))
    row = cursor.fetchone()
    conn.close()
    if row: return {"Name": row[0], "Sector": row[1], "Segment": row[2], "Business Model": row[3]}
    return None

def save_company_static_data(ticker, name, sector, segment, business_model):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''INSERT OR REPLACE INTO companies (ticker, name, sector, segment, business_model) VALUES (?, ?, ?, ?, ?)''', (ticker, name, sector, segment, business_model))
    conn.commit()
    conn.close()

def save_market_data(ticker, data_dict):
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute('''
        INSERT INTO market_data (ticker, collection_date, current_price, pe_ratio, roe, debt_ebitda, net_margin, div_yield)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (ticker, today, data_dict.get('Current Price'), data_dict.get('P/L'), data_dict.get('ROE (%)'), str(data_dict.get('Net Debt/EBITDA')), data_dict.get('Net Profit Margin (%)'), data_dict.get('Dividend Yield (%)')))
    conn.commit()
    conn.close()

def save_dashboard_snapshot(ticker, full_data_dict):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    json_data = json.dumps(full_data_dict, ensure_ascii=False)
    cursor.execute("INSERT INTO saved_dashboards (ticker, generated_at, dashboard_data) VALUES (?, ?, ?)", (ticker, now, json_data))
    conn.commit()
    conn.close()

def get_past_dashboards(ticker):
    conn = get_connection()
    df = pd.read_sql_query("SELECT generated_at, dashboard_data FROM saved_dashboards WHERE ticker = ? ORDER BY generated_at DESC", conn, params=(ticker,))
    conn.close()
    return df