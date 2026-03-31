"""
Extrator — CVM (Comissão de Valores Mobiliários)
Fonte: dados.cvm.gov.br (pública, sem autenticação)
Coleta: DRE, Balanço Patrimonial (Ativo+Passivo) e Fluxo de Caixa
Fontes tentadas em ordem: ITR (trimestral) → DFP (anual)
Saída:
  - __main__ (teste): CSV bruto em testes/cvm/
  - Airflow:          Parquet em data-lakehouse/bronze/cvm/
"""

import requests
import pandas as pd
import zipfile
import io
from datetime import date
from pathlib import Path

ROOT        = Path(__file__).resolve().parents[2]
BRONZE_PATH = ROOT / "data-lakehouse" / "bronze" / "cvm"
TEST_PATH   = ROOT / "testes" / "cvm"

# CNPJs sem formatação
EMPRESA_CNPJ = {
    "ASAI3": "06057223000171",
    "PRIO3": "10629105000168",
    "RENT3": "16670085000155",
}

# CSVs dentro do ZIP que nos interessam → prefixo de conta CVM
STATEMENT_MAP = {
    "DRE_con":    "3.",   # Demonstração de Resultado
    "BPA_con":    "1.",   # Balanço Patrimonial — Ativo
    "BPP_con":    "2.",   # Balanço Patrimonial — Passivo e PL
    "DFC_MI_con": "6.",   # Fluxo de Caixa (método indireto)
}

CVM_ITR_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/ITR/DADOS/"
CVM_DFP_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/"


def _download_zip(base_url: str, ano: int) -> zipfile.ZipFile:
    """Baixa o ZIP anual da CVM e retorna o objeto ZipFile em memória."""
    doc_type = "itr" if "ITR" in base_url else "dfp"
    url = base_url + f"{doc_type}_cia_aberta_{ano}.zip"
    print(f"[CVM] Baixando {url}")
    resp = requests.get(url, timeout=180)
    resp.raise_for_status()
    return zipfile.ZipFile(io.BytesIO(resp.content))


def _extract_statement(zf: zipfile.ZipFile, key: str) -> pd.DataFrame:
    """Extrai um CSV específico do ZIP pelo prefixo do nome."""
    matches = [n for n in zf.namelist() if key in n]
    if not matches:
        print(f"[CVM] CSV '{key}' não encontrado no ZIP")
        return pd.DataFrame()
    with zf.open(matches[0]) as f:
        df = pd.read_csv(f, sep=";", encoding="latin-1", dtype=str)
    print(f"[CVM] '{matches[0]}' — {len(df)} linhas brutas")
    return df


def _filter(df: pd.DataFrame, tickers: list[str], conta_prefix: str) -> pd.DataFrame:
    """Filtra por empresa e prefixo de conta contábil."""
    cnpjs = [EMPRESA_CNPJ[t] for t in tickers if t in EMPRESA_CNPJ]
    df["CNPJ_CIA"] = df["CNPJ_CIA"].str.replace(r"\D", "", regex=True)
    return df[
        df["CNPJ_CIA"].isin(cnpjs) &
        df["CD_CONTA"].str.startswith(conta_prefix)
    ].copy()


def _fetch_from_source(base_url: str, tickers: list[str], source_label: str) -> list[pd.DataFrame]:
    """Tenta baixar e filtrar dados de uma fonte CVM (ITR ou DFP)."""
    ano = date.today().year
    try:
        zf = _download_zip(base_url, ano)
    except Exception as e:
        print(f"[CVM] {source_label} {ano} falhou ({e}), tentando {ano - 1}")
        try:
            zf = _download_zip(base_url, ano - 1)
        except Exception as e2:
            print(f"[CVM] {source_label} {ano - 1} também falhou: {e2}")
            return []

    frames = []
    for key, prefix in STATEMENT_MAP.items():
        df_raw = _extract_statement(zf, key)
        if df_raw.empty:
            continue
        df_filt = _filter(df_raw, tickers, prefix)
        if df_filt.empty:
            continue
        df_filt["_statement"] = key
        df_filt["_source"] = source_label
        frames.append(df_filt)
    return frames


def extract_cvm(tickers: list[str], out_path: Path = BRONZE_PATH) -> None:
    """
    Busca DRE + BP + CF para cada ticker.
    Tenta ITR primeiro; tickers sem dados no ITR são buscados no DFP.
    """
    all_frames = []

    # 1. ITR — dados trimestrais
    itr_frames = _fetch_from_source(CVM_ITR_URL, tickers, "ITR")
    all_frames.extend(itr_frames)

    # Descobre quais tickers não vieram no ITR
    found_cnpjs = set()
    for df in itr_frames:
        found_cnpjs.update(df["CNPJ_CIA"].unique())

    missing = [t for t in tickers if EMPRESA_CNPJ.get(t) not in found_cnpjs]
    if missing:
        print(f"[CVM] Tickers sem dados no ITR, buscando no DFP: {missing}")
        dfp_frames = _fetch_from_source(CVM_DFP_URL, missing, "DFP")
        all_frames.extend(dfp_frames)

    if not all_frames:
        raise RuntimeError("[CVM] Nenhum dado coletado.")

    result = pd.concat(all_frames, ignore_index=True)
    result["_extracted_at"] = pd.Timestamp.utcnow()

    out_path.mkdir(parents=True, exist_ok=True)
    out_file = out_path / f"cvm_{date.today().isoformat()}.parquet"
    result.to_parquet(out_file, index=False)
    print(f"[CVM] {len(result)} linhas salvas em {out_file}")


if __name__ == "__main__":
    TEST_PATH.mkdir(parents=True, exist_ok=True)

    for source_label, base_url in [("ITR", CVM_ITR_URL), ("DFP", CVM_DFP_URL)]:
        ano = date.today().year
        try:
            zf = _download_zip(base_url, ano)
        except Exception:
            try:
                zf = _download_zip(base_url, ano - 1)
            except Exception as e:
                print(f"[CVM] {source_label} indisponível: {e}")
                continue

        for key, _ in STATEMENT_MAP.items():
            df = _extract_statement(zf, key)
            if not df.empty:
                out = TEST_PATH / f"cvm_raw_{source_label}_{key}_{date.today().isoformat()}.csv"
                df.to_csv(out, index=False)
                print(f"[CVM] CSV salvo em {out}")
