import streamlit as st
from core.orchestrator import AnalyticalOrchestrator
from core.collector import DataCollector
from utils.logger import logger

# UI
from ui.styles import apply_custom_styles
from ui.sidebar import render_sidebar
from ui.components import (
    render_header,
    render_summary_cards,
    render_price_chart,
    render_historical_trends,
    render_recent_news_list,
    render_ai_analysis
)

from config import PROJECT_NAME, VERSION, ICON_BRAND, DB_PATH

# Configuração da Página
st.set_page_config(
    page_title=PROJECT_NAME,
    page_icon=ICON_BRAND,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Singleton do Orquestrador (Injetando DB_PATH)
if "orchestrator" not in st.session_state:
    from core.database import DatabaseManager
    db_manager = DatabaseManager(db_path=DB_PATH)
    st.session_state.orchestrator = AnalyticalOrchestrator(db=db_manager)

def main():
    apply_custom_styles()
    
    # 1. Sidebar Inteligente
    ticker, model, version, run_btn = render_sidebar(st.session_state.orchestrator)

    if run_btn:
        try:
            with st.status(f"Processando {ticker}...", expanded=True) as status:
                data, analysis, is_historical = st.session_state.orchestrator.get_data(ticker, version, model)
                status.update(label="Diligência Carregada!", state="complete")

            # 2. Cabeçalho e Contexto
            nome_empresa = data.get('cadastral', {}).get('nome', ticker)
            render_header(ticker, nome_empresa)
            
            if is_historical:
                st.warning(f"VISÃO HISTÓRICA: Dados capturados originalmente em {version}")

            # 3. Layout Principal organizado por Abas
            col_main, col_side = st.columns([0.65, 0.35], gap="large")
            
            with col_main:
                tab_quant, tab_qual = st.tabs(["Análise Quantitativa", "Análise Qualitativa (IA)"])
                
                with tab_quant:
                    render_summary_cards(data)
                    
                    if not is_historical:
                        render_price_chart(DataCollector(ticker))
                    
                    history_df = st.session_state.orchestrator.get_historical_trends(ticker)
                    render_historical_trends(history_df)
                
                with tab_qual:
                    render_ai_analysis(analysis)

                st.info(f"Origem: {'SQLite (Local)' if is_historical else 'APIs Externas'}")
                
            with col_side:
                render_recent_news_list(
                    data.get("news", []), 
                    sentiment_analysis=analysis.get("sentimento_noticias")
                )


        except Exception as e:
            st.error(f"Erro no processamento: {e}")
            logger.error(f"App Crash: {e}")

    else:
        # Boas-vindas (Logo removida conforme solicitado)
        st.title(PROJECT_NAME)
        st.markdown(f"**Versão {VERSION}**")
        
        st.info("Insira um ativo na barra lateral e pressione Enter para ver o histórico disponível ou clique em Executar Diligência.")

if __name__ == "__main__":
    main()
