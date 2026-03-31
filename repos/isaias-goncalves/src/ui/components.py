import streamlit as st
import pandas as pd
from config import CHART_COLOR_PRIMARY, INDICATOR_TOOLTIPS


def render_header(ticker_symbol: str, nome_empresa: str):
    """Exibe o cabeçalho de identificação da empresa."""
    st.title(f"{nome_empresa} :grey[({ticker_symbol})]")

def render_summary_cards(data: dict):
    """Renderiza os indicadores fundamentalistas atuais em cards com tooltips."""
    st.header("Indicadores da Captura")
    indicators = data.get("market_indicators", {})
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    def fmt_pct(val): return f"{val*100:.2f}%" if val else "N/A"
    def fmt_curr(val): return f"R$ {val:.2f}" if val else "N/A"
    def fmt_num(val): return f"{val:.2f}" if val else "N/A"

    with col1: 
        st.metric("Preço na Data", fmt_curr(indicators.get('preco_atual')), help=INDICATOR_TOOLTIPS["price"])
    with col2: 
        st.metric("P/L", fmt_num(indicators.get('p_l')), help=INDICATOR_TOOLTIPS["p_l"])
    with col3: 
        st.metric("ROE", fmt_pct(indicators.get('roe')), help=INDICATOR_TOOLTIPS["roe"])
    with col4: 
        st.metric("Margem Líquida", fmt_pct(indicators.get('margem_liquida')), help=INDICATOR_TOOLTIPS["net_margin"])
    with col5: 
        st.metric("Div. Yield", fmt_pct(indicators.get('dy')), help=INDICATOR_TOOLTIPS["dy"])

def render_price_chart(collector):
    """Gera o gráfico de performance de mercado (Dados Vivos do Yahoo)."""
    st.subheader("Performance de Mercado (Últimos 12m - Live)")
    try:
        history = collector.get_history(period="1y")
        if not history.empty:
            st.line_chart(history['Close'], color=CHART_COLOR_PRIMARY)
        else:
            st.warning("Dados do Yahoo Finance indisponíveis no momento.")
    except Exception:
        st.error("Erro ao carregar gráfico de performance externa.")

def render_historical_trends(history_df: pd.DataFrame):
    """
    Renderiza tendências históricas do banco de dados com escalas separadas.
    """
    if history_df.empty or len(history_df) < 2:
        return

    st.header("Evolução no Terminal (Banco Local)")
    
    df = history_df.copy()
    df['collected_at'] = pd.to_datetime(df['collected_at'])
    df = df.set_index('collected_at')

    tab_price, tab_valuation, tab_efficiency = st.tabs(["Cotação", "Valuation (P/L)", "Eficiência (ROE)"])

    with tab_price:
        st.caption("Evolução do preço registrado em cada consulta no terminal.")
        st.line_chart(df['price'], color="#8C1007")

    with tab_valuation:
        st.caption("Evolução do Múltiplo Preço/Lucro (P/L).")
        st.line_chart(df['p_l'], color="#660B05")

    with tab_efficiency:
        st.caption("Evolução do Retorno sobre Patrimônio Líquido (ROE).")
        roe_display = df['roe'] * 100 if df['roe'].max() <= 1.0 else df['roe']
        st.line_chart(roe_display, color="#979797")

def render_recent_news_list(news_data: list, sentiment_analysis: dict = None):
    """Renderiza notícias e análise de sentimento."""
    st.header("Notícias & Sentimento")
    
    if sentiment_analysis and isinstance(sentiment_analysis, dict):
        classe = sentiment_analysis.get("classe", "Neutro")
        analise = sentiment_analysis.get("analise", "")
        
        # Mantemos emojis apenas no clima de notícias conforme solicitado
        if "Positivo" in classe: st.success(f"**Sentimento IA: {classe}** 🚀\n\n{analise}")
        elif "Negativo" in classe: st.error(f"**Sentimento IA: {classe}** ⚠️\n\n{analise}")
        else: st.info(f"**Sentimento IA: {classe}** 🔍\n\n{analise}")
    
    st.divider()
    if not news_data:
        st.info("Sem registros de notícias para esta consulta.")
        return

    for n in news_data[:5]:
        with st.expander(f"{n.get('title', 'Sem título')}"):
            st.write(f"*Fonte: {n.get('publisher', 'Fonte desconhecida')}*")
            st.link_button("Abrir Fonte", n.get('link', '#'), width='stretch')

def render_ai_analysis(analysis: dict):
    """Exibe a síntese qualitativa da IA unificada em uma única aba."""
    st.subheader("📌 Modelo de Geração de Valor")
    st.write(analysis.get("resumo_negocio", "N/A"))
    
    st.divider()
    
    st.subheader("⚖️ Análise Qualitativa de Downside")
    st.markdown(f"> {analysis.get('analise_indicadores', 'N/A')}")
    
    st.divider()
    
    st.subheader("❓ Questões Investigativas")
    for i, q in enumerate(analysis.get("perguntas_investigativas", []), 1):
        st.write(f"**{i}.** {q}")
