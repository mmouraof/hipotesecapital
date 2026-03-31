from src.web_scraping import *
from src.llm_report import *

import os
import pandas as pd
from dotenv import load_dotenv


load_dotenv()
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')

if not GEMINI_KEY:
    print("Warning: GEMINI_API_KEY is not set in the .env file. AI reporting will fail.")

if __name__ == "__main__":
    # Test with all tickers
    tickers = ['ASAI3', 'RECV3', 'MOVI3', 'BRKM5', 'HBSA3', 'ITUB4', 'BBDC4', 'OPCT3', 'BRSR6', 'PRIO3']
    valid_tickers = get_available_tickers()
    
    results = []
    
    for ticker in tickers:
        market_data = collect_data(ticker, valid_tickers)
        
        if market_data.get("Name") == "INVALID TICKER":
            print(f"{ticker} is invalid.")
            market_data["AI Report"] = "N/A"
            results.append(market_data)
            continue

        registration_data = collect_business_model(ticker, valid_tickers)
        news_data = collect_news(ticker, valid_tickers)
        
        # Consolidate everything in the base dictionary
        market_data.update(registration_data)
        market_data.update(news_data)

        ai_report = generate_report(market_data)
        market_data["AI Report"] = ai_report
        
        results.append(market_data)
        
    df = pd.DataFrame(results)
    
    # Updating the sorted columns to include the AI ​​response
    ordered_columns = [
        "Ticker", "Name", "Sector", "Segment", "Business Model", 
        "Current Price", "P/L", "ROE (%)", "Net Debt/EBITDA", 
        "Net Profit Margin (%)", "Dividend Yield (%)", "Recent News",
        "AI Report"
    ]
    
    # Filter the DataFrame to ensure the correct order
    df = df[ordered_columns]
    df.to_excel("data/collected_data.xlsx", index=False)