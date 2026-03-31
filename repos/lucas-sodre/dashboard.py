import streamlit as st
import pandas as pd
import plotly.express as px
from data.yahoo_raw import get_info_ticker, get_price_history
from data.news_sources import get_news_with_fallback
import os
from data.pipeline_db import DEFAULT_DB_PATH, get_fundamentals_history, get_latest_llm_report, get_tickers_from_db
from llm.report_generator import summarize_price_data, generate_structured_report_with_llm
from utils.formatters import format_currency, format_number, format_percent, format_text
from utils.news_parser import extract_news_item


def get_gemini_api_key():
    # Prioriza variável de ambiente e usa secrets como fallback.
    env_key = os.getenv("GOOGLE_API_KEY")
    if env_key:
        return env_key

    try:
        return st.secrets["GOOGLE_API_KEY"]
    except Exception:
        return None


@st.cache_data(ttl=1800)
def load_info(ticker):
    return get_info_ticker(ticker)


@st.cache_data(ttl=1800)
def load_news(ticker):
    return get_news_with_fallback(ticker=ticker, min_results=5, max_results=15)


@st.cache_data(ttl=1800)
def load_price_history(ticker, period):
    return get_price_history(ticker, period)


@st.cache_data(ttl=600)
def load_db_tickers():
    return get_tickers_from_db(db_path=DEFAULT_DB_PATH)


@st.cache_data(ttl=600)
def load_fundamentals_history(ticker):
    return get_fundamentals_history(ticker=ticker, limit=120, db_path=DEFAULT_DB_PATH)


@st.cache_data(ttl=600)
def load_latest_report_from_db(ticker):
    return get_latest_llm_report(ticker=ticker, db_path=DEFAULT_DB_PATH)

st.set_page_config(
    page_title="Dashboard Hipótese Capital",
    layout="wide"
)

# Junta tickers padrão com tickers já persistidos no banco.
default_tickers = ["ASAI3", "RECV3", "MOVI3", "BRKM5", "HBSA3", "ITUB4", "BBDC4", "OPCT3", "BRSR6", "PRIO3"]
db_tickers = load_db_tickers() or []
tickers = sorted({*default_tickers, *db_tickers})
period_map = {
    "1M": "1mo",
    "3M": "3mo",
    "6M": "6mo",
    "1A": "1y",
    "5A": "5y"
}

with st.sidebar:
    # Filtros principais de navegação do dashboard.
    st.header("Filtros")
    ticker = st.selectbox("Ticker", tickers)
    period_label = st.radio(
        "Período",
        list(period_map.keys()),
        index=2,
        horizontal=True
    )

info_dict = load_info(ticker) or {}
news = load_news(ticker) or []
data = load_price_history(ticker, period_map[period_label])

st.title(f"Dashboard Hipótese Capital")
st.title(f"{ticker}")
st.caption("Dados de mercado e informações fundamentais")
st.divider()

if not info_dict:
    st.warning("Não foi possível carregar informações para este ticker.")
else:
    st.subheader("Resumo da Empresa")
    name_col, sector_col, industry_col = st.columns(3)
    with name_col:
        st.markdown(f"**Nome**: {format_text(info_dict.get('Nome'))}")
    with sector_col:
        st.markdown(f"**Setor**: {format_text(info_dict.get('Setor'))}")
    with industry_col:
        st.markdown(f"**Indústria**: {format_text(info_dict.get('Indústria'))}")

    with st.expander("Descrição", expanded=False):
        st.write(format_text(info_dict.get("Descrição"), "Descrição indisponível."))

    st.subheader("Indicadores")
    metric_col_1, metric_col_2, metric_col_3, metric_col_4 = st.columns(4)
    with metric_col_1:
        st.metric("P/L", format_number(info_dict.get("P/L")))
    with metric_col_2:
        st.metric("ROE", format_percent(info_dict.get("ROE")))
    with metric_col_3:
        st.metric("DY", format_percent(info_dict.get("DY")))
    with metric_col_4:
        st.metric("Margem Líquida", format_percent(info_dict.get("Margem Líquida")))

    detail_col_1, detail_col_2 = st.columns(2)
    with detail_col_1:
        st.metric("Dívida/Equity", format_number(info_dict.get("Dívida/Equity")))
    with detail_col_2:
        current_currency = format_text(info_dict.get("Moeda"), "BRL")
        st.metric("Preço Atual", format_currency(info_dict.get("Preço Atual"), current_currency))

st.divider()
st.subheader(f"Histórico de Preço - {period_label}")

if data is not None and not data.empty and {"Date", "Close"}.issubset(data.columns):
    # Higieniza e ordena os dados antes do gráfico.
    chart_data = data.copy()
    chart_data["Date"] = pd.to_datetime(chart_data["Date"], errors="coerce")
    chart_data = chart_data.dropna(subset=["Date", "Close"])
    chart_data = chart_data.sort_values("Date")

    if chart_data.empty:
        st.info("Não há dados válidos para exibir no gráfico deste período.")
    else:
        # Ajusta os limites dos eixos ao intervalo real dos dados.
        x_min = chart_data["Date"].min()
        x_max = chart_data["Date"].max()
        y_min = float(chart_data["Close"].min())
        y_max = float(chart_data["Close"].max())
        y_padding = (y_max - y_min) * 0.05 if y_max > y_min else 1.0

        price_fig = px.line(chart_data, x="Date", y="Close")
        price_fig.update_traces(line={"width": 2})
        price_fig.update_xaxes(range=[x_min, x_max], title_text="Data")
        price_fig.update_yaxes(range=[y_min - y_padding, y_max + y_padding], title_text="Preço")
        price_fig.update_layout(margin={"l": 20, "r": 20, "t": 20, "b": 20})
        st.plotly_chart(price_fig, width="stretch")
        st.caption(
            f"Último fechamento: {format_currency(chart_data['Close'].iloc[-1], format_text(info_dict.get('Moeda'), 'BRL'))}"
        )
        st.caption("Fonte: Yahoo Finance. Pode haver divergências pontuais em relação a outras fontes devido a ajustes de mercado ou dados faltantes.")
else:
    st.info("Histórico de preços indisponível para o período selecionado.")

st.divider()
st.subheader("Histórico de Indicadores (Pipeline)")

history_df = load_fundamentals_history(ticker)
if not history_df.empty:
    # Mapeia os nomes exibidos no UI para as colunas persistidas no banco.
    metric_map = {
        "P/L": "pl",
        "ROE": "roe",
        "DY": "dy",
        "Dívida/Equity": "divida_equity",
        "Margem Líquida": "margem_liquida",
        "Preço Atual": "preco_atual",
    }

    selected_metric = st.selectbox("Indicador histórico", list(metric_map.keys()))
    metric_col = metric_map[selected_metric]

    chart_history = history_df[["captured_at", metric_col]].dropna().copy()
    if not chart_history.empty:
        # Mesmo critério de autoajuste para o gráfico histórico.
        chart_history = chart_history.sort_values("captured_at")
        x_min = chart_history["captured_at"].min()
        x_max = chart_history["captured_at"].max()
        y_min = float(chart_history[metric_col].min())
        y_max = float(chart_history[metric_col].max())
        y_padding = (y_max - y_min) * 0.05 if y_max > y_min else 1.0

        history_fig = px.line(chart_history, x="captured_at", y=metric_col)
        history_fig.update_traces(line={"width": 2})
        history_fig.update_xaxes(range=[x_min, x_max], title_text="Data de captura")
        history_fig.update_yaxes(range=[y_min - y_padding, y_max + y_padding], title_text=selected_metric)
        history_fig.update_layout(margin={"l": 20, "r": 20, "t": 20, "b": 20})
        st.plotly_chart(history_fig, width="stretch")
    else:
        st.info("Sem valores suficientes para plotar este indicador no histórico.")

    with st.expander("Ver snapshots salvos"):
        st.dataframe(
            history_df[
                [
                    "captured_at",
                    "pl",
                    "roe",
                    "dy",
                    "divida_equity",
                    "margem_liquida",
                    "preco_atual",
                    "moeda",
                ]
            ].sort_values("captured_at", ascending=False),
            width="stretch",
            hide_index=True,
        )
else:
    st.info("Ainda não há histórico em banco para este ticker. Execute o pipeline para começar a registrar snapshots.")

st.divider()
st.subheader("Notícias Recentes")

# Normaliza a estrutura das notícias vindas das múltiplas fontes.
parsed_news_items = [extract_news_item(item) for item in news] if news else []

if parsed_news_items:
    for parsed_news in parsed_news_items[:5]:
        title = parsed_news["title"]
        publisher = parsed_news["publisher"]
        published_at = parsed_news["published_at"]
        link = parsed_news["link"]

        st.markdown(f"**{title}**")
        st.caption(f"{publisher} - {published_at}")
        if link:
            st.markdown(f"[Leia mais]({link})")
        st.markdown("")
else:
    st.info("Nenhuma notícia recente disponível para este ticker.")

st.divider()
st.subheader("Relatório Estruturado (LLM)")

if st.button("Gerar relatório com IA", type="primary"):
    # Gera relatório sob demanda para evitar custo em toda renderização.
    with st.spinner("Gerando relatório estruturado com base nos dados coletados..."):
        price_summary = summarize_price_data(data)
        api_key = get_gemini_api_key()

        report_text, report_error = generate_structured_report_with_llm(
            ticker=ticker,
            info_dict=info_dict,
            period_label=period_label,
            price_summary=price_summary,
            parsed_news=parsed_news_items,
            api_key=api_key,
        )

    if report_error:
        st.error(report_error)
    else:
        st.markdown(report_text)

latest_saved_report = load_latest_report_from_db(ticker)
if latest_saved_report:
    with st.expander("Último relatório salvo no banco", expanded=False):
        st.caption(
            f"{latest_saved_report.get('provider')} | {latest_saved_report.get('model')} | {latest_saved_report.get('captured_at')}"
        )
        st.markdown(latest_saved_report.get("report_markdown", ""))

