"""
Dashboard — Centralizador de Análise
Visualização de dados macro, múltiplos de mercado e demonstrações financeiras.
Chat com LLM ancorado nos dados gold + transcrição do earnings call.
"""

import os
import sys
import psycopg2
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Adiciona synthesis ao path
sys.path.insert(0, "/app/synthesis")

# ── Cores ────────────────────────────────────────────────────────────────────
COLORS = {
    "primary":    "#dc9a56",
    "dark":       "#123b62",
    "mid":        "#1b4569",
    "light":      "#6a96bb",
    "white":      "#ffffff",
    "green":      "#2ca02c",
    "red":        "#d62728",
}

PLOTLY_THEME = dict(
    plot_bgcolor  = "#123b62",
    paper_bgcolor = "#123b62",
    font_color    = "#ffffff",
    xaxis         = dict(gridcolor="#1b4569", linecolor="#1b4569"),
    yaxis         = dict(gridcolor="#1b4569", linecolor="#1b4569"),
)

# ── Configuração da página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Centralizador de Análise",
    page_icon="📊",
    layout="wide",
)

# ── Conexão com PostgreSQL ────────────────────────────────────────────────────
PG_CONN = dict(
    host=os.getenv("PG_HOST", "postgres"),
    port=int(os.getenv("PG_PORT", "5432")),
    dbname=os.getenv("PG_DB", "hipotetical_fia"),
    user=os.getenv("PG_USER", "airflow"),
    password=os.getenv("PG_PASSWORD", "airflow"),
)

TICKERS = ["PRIO3", "RENT3"]

# Key DRE accounts
DRE_ACCOUNTS = {
    "3.01": "Net Revenue",
    "3.05": "Gross Profit",
    "3.07": "Operating Income",
    "3.11": "Net Income",
}


@st.cache_data(ttl=300)
def query(sql: str, params=None) -> pd.DataFrame:
    conn = psycopg2.connect(**PG_CONN)
    try:
        return pd.read_sql(sql, conn, params=params)
    finally:
        conn.close()


# ── Custom CSS — Avenir font + theme ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@300;400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Avenir Next', 'Avenir', 'Nunito', sans-serif !important;
}

#MainMenu, footer, header {visibility: hidden;}

.block-container {
    padding-top: 0rem !important;
}

h1, h2, h3, h4 {
    font-family: 'Avenir Next', 'Avenir', 'Nunito', sans-serif !important;
    font-weight: 600;
    color: #ffffff;
}

.stMetric label {
    color: #6a96bb !important;
    font-size: 0.85rem;
}

.stMetric [data-testid="stMetricValue"] {
    color: #dc9a56 !important;
    font-size: 1.4rem;
    font-weight: 600;
}

[data-testid="stSidebar"] {
    background-color: #1b4569;
}

.stTabs [data-baseweb="tab-list"] {
    background-color: transparent;
    border-radius: 0;
    padding: 0;
    gap: 12px;
    border-bottom: none;
}

.stTabs [data-baseweb="tab"] {
    background-color: #ffffff;
    color: #123b62;
    font-weight: 700;
    font-size: 1.05rem;
    letter-spacing: 1.5px;
    border-radius: 6px;
    border: 2px solid #d0dce8;
    padding: 14px 40px;
    min-width: 150px;
    text-align: center;
}

.stTabs [data-baseweb="tab"]:hover {
    background-color: #dce8f0;
    border-color: #123b62;
}

.stTabs [aria-selected="true"] {
    background-color: #123b62 !important;
    color: #ffffff !important;
    border: 2px solid #123b62 !important;
}

.stTabs [data-baseweb="tab-highlight"] {
    display: none;
}

.stTabs [data-baseweb="tab-border"] {
    display: none;
}
</style>
""", unsafe_allow_html=True)

# ── Header institucional ──────────────────────────────────────────────────────
st.markdown("""
<div style="
    background-color: #123b62;
    padding: 1.2rem 2rem;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    border-bottom: 3px solid #dc9a56;
">
    <div>
        <span style="
            font-size: 1.8rem;
            font-weight: 700;
            color: #dc9a56;
            font-family: 'Avenir Next', 'Avenir', 'Nunito', sans-serif;
            letter-spacing: 2px;
        ">HF</span>
    </div>
    <div>
        <div style="
            color: #ffffff;
            font-size: 1rem;
            font-weight: 600;
            letter-spacing: 1px;
            font-family: 'Avenir Next', 'Avenir', 'Nunito', sans-serif;
        ">HYPOTHETICAL FIA</div>
        <div style="
            color: #6a96bb;
            font-size: 0.75rem;
            letter-spacing: 1px;
            font-family: 'Avenir Next', 'Avenir', 'Nunito', sans-serif;
        ">INVESTMENT ANALYSIS PLATFORM</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📊 Análise")
    ticker = st.selectbox("Empresa", TICKERS)
    st.caption(f"Pipeline: bronze → staging → gold")
    st.divider()
    st.caption("Dados: BCB · CVM · Yahoo Finance")
    st.caption("Orquestração: Apache Airflow")
    st.caption("Transformação: dbt-core")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_macro, tab_company, tab_financials, tab_chat = st.tabs([
    "MACRO", "EMPRESA", "FINANCEIRO", "CHAT"
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — MACRO
# ═══════════════════════════════════════════════════════════════════════════════
with tab_macro:
    st.header("Macro Indicators — Brazil")

    macro = query("""
        SELECT ref_date, selic_rate, ipca_monthly, usd_brl_rate, unemployment_rate, trade_balance
        FROM gold.gold_macro
        WHERE ref_date >= NOW() - INTERVAL '24 months'
        ORDER BY ref_date ASC
    """)

    if macro.empty:
        st.warning("No macro data available. Run the monday_briefing DAG first.")
    else:
        col1, col2 = st.columns(2)

        with col1:
            # Selic
            selic = macro.dropna(subset=["selic_rate"])
            fig = px.line(selic, x="ref_date", y="selic_rate",
                          title="Selic Rate (% p.a.)", markers=True,
                          color_discrete_sequence=[COLORS["primary"]])
            fig.update_layout(height=300, margin=dict(t=40, b=20), **PLOTLY_THEME)
            st.plotly_chart(fig, use_container_width=True)

            # USD/BRL
            fx = macro.dropna(subset=["usd_brl_rate"])
            fig2 = px.line(fx, x="ref_date", y="usd_brl_rate",
                           title="USD/BRL Exchange Rate", markers=False,
                           color_discrete_sequence=[COLORS["light"]])
            fig2.update_layout(height=300, margin=dict(t=40, b=20))
            st.plotly_chart(fig2, use_container_width=True)

        with col2:
            # IPCA
            ipca = macro.dropna(subset=["ipca_monthly"])
            fig3 = px.bar(ipca, x="ref_date", y="ipca_monthly",
                          title="IPCA Monthly (% MoM)",
                          color_discrete_sequence=[COLORS["green"]])
            fig3.update_layout(height=300, margin=dict(t=40, b=20))
            st.plotly_chart(fig3, use_container_width=True)

            # Desemprego
            unemp = macro.dropna(subset=["unemployment_rate"])
            fig4 = px.line(unemp, x="ref_date", y="unemployment_rate",
                           title="Unemployment Rate (%)", markers=True,
                           color_discrete_sequence=[COLORS["red"]])
            fig4.update_layout(height=300, margin=dict(t=40, b=20))
            st.plotly_chart(fig4, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — EMPRESA
# ═══════════════════════════════════════════════════════════════════════════════
with tab_company:
    st.header(f"Market Overview — {ticker}")

    market = query("""
        SELECT * FROM gold.gold_market WHERE ticker = %s
    """, (ticker,))

    if market.empty:
        st.warning("No market data available.")
    else:
        row = market.iloc[0]

        # Cards de múltiplos
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Price (BRL)", f"R$ {row['current_price']:.2f}" if row['current_price'] else "N/A")
        c2.metric("P/E Ratio", f"{row['pe_ratio']:.1f}x" if row['pe_ratio'] else "N/A")
        c3.metric("EV/EBITDA", f"{row['ev_ebitda']:.1f}x" if row['ev_ebitda'] else "N/A")
        c4.metric("P/B Ratio", f"{row['pb_ratio']:.2f}x" if row['pb_ratio'] else "N/A")
        c5.metric("Dividend Yield", f"{row['dividend_yield']*100:.1f}%" if row['dividend_yield'] else "N/A")

        st.divider()

        c6, c7, c8, c9 = st.columns(4)
        c6.metric("ROE", f"{row['roe']*100:.1f}%" if row['roe'] else "N/A")
        c7.metric("Net Margin", f"{row['net_margin']*100:.1f}%" if row['net_margin'] else "N/A")
        c8.metric("EBITDA Margin", f"{row['ebitda_margin']*100:.1f}%" if row['ebitda_margin'] else "N/A")
        c9.metric("Debt/Equity", f"{row['debt_to_equity']:.1f}x" if row['debt_to_equity'] else "N/A")

        st.divider()
        c10, c11 = st.columns(2)
        mktcap = row['market_cap']
        revenue = row['total_revenue']
        net_inc = row['net_income']
        c10.metric("Market Cap", f"R$ {mktcap/1e9:.1f}B" if mktcap else "N/A")
        c11.metric("Net Income (LTM)", f"R$ {net_inc/1e9:.2f}B" if net_inc else "N/A")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — FINANCEIRO
# ═══════════════════════════════════════════════════════════════════════════════
with tab_financials:
    st.header(f"Financial Statements — {ticker}")

    dre = query(f"""
        SELECT ref_date, account_code, account_name, account_value, currency_scale
        FROM gold.gold_{ticker.lower()}_dre
        WHERE account_code IN ('3.01', '3.05', '3.07', '3.11')
        ORDER BY ref_date ASC
    """)

    if dre.empty:
        st.warning("No financial data available for this ticker.")
    else:
        # Multiplica por 1000 se MILHAR
        dre["value_brl"] = dre.apply(
            lambda r: r["account_value"] * 1000 if r["currency_scale"] == "MIL" else r["account_value"],
            axis=1
        )
        dre["account_label"] = dre["account_code"].map(DRE_ACCOUNTS)

        col1, col2 = st.columns(2)

        with col1:
            revenue = dre[dre["account_code"] == "3.01"]
            if not revenue.empty:
                fig = px.bar(revenue, x="ref_date", y="value_brl",
                             title="Net Revenue (BRL)",
                             color_discrete_sequence=[COLORS["primary"]])
                fig.update_layout(height=350, yaxis_tickformat=".2s", **PLOTLY_THEME)
                st.plotly_chart(fig, use_container_width=True)

            op_income = dre[dre["account_code"] == "3.07"]
            if not op_income.empty:
                fig3 = px.bar(op_income, x="ref_date", y="value_brl",
                              title="Operating Income (BRL)",
                              color_discrete_sequence=[COLORS["light"]])
                fig3.update_layout(height=350, yaxis_tickformat=".2s")
                st.plotly_chart(fig3, use_container_width=True)

        with col2:
            net_inc = dre[dre["account_code"] == "3.11"]
            if not net_inc.empty:
                colors = ["#d62728" if v < 0 else "#2ca02c" for v in net_inc["value_brl"]]
                fig2 = go.Figure(go.Bar(
                    x=net_inc["ref_date"], y=net_inc["value_brl"],
                    marker_color=colors, name="Net Income"
                ))
                fig2.update_layout(title="Net Income (BRL)", height=350,
                                   yaxis_tickformat=".2s", **PLOTLY_THEME)
                st.plotly_chart(fig2, use_container_width=True)

            gross = dre[dre["account_code"] == "3.05"]
            if not gross.empty:
                fig4 = px.bar(gross, x="ref_date", y="value_brl",
                              title="Gross Profit (BRL)",
                              color_discrete_sequence=[COLORS["primary"]])
                fig4.update_layout(height=350, yaxis_tickformat=".2s")
                st.plotly_chart(fig4, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — CHAT
# ═══════════════════════════════════════════════════════════════════════════════
with tab_chat:
    st.header(f"💬 Analyst Helper — {ticker}")
    st.caption("Ask questions about the company. Context: macro data, market multiples, financial statements and earnings call transcript.")

    # Inicializa histórico
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "context" not in st.session_state:
        st.session_state.context = {}

    # Carrega contexto se mudou o ticker
    if st.session_state.context.get("ticker") != ticker:
        with st.spinner("Loading context from database..."):
            try:
                from rag import build_context
                ctx = build_context(ticker)
                st.session_state.context = {"ticker": ticker, "data": ctx}
                st.session_state.messages = []
            except Exception as e:
                st.error(f"Error loading context: {e}")
                st.session_state.context = {"ticker": ticker, "data": ""}

    # Exibe histórico
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Input do usuário
    if prompt := st.chat_input(f"Ask about {ticker}..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    from llm_report import chat
                    response = chat(
                        messages=st.session_state.messages,
                        context=st.session_state.context.get("data", ""),
                    )
                    st.write(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    err = f"LLM error: {e}. Make sure LLM_API_KEY and LLM_PROVIDER are set."
                    st.error(err)
