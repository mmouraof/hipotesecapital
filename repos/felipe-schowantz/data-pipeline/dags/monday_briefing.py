"""
DAG: monday_briefing
Agendamento: toda segunda-feira às 8h
Objetivo: coletar dados macro e micro, carregar no PostgreSQL,
          rodar transformações dbt e acionar síntese LLM.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

# ── defaults ────────────────────────────────────────────────────────────────
DEFAULT_ARGS = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

TICKERS = ["ASAI3.SA", "PRIO3.SA", "RENT3.SA"]

# ── imports dos extractors e loaders ────────────────────────────────────────
def extract_bcb_task():
    from extractors.macro_bcb import extract_bcb
    extract_bcb()

def extract_yfinance_task():
    from extractors.market_yfinance import extract_yfinance
    extract_yfinance(tickers=TICKERS)

def extract_cvm_task():
    from extractors.fundamentals_cvm import extract_cvm
    extract_cvm(tickers=["ASAI3", "PRIO3", "RENT3"])

def load_to_postgres_task():
    from loaders.postgres_loader import load_all_parquets
    load_all_parquets()

def dbt_run_task():
    from loaders.postgres_loader import run_dbt
    run_dbt()

# ── DAG ─────────────────────────────────────────────────────────────────────
with DAG(
    dag_id="monday_briefing",
    description="Pipeline semanal de coleta, transformação e síntese para o comitê das 14h",
    schedule_interval="0 8 * * 1",   # toda segunda às 8h
    start_date=days_ago(1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["briefing", "finance"],
) as dag:

    # ── Extração ─────────────────────────────────────────────────────────────
    t_bcb = PythonOperator(
        task_id="extract_bcb",
        python_callable=extract_bcb_task,
        doc_md="Coleta indicadores macro do Banco Central (SELIC, IPCA, câmbio, desemprego).",
    )

    t_yfinance = PythonOperator(
        task_id="extract_yfinance",
        python_callable=extract_yfinance_task,
        doc_md="Coleta preço, múltiplos e margens via Yahoo Finance para ASAI3, PRIO3 e RENT3.",
    )

    t_cvm = PythonOperator(
        task_id="extract_cvm",
        python_callable=extract_cvm_task,
        doc_md="Coleta linhas de DRE e dados cadastrais via CVM (ITR/DFP).",
    )

    # ── Carga no PostgreSQL ───────────────────────────────────────────────────
    t_load = PythonOperator(
        task_id="load_to_postgres",
        python_callable=load_to_postgres_task,
        doc_md="Lê os Parquets da camada raw e carrega no PostgreSQL (schema: staging).",
    )

    # ── Transformação dbt ─────────────────────────────────────────────────────
    t_dbt = PythonOperator(
        task_id="dbt_run",
        python_callable=dbt_run_task,
        doc_md="Executa modelos dbt: staging → marts. Roda testes de qualidade em seguida.",
    )

    # ── Dependências ──────────────────────────────────────────────────────────
    [t_bcb, t_yfinance, t_cvm] >> t_load >> t_dbt
