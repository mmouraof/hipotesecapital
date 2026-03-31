"""
SiteWriter — salva DataFrames na bronze (Parquet) e silver (PostgreSQL).

Fluxo:
  DataFrame → Bronze (Parquet) → Silver (PostgreSQL staging)

A tabela no PostgreSQL é criada automaticamente se não existir.
Todas as colunas são TEXT na raw, a tipagem é feita pelo dbt silver.
"""

import os
import psycopg2
import pandas as pd
from pathlib import Path
from psycopg2.extras import execute_values

BRONZE_PATH = Path(__file__).resolve().parents[2] / "data-lakehouse" / "bronze" / "site"

PG_HOST     = os.getenv("PG_HOST",     "postgres")
PG_PORT     = os.getenv("PG_PORT",     "5432")
PG_DB       = os.getenv("PG_DB",       "hipotetical_fia")
PG_USER     = os.getenv("PG_USER",     "airflow")
PG_PASSWORD = os.getenv("PG_PASSWORD", "airflow")


def _get_conn():
    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT,
        dbname=PG_DB, user=PG_USER, password=PG_PASSWORD,
    )


def write_bronze(table: str, df: pd.DataFrame) -> Path:
    """Salva DataFrame como Parquet na bronze/site/{table}/."""
    out_dir = BRONZE_PATH / table
    out_dir.mkdir(parents=True, exist_ok=True)

    ref_date = str(df["reference_date"].iloc[0]) if "reference_date" in df.columns else "unknown"
    out_file = out_dir / f"{ref_date}.parquet"
    df.to_parquet(out_file, index=False)
    print(f"[BRONZE] {table} → {out_file}")
    return out_file


def write_silver(table: str, df: pd.DataFrame) -> None:
    """
    Cria a tabela no PostgreSQL se não existir (schema: staging)
    e insere os dados. Todas as colunas como TEXT.
    """
    df_text = df.astype(str)
    columns = list(df_text.columns)

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            # Cria tabela dinamicamente se não existir
            col_defs = ", ".join(f'"{c}" TEXT' for c in columns)
            cur.execute(
                f'CREATE TABLE IF NOT EXISTS staging."{table}" ({col_defs});'
            )

            # Insere dados
            col_str = ", ".join(f'"{c}"' for c in columns)
            values  = [tuple(row) for row in df_text.itertuples(index=False, name=None)]
            execute_values(
                cur,
                f'INSERT INTO staging."{table}" ({col_str}) VALUES %s',
                values,
            )
        conn.commit()
        print(f"[SILVER] {len(df)} linhas → staging.\"{table}\"")
    except Exception as e:
        conn.rollback()
        print(f"[SILVER] Erro em {table}: {e}")
        raise
    finally:
        conn.close()


def write_all(tables: dict[str, pd.DataFrame]) -> None:
    """Processa todos os DataFrames: bronze + silver."""
    for table, df in tables.items():
        write_bronze(table, df)
        write_silver(table, df)
