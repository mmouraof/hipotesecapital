"""
Loader — PostgreSQL + dbt
1. Lê os Parquets da camada bronze e carrega nas tabelas de staging do PostgreSQL.
2. Dispara dbt run + dbt test para transformar staging → marts.
"""

import os
import subprocess
import psycopg2
import pandas as pd
from pathlib import Path
from psycopg2.extras import execute_values

DBT_PROJECT_DIR = Path(__file__).resolve().parents[2] / "dbt"

# Parâmetros de conexão
PG_HOST     = os.getenv("PG_HOST",     "postgres")
PG_PORT     = os.getenv("PG_PORT",     "5432")
PG_DB       = os.getenv("PG_DB",       "hipotetical_fia")
PG_USER     = os.getenv("PG_USER",     "airflow")
PG_PASSWORD = os.getenv("PG_PASSWORD", "airflow")

BRONZE_PATH = Path(__file__).resolve().parents[2] / "data-lakehouse" / "bronze"

TABLE_MAP = {
    "bcb":      "staging.raw_bcb",
    "yfinance": "staging.raw_yfinance",
    "cvm":      "staging.raw_cvm",
}


def get_conn():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD,
    )


def load_source(source: str) -> None:
    """Carrega o Parquet mais recente de uma fonte no PostgreSQL via psycopg2."""
    source_path = BRONZE_PATH / source
    parquets = sorted(source_path.glob("*.parquet"))
    if not parquets:
        print(f"[PG] Nenhum Parquet encontrado para {source}")
        return

    latest = parquets[-1]
    df = pd.read_parquet(latest)

    # Converte timestamps para string para evitar problemas de tipo
    for col in df.select_dtypes(include=["datetimetz", "datetime64[ns, UTC]"]).columns:
        df[col] = df[col].astype(str)

    table = TABLE_MAP[source]
    columns = list(df.columns)
    values  = [tuple(row) for row in df.itertuples(index=False, name=None)]

    col_str = ", ".join(f'"{c}"' for c in columns)
    sql = f'INSERT INTO {table} ({col_str}) VALUES %s'

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(f"TRUNCATE TABLE {table}")
            execute_values(cur, sql, values)
        conn.commit()
        print(f"[PG] {len(df)} linhas carregadas em {table} a partir de {latest.name}")
    except Exception as e:
        conn.rollback()
        print(f"[PG] Erro ao carregar {source}: {e}")
        raise
    finally:
        conn.close()


def run_dbt() -> None:
    """Executa dbt run + dbt test após o carregamento."""
    import shutil
    dbt_bin = shutil.which("dbt") or "/home/airflow/.local/bin/dbt"
    print(f"[DBT] Usando binário: {dbt_bin}")

    print("[DBT] Iniciando dbt run...")
    result = subprocess.run(
        [dbt_bin, "run", "--profiles-dir", str(DBT_PROJECT_DIR)],
        cwd=str(DBT_PROJECT_DIR),
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"[DBT] ERRO:\n{result.stderr}")
        raise RuntimeError("[DBT] dbt run falhou.")

    print("[DBT] Iniciando dbt test...")
    result = subprocess.run(
        [dbt_bin, "test", "--profiles-dir", str(DBT_PROJECT_DIR)],
        cwd=str(DBT_PROJECT_DIR),
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"[DBT] WARN: dbt test com falhas:\n{result.stderr}")


def load_all_parquets() -> None:
    """Carrega todas as fontes no PostgreSQL via psycopg2."""
    for source in TABLE_MAP:
        load_source(source)


if __name__ == "__main__":
    load_all_parquets()
