import os
import io
import json
import tempfile
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy import select

from src.database import engine, DadosCotacao, IndicadoresFundamentalistas, Ativo, Noticias
from src.backend.llm_utils import generate_ai_report, pdf_report_saver
import src.backend.scrapper1 as s1

load_dotenv()

def generate_dashboard_report():
    # ══════════════════════════════════════════════════════════════════════════════
    #  CONFIG
    # ══════════════════════════════════════════════════════════════════════════════

    st.set_page_config(
        page_title="HipoteseCapital",
        page_icon="📊",
        layout="wide",
    )

    COTACAO_COLS = {
        "Cotacao":           "Cotação",
        "Min52semanas":      "Mín. 52 Sem.",
        "Max52semanas":      "Máx. 52 Sem.",
        "VolumeMedio2Meses": "Vol. Médio 2M",
        "ValorMercado":      "Valor de Mercado",
        "NumeroAcoes":       "Nº de Ações",
    }

    INDICADOR_COLS = {
        "PL":                  "P/L",
        "ROE":                 "ROE (%)",
        "DividaLiquidaEBITDA": "Dív. Líq./EBITDA",
        "MargemLiquida":       "Margem Líquida (%)",
        "DividendYield":       "Dividend Yield (%)",
    }

    # ══════════════════════════════════════════════════════════════════════════════
    #  CACHE / QUERIES
    # ══════════════════════════════════════════════════════════════════════════════

    @st.cache_data(ttl=300)
    def load_tickers() -> list[str]:
        with Session(engine) as s:
            rows = s.execute(select(Ativo.Ticker)).scalars().all()
        return sorted(rows)


    @st.cache_data(ttl=300)
    def load_cotacao(tickers: list[str], dt_ini: date, dt_fim: date) -> pd.DataFrame:
        with Session(engine) as s:
            q = (
                select(DadosCotacao)
                .where(DadosCotacao.Ticker.in_(tickers))
                .where(DadosCotacao.DataConsulta.between(dt_ini, dt_fim))
                .order_by(DadosCotacao.DataConsulta)
            )
            rows = s.execute(q).scalars().all()
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame([{
            "Data":              r.DataConsulta,
            "Ticker":            r.Ticker,
            "Cotacao":           float(r.Cotacao or 0),
            "Min52semanas":      float(r.Min52semanas or 0),
            "Max52semanas":      float(r.Max52semanas or 0),
            "VolumeMedio2Meses": float(r.VolumeMedio2Meses or 0),
            "ValorMercado":      float(r.ValorMercado or 0),
            "NumeroAcoes":       float(r.NumeroAcoes or 0),
        } for r in rows])
        df["Data"] = pd.to_datetime(df["Data"])
        return df


    @st.cache_data(ttl=300)
    def load_indicadores(tickers: list[str], dt_ini: date, dt_fim: date) -> pd.DataFrame:
        with Session(engine) as s:
            q = (
                select(IndicadoresFundamentalistas)
                .where(IndicadoresFundamentalistas.Ticker.in_(tickers))
                .where(IndicadoresFundamentalistas.DataConsulta.between(dt_ini, dt_fim))
                .order_by(IndicadoresFundamentalistas.DataConsulta)
            )
            rows = s.execute(q).scalars().all()
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame([{
            "Data":                r.DataConsulta,
            "Ticker":              r.Ticker,
            "PL":                  float(r.PL or 0),
            "ROE":                 float(r.ROE or 0),
            "DividaLiquidaEBITDA": float(r.DividaLiquidaEBITDA or 0),
            "MargemLiquida":       float(r.MargemLiquida or 0),
            "DividendYield":       float(r.DividendYield or 0),
        } for r in rows])
        df["Data"] = pd.to_datetime(df["Data"])
        return df


    @st.cache_data(ttl=300)
    def load_ativos_info(tickers: list[str]) -> pd.DataFrame:
        with Session(engine) as s:
            rows = s.execute(
                select(Ativo).where(Ativo.Ticker.in_(tickers))
            ).scalars().all()
        return pd.DataFrame([{
            "Ticker":   r.Ticker,
            "Empresa":  r.EmpresaAtivo,
            "Setor":    r.SetorAtuacaoEmpresa,
            "Segmento": r.SegmentoAtuacaoEmpresa,
            "Resumo":   r.ResumoEmpresa,
        } for r in rows])


    @st.cache_data(ttl=300)
    def load_noticias(ticker: str) -> list[dict]:
        with Session(engine) as s:
            q = (
                select(Noticias)
                .where(Noticias.Ticker == ticker)
                .order_by(Noticias.DataConsulta.desc())
                .limit(5)
            )
            rows = s.execute(q).scalars().all()
        return [
            {
                "url":           r.URLNoticia,
                "resumo":        r.Resumo,
                "classificador": r.Classificador,
                "escala":        float(r.Escala or 0),
            }
            for r in rows
        ]


    # ══════════════════════════════════════════════════════════════════════════════
    #  HELPERS
    # ══════════════════════════════════════════════════════════════════════════════

    def line_chart(df: pd.DataFrame, col: str, label: str, tickers: list[str]) -> go.Figure:
        fig = px.line(
            df[df["Ticker"].isin(tickers)],
            x="Data", y=col, color="Ticker",
            labels={"Data": "Data", col: label},
            title=label,
            template="plotly_dark",
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=36, b=0),
            legend=dict(orientation="h", y=-0.2),
            title_font_size=14,
        )
        return fig


    def latest_kpi(df: pd.DataFrame, col: str, ticker: str, fmt: str = "{:.2f}") -> str:
        sub = df[df["Ticker"] == ticker]
        if sub.empty:
            return "—"
        val = sub.sort_values("Data").iloc[-1][col]
        try:
            return fmt.format(val)
        except Exception:
            return str(val)


    def build_dados_para_relatorio(ticker: str, df_cot: pd.DataFrame, df_ind: pd.DataFrame, df_ati: pd.DataFrame) -> dict:
        """Monta o dicionário no formato esperado por generate_ai_report."""
        ati = df_ati[df_ati["Ticker"] == ticker]
        cad = ati.iloc[0].to_dict() if not ati.empty else {}

        def last_row(df):
            sub = df[df["Ticker"] == ticker].sort_values("Data")
            return sub.iloc[-1].to_dict() if not sub.empty else {}

        cot = last_row(df_cot)
        ind = last_row(df_ind)
        noticias_raw = load_noticias(ticker)
        noticias = {f"noticia_{i+1}": [n["url"], n["resumo"], n["classificador"], n["escala"]]
                    for i, n in enumerate(noticias_raw)}

        return {
            "ticker": ticker,
            "data_coleta": date.today().strftime("%Y-%m-%d"),
            "dados_cadastrais": {
                "nome_empresa": cad.get("Empresa"),
                "setor":        cad.get("Setor"),
                "segmento":     cad.get("Segmento"),
                "resumo_negocio": cad.get("Resumo"),
            },
            "dados_cotacao": {
                "cotacao":             cot.get("Cotacao"),
                "data_ultima_cotacao": str(cot.get("Data", "")),
                "minimo_52_semanas":   cot.get("Min52semanas"),
                "maximo_52_semanas":   cot.get("Max52semanas"),
                "volume_medio_2_meses":cot.get("VolumeMedio2Meses"),
                "valor_de_mercado":    cot.get("ValorMercado"),
                "numero_de_acoes":     cot.get("NumeroAcoes"),
            },
            "indicadores_fundamentalistas": {
                "p_l":                   ind.get("PL"),
                "roe":                   ind.get("ROE"),
                "divida_liquida_ebitda": ind.get("DividaLiquidaEBITDA"),
                "margem_liquida":        ind.get("MargemLiquida"),
                "dividend_yield":        ind.get("DividendYield"),
            },
            "noticias": noticias,
        }


    # ══════════════════════════════════════════════════════════════════════════════
    #  SIDEBAR  —  FILTROS GLOBAIS
    # ══════════════════════════════════════════════════════════════════════════════

    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/combo-chart.png", width=60)
        st.title("HipoteseCapital")
        st.markdown("---")

        all_tickers = load_tickers()
        sel_tickers = st.multiselect(
            "📌 Tickers",
            options=all_tickers,
            default=all_tickers[:2] if len(all_tickers) >= 2 else all_tickers,
        )

        tipo_dados = st.radio(
            "📂 Tipo de dados",
            ["Cotação", "Indicadores Fundamentalistas", "Ambos"],
            index=2,
        )

        st.markdown("---")
        st.markdown("**🗓 Período**")
        dt_ini = st.date_input("De",  value=date.today() - timedelta(days=180))
        dt_fim = st.date_input("Até", value=date.today())

        st.markdown("---")
        if st.button("🔄 Atualizar cache"):
            st.cache_data.clear()
            st.rerun()

    if not all_tickers:
        st.info("Nenhum ticker cadastrado ainda. Cadastre um abaixo para começar.")

        with st.form("form_cadastro"):
            novo_ticker = st.text_input("Ticker", placeholder="Ex: PETR4.SA, VALE3.SA, AAPL").strip().upper()
            submitted = st.form_submit_button("➕ Cadastrar e coletar dados")

        if submitted:
            if not novo_ticker:
                st.warning("Digite um ticker válido.")
            else:
                with st.spinner(f"Coletando dados de {novo_ticker}..."):
                    try:
                        from src.database import Base
                        from src.database.database import insert_data
                        Base.metadata.create_all(engine)

                        dados = s1.get_full_data(novo_ticker)
                        if not dados:
                            st.error("Ticker não encontrado ou sem dados disponíveis.")
                        else:
                            with Session(engine) as session:
                                insert_data(session, novo_ticker, dados)
                                session.commit()
                            st.success(f"✅ {novo_ticker} cadastrado com sucesso! Recarregue a página.")
                            st.cache_data.clear()
                            st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao cadastrar {novo_ticker}: {e}")
        st.stop()

    if not sel_tickers:
        st.warning("Selecione ao menos um ticker na barra lateral.")
        st.stop()

    # ══════════════════════════════════════════════════════════════════════════════
    #  CARREGA DADOS
    # ══════════════════════════════════════════════════════════════════════════════

    df_cot = load_cotacao(sel_tickers, dt_ini, dt_fim)
    df_ind = load_indicadores(sel_tickers, dt_ini, dt_fim)
    df_ati = load_ativos_info(sel_tickers)

    # ══════════════════════════════════════════════════════════════════════════════
    #  CABEÇALHO
    # ══════════════════════════════════════════════════════════════════════════════

    st.title("📊 Dashboard — HipoteseCapital")
    st.caption(f"Período: {dt_ini} → {dt_fim}  |  Tickers: {', '.join(sel_tickers)}")
    st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════════════
    #  SEÇÃO 1 – DADOS CADASTRAIS
    # ══════════════════════════════════════════════════════════════════════════════

    with st.expander("🏢 Dados Cadastrais", expanded=False):
        if df_ati.empty:
            st.info("Nenhum dado cadastral encontrado.")
        else:
            for _, row in df_ati.iterrows():
                st.subheader(f"{row['Ticker']} — {row['Empresa']}")
                col1, col2 = st.columns(2)
                col1.markdown(f"**Setor:** {row['Setor']}")
                col2.markdown(f"**Segmento:** {row['Segmento']}")
                st.markdown(f"_{row['Resumo']}_")
                st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════════════
    #  SEÇÃO 2 – KPIs MAIS RECENTES
    # ══════════════════════════════════════════════════════════════════════════════

    st.subheader("📌 Últimos valores registrados")

    for ticker in sel_tickers:
        st.markdown(f"#### {ticker}")

        if tipo_dados in ("Cotação", "Ambos") and not df_cot.empty:
            cols = st.columns(5)
            cols[0].metric("Cotação",          latest_kpi(df_cot, "Cotacao",      ticker, "R$ {:.2f}"))
            cols[1].metric("Mín. 52 Sem.",     latest_kpi(df_cot, "Min52semanas", ticker, "R$ {:.2f}"))
            cols[2].metric("Máx. 52 Sem.",     latest_kpi(df_cot, "Max52semanas", ticker, "R$ {:.2f}"))
            cols[3].metric("Valor de Mercado", latest_kpi(df_cot, "ValorMercado", ticker, "R$ {:,.0f}"))
            cols[4].metric("Nº de Ações",      latest_kpi(df_cot, "NumeroAcoes",  ticker, "{:,.0f}"))

        if tipo_dados in ("Indicadores Fundamentalistas", "Ambos") and not df_ind.empty:
            cols2 = st.columns(5)
            cols2[0].metric("P/L",             latest_kpi(df_ind, "PL",                  ticker))
            cols2[1].metric("ROE (%)",          latest_kpi(df_ind, "ROE",                 ticker))
            cols2[2].metric("Dív/EBITDA",       latest_kpi(df_ind, "DividaLiquidaEBITDA", ticker))
            cols2[3].metric("Margem Líq. (%)",  latest_kpi(df_ind, "MargemLiquida",        ticker))
            cols2[4].metric("DY (%)",           latest_kpi(df_ind, "DividendYield",         ticker))

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════════════
    #  SEÇÃO 3 – GRÁFICOS TEMPORAIS DE COTAÇÃO
    # ══════════════════════════════════════════════════════════════════════════════

    if tipo_dados in ("Cotação", "Ambos"):
        st.subheader("📈 Evolução — Dados de Cotação")

        if df_cot.empty:
            st.info("Nenhum dado de cotação no período selecionado.")
        else:
            sel_cot_metrics = st.multiselect(
                "Métricas de cotação",
                options=list(COTACAO_COLS.keys()),
                default=["Cotacao", "Min52semanas", "Max52semanas"],
                format_func=lambda x: COTACAO_COLS[x],
                key="sel_cot",
            )
            for metric in sel_cot_metrics:
                st.plotly_chart(
                    line_chart(df_cot, metric, COTACAO_COLS[metric], sel_tickers),
                    use_container_width=True,
                )
            with st.expander("🔍 Tabela — Dados de Cotação"):
                df_show = df_cot[df_cot["Ticker"].isin(sel_tickers)].copy()
                df_show.rename(columns={**COTACAO_COLS, "Data": "Data"}, inplace=True)
                st.dataframe(df_show.sort_values("Data", ascending=False), use_container_width=True)

        st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════════════
    #  SEÇÃO 4 – GRÁFICOS TEMPORAIS DE INDICADORES
    # ══════════════════════════════════════════════════════════════════════════════

    if tipo_dados in ("Indicadores Fundamentalistas", "Ambos"):
        st.subheader("📉 Evolução — Indicadores Fundamentalistas")

        if df_ind.empty:
            st.info("Nenhum dado de indicadores no período selecionado.")
        else:
            sel_ind_metrics = st.multiselect(
                "Indicadores",
                options=list(INDICADOR_COLS.keys()),
                default=list(INDICADOR_COLS.keys()),
                format_func=lambda x: INDICADOR_COLS[x],
                key="sel_ind",
            )
            for i in range(0, len(sel_ind_metrics), 2):
                pair = sel_ind_metrics[i:i+2]
                cols = st.columns(len(pair))
                for j, metric in enumerate(pair):
                    cols[j].plotly_chart(
                        line_chart(df_ind, metric, INDICADOR_COLS[metric], sel_tickers),
                        use_container_width=True,
                    )
            with st.expander("🔍 Tabela — Indicadores Fundamentalistas"):
                df_show = df_ind[df_ind["Ticker"].isin(sel_tickers)].copy()
                df_show.rename(columns={**INDICADOR_COLS, "Data": "Data"}, inplace=True)
                st.dataframe(df_show.sort_values("Data", ascending=False), use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════════
    #  SEÇÃO 5 – COMPARATIVO ENTRE TICKERS
    # ══════════════════════════════════════════════════════════════════════════════

    st.markdown("---")
    st.subheader("⚖️ Comparativo entre Tickers — Último Registro")

    if len(sel_tickers) > 1:
        tab_cot, tab_ind = st.tabs(["Cotação", "Indicadores"])

        with tab_cot:
            if not df_cot.empty:
                latest_cot = (
                    df_cot[df_cot["Ticker"].isin(sel_tickers)]
                    .sort_values("Data").groupby("Ticker").last().reset_index()
                )
                metric_cot = st.selectbox(
                    "Métrica", list(COTACAO_COLS.keys()),
                    format_func=lambda x: COTACAO_COLS[x], key="cmp_cot",
                )
                fig = px.bar(latest_cot, x="Ticker", y=metric_cot, color="Ticker",
                            title=COTACAO_COLS[metric_cot], template="plotly_dark", text_auto=".2s")
                fig.update_layout(margin=dict(t=36, b=0), showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

        with tab_ind:
            if not df_ind.empty:
                latest_ind = (
                    df_ind[df_ind["Ticker"].isin(sel_tickers)]
                    .sort_values("Data").groupby("Ticker").last().reset_index()
                )
                metric_ind = st.selectbox(
                    "Indicador", list(INDICADOR_COLS.keys()),
                    format_func=lambda x: INDICADOR_COLS[x], key="cmp_ind",
                )
                fig = px.bar(latest_ind, x="Ticker", y=metric_ind, color="Ticker",
                            title=INDICADOR_COLS[metric_ind], template="plotly_dark", text_auto=".2f")
                fig.update_layout(margin=dict(t=36, b=0), showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Selecione mais de um ticker para ver o comparativo.")

    # ══════════════════════════════════════════════════════════════════════════════
    #  SEÇÃO 6 – GERAÇÃO DE RELATÓRIO PDF
    # ══════════════════════════════════════════════════════════════════════════════

    st.markdown("---")
    st.subheader("📄 Relatório Fundamentalista (IA)")

    st.markdown(
        "Gera um relatório completo em PDF com análise de indicadores, síntese de notícias "
        "e perguntas críticas do analista, produzido pelo Claude."
    )

    col_sel, col_btn = st.columns([2, 1])

    ticker_relatorio = col_sel.selectbox(
        "Ticker para o relatório",
        options=sel_tickers,
        key="ticker_pdf",
    )

    gerar = col_btn.button("🤖 Gerar Relatório PDF", use_container_width=True)

    # Estado persistente para armazenar o PDF gerado entre reruns
    if "pdf_bytes"   not in st.session_state:
        st.session_state.pdf_bytes   = None
    if "pdf_ticker"  not in st.session_state:
        st.session_state.pdf_ticker  = None

    if gerar:
        if df_cot.empty or df_ind.empty or df_ati.empty:
            st.warning("Dados insuficientes para gerar o relatório. Verifique os filtros.")
        else:
            with st.spinner("Consultando Claude e gerando PDF — isso pode levar alguns segundos..."):
                try:
                    dados_relatorio = build_dados_para_relatorio(
                        ticker_relatorio, df_cot, df_ind, df_ati
                    )
                    html = generate_ai_report(dados_relatorio)

                    # Salva em arquivo temporário e lê os bytes para download
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                        pdf_path = tmp.name

                    pdf_report_saver(html, pdf_path)

                    with open(pdf_path, "rb") as f:
                        st.session_state.pdf_bytes  = f.read()
                        st.session_state.pdf_ticker = ticker_relatorio

                    os.remove(pdf_path)
                    st.success("✅ Relatório gerado com sucesso!")

                except Exception as e:
                    st.error(f"Erro ao gerar relatório: {e}")

    # Botão de download (persiste entre reruns enquanto o PDF estiver em session_state)
    if st.session_state.pdf_bytes and st.session_state.pdf_ticker:
        nome_arquivo = f"relatorio_{st.session_state.pdf_ticker}_{date.today()}.pdf"
        st.download_button(
            label="⬇️ Baixar PDF",
            data=st.session_state.pdf_bytes,
            file_name=nome_arquivo,
            mime="application/pdf",
            use_container_width=False,
        )

    # ══════════════════════════════════════════════════════════════════════════════
    #  RODAPÉ
    # ══════════════════════════════════════════════════════════════════════════════

    st.markdown("---")
    st.caption("HipoteseCapital © 2025 — Dados via yfinance | Powered by Streamlit + SQLAlchemy")