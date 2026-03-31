"""
Extrator — Banco Central do Brasil (BCB)
Fonte: api.bcb.gov.br (pública, sem autenticação)
Saída: Parquet em data-lakehouse/bronze/bcb/
"""

import time
import pandas as pd
from bcb import sgs
from datetime import date, timedelta
from pathlib import Path

# ── Séries do Banco Central ──────────────────────────────────────────────────
BCB_SERIES = {
    "selic_meta":        432,   # Taxa SELIC (% a.a.)
    "ipca_mensal":       433,   # IPCA variação mensal (%)
    "desemprego":        24369, # Taxa de desemprego PNAD (%)
    "cambio_usd_brl":    1,     # Taxa de câmbio USD/BRL (venda)
    "balanco_comercial": 22707, # Saldo da balança comercial (US$ milhões)
}

BRONZE_PATH = Path(__file__).resolve().parents[2] / "data-lakehouse" / "bronze" / "bcb"
TEST_PATH   = Path(__file__).resolve().parents[2] / "testes" / "bcb"
MAX_RETRIES = 3


def _fetch_serie(name: str, codigo: int, start: str, end: str) -> pd.DataFrame:
    """Busca uma série do BCB com até MAX_RETRIES tentativas."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"[BCB] Tentativa {attempt}/{MAX_RETRIES} — {name} (série {codigo})")
            df = sgs.get({name: codigo}, start=start, end=end)
            print(f"[BCB] {name} — {len(df)} registros coletados")
            return df
        except Exception as e:
            print(f"[BCB] ERRO tentativa {attempt}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(2)
    print(f"[BCB] {name} falhou após {MAX_RETRIES} tentativas — pulando.")
    return None


def extract_bcb(lookback_days: int = 365, out_path: Path = BRONZE_PATH) -> None:
    """
    Coleta as séries macro do BCB dos últimos `lookback_days` dias
    e salva em Parquet.
    """
    start = (date.today() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    end   = date.today().strftime("%Y-%m-%d")
    print(f"[BCB] Coletando de {start} até {end}")

    frames = []
    for name, codigo in BCB_SERIES.items():
        df = _fetch_serie(name, codigo, start, end)
        if df is not None:
            frames.append(df)

    if not frames:
        raise RuntimeError("[BCB] Nenhuma série coletada. Verifique a conexão.")

    result = pd.concat(frames, axis=1).reset_index()
    result.rename(columns={"index": "data", "Date": "data"}, inplace=True)
    result["_extracted_at"] = pd.Timestamp.utcnow()
    print(f"[BCB] DataFrame final: {result.shape[0]} linhas x {result.shape[1]} colunas")
    print(f"[BCB] Colunas: {list(result.columns)}")

    out_path.mkdir(parents=True, exist_ok=True)
    parquet_file = out_path / f"bcb_{date.today().isoformat()}.parquet"
    result.to_parquet(parquet_file, index=False)
    print(f"[BCB] Salvo em {parquet_file}")


if __name__ == "__main__":
    TEST_PATH.mkdir(parents=True, exist_ok=True)
    extract_bcb(out_path=TEST_PATH)
