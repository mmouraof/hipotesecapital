import sqlite3
from datetime import datetime, timezone

import pandas as pd


DEFAULT_DB_PATH = "data/pipeline.sqlite3"


def _utc_now_iso():
    # Timestamp padrão em UTC para manter consistência histórica.
    return datetime.now(timezone.utc).isoformat()


def get_connection(db_path=DEFAULT_DB_PATH):
    # row_factory facilita ler colunas por nome nas consultas.
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path=DEFAULT_DB_PATH):
    # Cria a estrutura mínima para cadastro estático + snapshots por execução.
    conn = get_connection(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS companies (
                ticker TEXT PRIMARY KEY,
                nome TEXT,
                setor TEXT,
                industria TEXT,
                descricao TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS pipeline_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                total_tickers INTEGER DEFAULT 0,
                processed_tickers INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS fundamentals_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                captured_at TEXT NOT NULL,
                pl REAL,
                roe REAL,
                dy REAL,
                divida_equity REAL,
                margem_liquida REAL,
                preco_atual REAL,
                moeda TEXT,
                FOREIGN KEY (run_id) REFERENCES pipeline_runs(id),
                FOREIGN KEY (ticker) REFERENCES companies(ticker)
            );

            CREATE TABLE IF NOT EXISTS news_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                captured_at TEXT NOT NULL,
                title TEXT,
                publisher TEXT,
                published_at TEXT,
                link TEXT,
                summary TEXT,
                FOREIGN KEY (run_id) REFERENCES pipeline_runs(id),
                FOREIGN KEY (ticker) REFERENCES companies(ticker)
            );

            CREATE TABLE IF NOT EXISTS llm_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                captured_at TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT,
                report_markdown TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES pipeline_runs(id),
                FOREIGN KEY (ticker) REFERENCES companies(ticker)
            );

            CREATE INDEX IF NOT EXISTS idx_fundamentals_ticker_time
                ON fundamentals_snapshots (ticker, captured_at DESC);

            CREATE INDEX IF NOT EXISTS idx_news_ticker_time
                ON news_snapshots (ticker, captured_at DESC);

            CREATE INDEX IF NOT EXISTS idx_reports_ticker_time
                ON llm_reports (ticker, captured_at DESC);
            """
        )
        conn.commit()
    finally:
        conn.close()


def start_pipeline_run(total_tickers, db_path=DEFAULT_DB_PATH):
    # Abre uma nova execução para auditoria e acompanhamento do pipeline.
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            INSERT INTO pipeline_runs (started_at, status, total_tickers)
            VALUES (?, ?, ?)
            """,
            (_utc_now_iso(), "running", int(total_tickers)),
        )
        conn.commit()
        return int(cursor.lastrowid)
    finally:
        conn.close()


def finish_pipeline_run(run_id, processed_tickers, error_count, status="finished", notes=None, db_path=DEFAULT_DB_PATH):
    # Fecha a execução com status final e contadores da rodada.
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            UPDATE pipeline_runs
            SET finished_at = ?, status = ?, processed_tickers = ?, error_count = ?, notes = ?
            WHERE id = ?
            """,
            (_utc_now_iso(), status, int(processed_tickers), int(error_count), notes, int(run_id)),
        )
        conn.commit()
    finally:
        conn.close()


def upsert_company(ticker, info_dict, db_path=DEFAULT_DB_PATH):
    # Mantém cadastro da empresa atualizado sem perder o histórico de snapshots.
    conn = get_connection(db_path)
    now = _utc_now_iso()
    try:
        conn.execute(
            """
            INSERT INTO companies (ticker, nome, setor, industria, descricao, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                nome = excluded.nome,
                setor = excluded.setor,
                industria = excluded.industria,
                descricao = excluded.descricao,
                updated_at = excluded.updated_at
            """,
            (
                ticker,
                info_dict.get("Nome"),
                info_dict.get("Setor"),
                info_dict.get("Indústria"),
                info_dict.get("Descrição"),
                now,
                now,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def insert_fundamental_snapshot(run_id, ticker, info_dict, db_path=DEFAULT_DB_PATH):
    # Snapshot imutável de fundamentos para consulta temporal no dashboard.
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO fundamentals_snapshots (
                run_id, ticker, captured_at, pl, roe, dy, divida_equity,
                margem_liquida, preco_atual, moeda
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(run_id),
                ticker,
                _utc_now_iso(),
                info_dict.get("P/L"),
                info_dict.get("ROE"),
                info_dict.get("DY"),
                info_dict.get("Dívida/Equity"),
                info_dict.get("Margem Líquida"),
                info_dict.get("Preço Atual"),
                info_dict.get("Moeda"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def insert_news_snapshots(run_id, ticker, parsed_news_items, db_path=DEFAULT_DB_PATH):
    if not parsed_news_items:
        return

    # Salva lote de notícias da mesma execução/ticker.
    conn = get_connection(db_path)
    try:
        rows = [
            (
                int(run_id),
                ticker,
                _utc_now_iso(),
                news.get("title"),
                news.get("publisher"),
                news.get("published_at"),
                news.get("link"),
                news.get("summary"),
            )
            for news in parsed_news_items
        ]

        conn.executemany(
            """
            INSERT INTO news_snapshots (
                run_id, ticker, captured_at, title, publisher, published_at, link, summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def insert_llm_report(run_id, ticker, provider, model, report_markdown, db_path=DEFAULT_DB_PATH):
    if not report_markdown:
        return

    # Persiste a versão do relatório gerado para reuso no dashboard.
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO llm_reports (run_id, ticker, captured_at, provider, model, report_markdown)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (int(run_id), ticker, _utc_now_iso(), provider, model, report_markdown),
        )
        conn.commit()
    finally:
        conn.close()


def get_tickers_from_db(db_path=DEFAULT_DB_PATH):
    # Fonte de tickers já vistos pelo pipeline.
    conn = get_connection(db_path)
    try:
        rows = conn.execute("SELECT ticker FROM companies ORDER BY ticker").fetchall()
        return [row["ticker"] for row in rows]
    finally:
        conn.close()


def get_fundamentals_history(ticker, limit=100, db_path=DEFAULT_DB_PATH):
    # Retorna série histórica ordenada por data para plotagem.
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT captured_at, pl, roe, dy, divida_equity, margem_liquida, preco_atual, moeda
            FROM fundamentals_snapshots
            WHERE ticker = ?
            ORDER BY captured_at DESC
            LIMIT ?
            """,
            (ticker, int(limit)),
        ).fetchall()
        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame([dict(row) for row in rows])
        df["captured_at"] = pd.to_datetime(df["captured_at"], errors="coerce")
        return df.sort_values("captured_at")
    finally:
        conn.close()


def get_latest_llm_report(ticker, db_path=DEFAULT_DB_PATH):
    # Recupera apenas o relatório mais recente para leitura rápida.
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            """
            SELECT captured_at, provider, model, report_markdown
            FROM llm_reports
            WHERE ticker = ?
            ORDER BY captured_at DESC
            LIMIT 1
            """,
            (ticker,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()