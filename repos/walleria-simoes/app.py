from src.web_scraping import *
from src.llm_report import *
from src.db_manager import *

import logging
import streamlit as st
import pandas as pd
import json
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

init_db()
load_dotenv()

st.set_page_config(
    page_title="Report Maker",
    page_icon="img\\logo_charles_river.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data(ttl=3600) 
def load_valid_tickers():
    return get_available_tickers()

valid_tickers = load_valid_tickers()

# Sidebar
st.sidebar.title("Report Maker")
st.sidebar.markdown("Enter the code of a B3 asset to generate an automated report.")

ticker_input = st.sidebar.text_input("Ticker (ex: WEGE3, PETR4):", max_chars=6, key="new_ticker").strip().upper()
gerar_btn = st.sidebar.button("Generate Report", type="primary")

st.sidebar.divider()

st.sidebar.markdown("# Record")
ticker_historico = st.sidebar.text_input("View ticker history:", max_chars=6, key="hist_ticker").strip().upper()

if ticker_historico:
    df_historico = get_past_dashboards(ticker_historico)
    if not df_historico.empty:
        st.sidebar.success(f"{len(df_historico)} dashboard found")
        
        selected_date = st.sidebar.selectbox(
            "Select a version:",
            options=df_historico['generated_at'].tolist(),
            index=0,
            key="version_selector"
        )
        
        if st.sidebar.button("Load Dashboard Snapshot"):
            row = df_historico[df_historico['generated_at'] == selected_date].iloc[0]
            saved_dict = json.loads(row['dashboard_data'])
            
            st.session_state['displayed_report'] = {
                "ticker": ticker_historico,
                "date": selected_date,
                "market_data": saved_dict,
                "is_history": True
            }
    else:
        st.sidebar.warning("No reports found for this ticker.")

st.sidebar.divider()
st.sidebar.caption("Developed with Fundamentus, YFinance, and Google Gemini.")


if gerar_btn:
    if not ticker_input:
        st.warning("Please enter a ticker symbol before generating the report.")
    else:
        with st.status(f"Analyzing {ticker_input}...", expanded=True) as status:
            st.write("Please wait while the report is being generated.")
            market_data = collect_data(ticker_input, valid_tickers)
            
            if market_data.get("Name") in ["INVALID TICKER", "N/A", "TICKER INVÁLIDO"]:
                status.update(label="Search error", state="error", expanded=False)
                st.error(f"Ticker **{ticker_input}** not found.")
                st.stop()
            
            registration_data = collect_business_model(ticker_input, valid_tickers)
            news_data = collect_news(ticker_input, valid_tickers)
            
            market_data.update(registration_data)
            market_data.update(news_data)
            
            save_company_static_data(ticker_input, market_data.get("Name"), market_data.get("Sector"), market_data.get("Segment"), market_data.get("Business Model"))
            save_market_data(ticker_input, market_data)
        
            ai_report = generate_report(market_data)
            market_data["AI Report"] = ai_report
            
            save_dashboard_snapshot(ticker_input, market_data)
            
            st.session_state['displayed_report'] = {
                "ticker": ticker_input,
                "market_data": market_data,
                "is_history": False
            }
            status.update(label="Analysis successfully completed!", state="complete", expanded=False)

# Main screen
if 'displayed_report' in st.session_state:
    res = st.session_state['displayed_report']
    m_data = res['market_data']
    
    # If it's an old report, it displays a context alert
    if res['is_history']:
        st.warning(f"**Historical Snapshot:** You are viewing the dashboard exactly as it was generated on **{res['date']}**.")
    
    # Single Rendering (works for both new and historical files)
    st.title(f"{m_data.get('Name')} ({res['ticker']})")
    st.subheader(f"Sector: {m_data.get('Sector')} | Segment: {m_data.get('Segment')}")
    
    st.markdown("### Basic Indicators")
    is_bank = m_data.get("Net Debt/EBITDA") == "N/A (Banco)"
    
    if is_bank:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Current Price", f"R$ {m_data.get('Current Price')}")
        col2.metric("P/L", m_data.get('P/L'))
        col3.metric("ROE", f"{m_data.get('ROE (%)')}%" if m_data.get('ROE (%)') != "N/D" else "N/D")
        col4.metric("Div. Yield (%)", f"{m_data.get('Dividend Yield (%)')}%")
    else:
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        col1.metric("Current Price", f"R$ {m_data.get('Current Price')}")
        col2.metric("P/L", m_data.get('P/L'))
        col3.metric("ROE", f"{m_data.get('ROE (%)')}%" if m_data.get('ROE (%)') != "N/D" else "N/D")
        col4.metric("Net Debt/EBITDA", m_data.get('Net Debt/EBITDA'))
        col5.metric("Net Profit Margin (%)", f"{m_data.get('Net Profit Margin (%)')}%" if m_data.get('Net Profit Margin (%)') not in ["N/D", "N/A (Banco)"] else m_data.get('Net Profit Margin (%)'))
        col6.metric("Div. Yield (%)", f"{m_data.get('Dividend Yield (%)')}%")
    
    st.divider()
    col_main, col_side = st.columns([2, 1])
    
    with col_main:
        st.markdown("### AI Analysis")
        st.markdown(m_data.get("AI Report"))
        
    with col_side:
            st.markdown("### Business Model")
            
            # Reads the data source (if it doesn't exist, assumes it came from the API).
            bm_source = m_data.get("BM_Source", "YFinance")
            
            # It triggers an alert if the API crashes and the system needs to use the cache.
            if bm_source == "Database Fallback":
                st.warning("**API Unavailable:** Displaying cached business model from the local database.")
                
            with st.expander("Read full summary", expanded=True):
                # If both attempts fail, the error message is displayed in red.
                if bm_source == "Failed":
                    st.error(m_data.get("Business Model"))
                else:
                    st.write(m_data.get("Business Model"))
            
            st.markdown("### Recent News")
            noticias = m_data.get("Recent News", "")
            if noticias and "http" in noticias:
                for news in noticias.split('\n'):
                    if news.strip():
                        idx = news.find('https')
                        if idx != -1:
                            st.markdown(f"[{news[:idx].strip(' -')}]({news[idx:]})")
                        else:
                            st.markdown(news)
            else:
                st.write(noticias)