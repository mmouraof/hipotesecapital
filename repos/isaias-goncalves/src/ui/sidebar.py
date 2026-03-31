import streamlit as st
from typing import List, Tuple
from config import LOGO_LIGHT, DEFAULT_TICKER, AVAILABLE_MODELS, VERSION

def render_sidebar(orchestrator) -> Tuple[str, str, str, bool]:
    """
    Renderiza a barra lateral com lógica de atualização imediata do histórico.
    """
    with st.sidebar:
        st.image(LOGO_LIGHT, width='stretch')
        st.divider()
        
        st.subheader("🛠️ Parâmetros")
        
        # Campo de Ticker com Session State para ser reativo
        if "ticker_input" not in st.session_state:
            st.session_state.ticker_input = DEFAULT_TICKER

        ticker = st.text_input(
            "Ticker B3", 
            value=st.session_state.ticker_input,
            key="ticker_field",
            help="Digite e pressione Enter para atualizar as versões disponíveis.",
            placeholder="Ex: ASAI3..."
        ).upper()

        # Busca versões disponíveis para este ticker específico
        history_dates = orchestrator.get_history_options(ticker)
        
        options = ["Live (Nova Análise)"]
        if history_dates:
            options.extend(history_dates)
        
        version = st.selectbox(
            "Versão da Análise",
            options,
            index=0,
            help="Escolha entre gerar dados novos ou carregar capturas históricas do banco."
        )
        
        model_name = st.selectbox(
            "Modelo Analítico (LLM)", 
            AVAILABLE_MODELS,
            index=0
        )
        
        st.write("")
        analyze_button = st.button("Executar Diligência", width='stretch', type="primary")
        
        st.markdown("<br>" * 5, unsafe_allow_html=True)
        st.caption("---")
        st.caption(f"Terminal Analítico *por Isaías Gouvêa Gonçalves* | Versão {VERSION}")
        
        return ticker, model_name, version, analyze_button
