"""
Configuração central das empresas do portfólio.
Adicionar nova empresa = adicionar uma entrada no dict COMPANIES.
"""

# ── Planilhas/abas a ignorar no crawler ──────────────────────────────────────
SHEETS_TO_IGNORE = {
    "Capa", "Índice", "Index", "Cover",
    "Sumário", "Summary", "Notas", "Notes",
}

# ── Empresas monitoradas ──────────────────────────────────────────────────────
COMPANIES = {
    "ASAI3": {
        "name":         "Assaí Atacadista",
        "cnpj":         "06057223000171",
        "source_type":  "pdf",
        "content_type": "transcript",   # PDF com transcrição de call de resultados
        # TODO: CNPJ não encontrado nem no ITR nem no DFP da CVM (2025).
        # Verificar CNPJ correto na B3 ou usar transcript como fonte primária.
    },
    "PRIO3": {
        "name":         "PetroRio",
        "cnpj":         "10629105000168",
        "source_type":  "pdf",
        "content_type": "financial",    # PDF com DRE, BP, CF em tabelas
    },
    "RENT3": {
        "name":         "Localiza",
        "cnpj":         "16670085000155",
        "source_type":  "pdf",
        "content_type": "financial",
    },
}

# ── Padrão de nome de arquivo ─────────────────────────────────────────────────
# Formato: YYYY-MM-DD_TICKER_PERIOD_TYPE.ext
# Exemplo: 2026-01-12_ASAI3_4T25_transcricao.pdf
#          2026-03-20_RENT3_1T26_transcricao.pdf
FILE_PATTERN = r"^(\d{4}-\d{2}-\d{2})_([A-Z0-9]+)_([A-Z0-9]+)_([a-z]+)\.(pdf|xlsx|mp3|mp4|wav|txt)$"

# ── Nome padronizado de tabela de destino ─────────────────────────────────────
# Padrão: from_site_{ticker}_{period}_{type}_{sheet}
# Exemplo: from_site_asai3_4t25_transcricao_transcript
def table_name(ticker: str, period: str, doc_type: str, sheet: str) -> str:
    sheet_clean = (
        sheet.replace("&", "and")
             .replace(" ", "_")
             .replace("-", "_")
             .lower()
    )
    return f"from_site_{ticker.lower()}_{period.lower()}_{doc_type.lower()}_{sheet_clean}"
