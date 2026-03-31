"""
DAG: llm_synthesis
Agendamento: toda segunda-feira às 9h (após monday_briefing)
Objetivo: buscar dados processados via RAG e gerar síntese LLM para o comitê.

Fluxo:
  1. fetch_context  — busca dados relevantes dos marts via psycopg2 (RAG)
  2. generate_report — envia contexto para LLM e gera síntese por ticker
"""

from datetime import timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

TICKERS = ["ASAI3", "PRIO3", "RENT3"]

DEFAULT_ARGS = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def fetch_context_task():
    from synthesis.rag import fetch_context
    fetch_context(tickers=TICKERS)


def generate_report_task():
    from synthesis.llm_report import generate_reports
    generate_reports(tickers=TICKERS)


with DAG(
    dag_id="llm_synthesis",
    description="RAG + síntese LLM semanal por ticker para o comitê das 14h",
    schedule_interval="0 9 * * 1",   # toda segunda às 9h
    start_date=days_ago(1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["llm", "synthesis", "rag"],
) as dag:

    t_rag = PythonOperator(
        task_id="fetch_context",
        python_callable=fetch_context_task,
        doc_md="Busca dados dos marts no PostgreSQL e monta contexto para o LLM (RAG).",
    )

    t_llm = PythonOperator(
        task_id="generate_report",
        python_callable=generate_report_task,
        doc_md="Envia contexto ao LLM e gera síntese das mudanças relevantes pela tese.",
    )

    t_rag >> t_llm
