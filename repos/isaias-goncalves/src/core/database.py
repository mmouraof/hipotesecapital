import sqlite3
import os
import json
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
from utils.logger import logger

class DatabaseManager:
    """
    Gerenciador do banco de dados SQLite com suporte a versionamento (migrations).
    Abstrai toda a persistência de dados do terminal analítico.
    """
    
    def __init__(self, db_path: str = "database.db", migrations_dir: str = "migrations") -> None:
        self.db_path = db_path
        self.migrations_dir = migrations_dir
        self._initialize_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Cria e retorna uma conexão com suporte a chaves estrangeiras."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize_db(self) -> None:
        """Inicializa o banco e aplica migrações pendentes."""
        if not os.path.exists(self.db_path):
            logger.info(f"DB: Criando novo banco de dados em {self.db_path}")
        
        self._apply_migrations()

    def _apply_migrations(self) -> None:
        """Sistema de versionamento manual via arquivos .sql."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT MAX(version) FROM schema_version")
                current_version = cursor.fetchone()[0] or 0
            except sqlite3.OperationalError:
                current_version = 0

            if not os.path.exists(self.migrations_dir):
                os.makedirs(self.migrations_dir)
                return

            migration_files = sorted([f for f in os.listdir(self.migrations_dir) if f.endswith(".sql")])
            
            for file in migration_files:
                version = int(file.split("_")[0])
                if version > current_version:
                    logger.info(f"DB: Aplicando migração de banco de dados: {file}")
                    with open(os.path.join(self.migrations_dir, file), "r", encoding="utf-8") as f:
                        sql = f.read()
                        conn.executescript(sql)
            
            conn.commit()
        except Exception as e:
            logger.error(f"DB: Erro ao aplicar migrações: {e}")
            conn.rollback()
        finally:
            conn.close()

    def _generate_news_hash(self, title: str) -> str:
        """Gera um hash único para o título da notícia."""
        return hashlib.md5(title.encode('utf-8')).hexdigest()

    def save_ticker_run(self, ticker: str, data: Dict[str, Any], analysis: Dict[str, Any], model_used: str) -> None:
        """Persiste uma rodada completa de análise."""
        conn = self._get_connection()
        try:
            with conn:
                cadastral = data.get("cadastral", {})
                conn.execute("""
                    INSERT INTO companies (ticker, name, sector, industry, business_summary, last_updated)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(ticker) DO UPDATE SET
                        name=excluded.name, sector=excluded.sector, industry=excluded.industry,
                        business_summary=excluded.business_summary, last_updated=CURRENT_TIMESTAMP
                    WHERE (julianday('now') - julianday(last_updated)) > 7;
                """, (ticker, cadastral.get("nome"), cadastral.get("setor"), cadastral.get("segmento"), cadastral.get("resumo")))

                indicators = data.get("market_indicators", {})
                conn.execute("""
                    INSERT INTO market_data (ticker, price, p_l, roe, dy, net_margin, debt_ebitda)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (ticker, indicators.get("preco_atual"), indicators.get("p_l"), indicators.get("roe"), 
                      indicators.get("dy"), indicators.get("margem_liquida"), indicators.get("divida_ebitda")))

                for news_item in data.get("news", []):
                    title = news_item.get("title", "")
                    conn.execute("""
                        INSERT OR IGNORE INTO news (ticker, title, link, publisher, news_hash)
                        VALUES (?, ?, ?, ?, ?)
                    """, (ticker, title, news_item.get("link"), news_item.get("publisher"), self._generate_news_hash(title)))

                sentiment = analysis.get("sentimento_noticias", {})
                conn.execute("""
                    INSERT INTO ai_analyses (ticker, model_used, business_summary_ai, indicator_analysis, 
                                          sentiment_class, sentiment_analysis, investigative_questions)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (ticker, model_used, analysis.get("resumo_negocio"), analysis.get("analise_indicadores"),
                      sentiment.get("classe"), sentiment.get("analise"), json.dumps(analysis.get("perguntas_investigativas", []))))
        except Exception as e:
            logger.error(f"DB: Erro ao salvar dados coletados de {ticker} no banco: {e}")
        finally:
            conn.close()

    def get_available_analysis_dates(self, ticker: str) -> List[str]:
        """Retorna os timestamps de todas as análises salvas para o ticker."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT analyzed_at FROM ai_analyses 
                WHERE ticker = ? ORDER BY analyzed_at DESC
            """, (ticker,))
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_full_run_by_timestamp(self, ticker: str, timestamp: str) -> Optional[Dict[str, Any]]:
        """Reconstrói uma execução completa baseada em um timestamp específico."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # 1. Dados da Análise de IA
            cursor.execute("SELECT * FROM ai_analyses WHERE ticker = ? AND analyzed_at = ?", (ticker, timestamp))
            row_ai = cursor.fetchone()
            if not row_ai: return None
            row_ai = dict(row_ai)

            # 2. Dados Cadastrais (Perfil da época ou atual mais próximo)
            cursor.execute("SELECT * FROM companies WHERE ticker = ?", (ticker,))
            row_comp = dict(cursor.fetchone())

            # 3. Dados de Mercado (Mais próximos da análise)
            cursor.execute("""
                SELECT * FROM market_data 
                WHERE ticker = ? AND collected_at <= ? 
                ORDER BY collected_at DESC LIMIT 1
            """, (ticker, timestamp))
            row_mkt = dict(cursor.fetchone())

            # 4. Notícias (Filtradas para o período)
            cursor.execute("""
                SELECT title, link, publisher FROM news 
                WHERE ticker = ? AND (rowid IN (SELECT rowid FROM news WHERE ticker = ? LIMIT 10))
            """, (ticker, ticker)) # Simplificado: pegamos as 10 últimas vinculadas
            news_rows = [dict(r) for r in cursor.fetchall()]

            # Reconstrói os dicionários 'data' e 'analysis'
            data = {
                "cadastral": {
                    "nome": row_comp["name"], "setor": row_comp["sector"], 
                    "segmento": row_comp["industry"], "resumo": row_comp["business_summary"]
                },
                "market_indicators": {
                    "preco_atual": row_mkt["price"], "p_l": row_mkt["p_l"], "roe": row_mkt["roe"],
                    "dy": row_mkt["dy"], "margem_liquida": row_mkt["net_margin"], "divida_ebitda": row_mkt["debt_ebitda"]
                },
                "news": news_rows
            }
            
            analysis = {
                "resumo_negocio": row_ai["business_summary_ai"],
                "analise_indicadores": row_ai["indicator_analysis"],
                "sentimento_noticias": {
                    "classe": row_ai["sentiment_class"],
                    "analise": row_ai["sentiment_analysis"]
                },
                "perguntas_investigativas": json.loads(row_ai["investigative_questions"])
            }

            return {"data": data, "analysis": analysis, "collected_at": row_mkt["collected_at"]}
        except Exception as e:
            logger.error(f"DB: Erro ao recuperar histórico: {e}")
            return None
        finally:
            conn.close()

    def get_ticker_history(self, ticker: str, limit: int = 30) -> pd.DataFrame:
        """Retorna série temporal de indicadores."""
        conn = self._get_connection()
        try:
            query = "SELECT * FROM market_data WHERE ticker = ? ORDER BY collected_at ASC LIMIT ?"
            return pd.read_sql_query(query, conn, params=(ticker, limit))
        finally:
            conn.close()
