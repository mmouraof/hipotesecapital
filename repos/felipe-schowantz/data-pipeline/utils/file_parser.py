"""
FileParser — lê transcrições PDF e Excels da pasta uploads/.

Classes:
  FileNameParser       — valida e decompõe o nome do arquivo
  PDFTranscriptParser  — extrai texto de PDFs de transcrição de call de resultados
  ExcelParser          — extrai abas de .xlsx (futuro)
  AudioTranscriber     — transcreve áudio via Whisper API (futuro)

Nota: extração de tabelas financeiras de PDF foi descartada.
      Dados de DRE, BP e CF vêm da API pública da CVM.
"""

import re
import pandas as pd
import pdfplumber
from datetime import date
from pathlib import Path
from typing import Optional

from utils.company_config import FILE_PATTERN, COMPANIES, SHEETS_TO_IGNORE, table_name


# ── FileNameParser ────────────────────────────────────────────────────────────
class FileNameParser:
    """
    Valida e decompõe o nome do arquivo no padrão:
    YYYY-MM-DD_TICKER_PERIOD_TYPE.ext
    Exemplo: 2026-01-12_ASAI3_4T25_transcricao.pdf
    """

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.filename = filepath.name
        self._match   = re.match(FILE_PATTERN, self.filename, re.IGNORECASE)

        if not self._match:
            raise ValueError(
                f"Nome inválido: '{self.filename}'. "
                f"Esperado: YYYY-MM-DD_TICKER_PERIOD_TYPE.ext  "
                f"Exemplo:  2026-01-12_ASAI3_4T25_transcricao.pdf"
            )

    @property
    def reference_date(self) -> date:
        return date.fromisoformat(self._match.group(1))

    @property
    def ticker(self) -> str:
        return self._match.group(2).upper()

    @property
    def period(self) -> str:
        """Período de referência ex: 4T25, 1T26"""
        return self._match.group(3).upper()

    @property
    def doc_type(self) -> str:
        """Tipo do documento ex: transcricao"""
        return self._match.group(4).lower()

    @property
    def extension(self) -> str:
        return self._match.group(5).lower()

    @property
    def company(self) -> Optional[dict]:
        return COMPANIES.get(self.ticker)

    def validate_ticker(self) -> None:
        if self.ticker not in COMPANIES:
            raise ValueError(
                f"Ticker '{self.ticker}' não está em COMPANIES. "
                f"Válidos: {list(COMPANIES.keys())}"
            )

    def __repr__(self):
        return (
            f"FileNameParser("
            f"ticker={self.ticker}, period={self.period}, "
            f"doc_type={self.doc_type}, date={self.reference_date}, "
            f"ext={self.extension})"
        )


# ── PDFTranscriptParser ───────────────────────────────────────────────────────
class PDFTranscriptParser:
    """
    Extrai texto corrido de PDFs de transcrição de call de resultados.
    Retorna um DataFrame por página com o texto extraído.
    """

    def __init__(self, meta: FileNameParser):
        self.meta = meta

    def parse(self) -> dict[str, pd.DataFrame]:
        pages = []
        with pdfplumber.open(self.meta.filepath) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                pages.append({"page": i, "text": text.strip()})

        df = pd.DataFrame(pages)
        df["ticker"]         = self.meta.ticker
        df["period"]         = self.meta.period
        df["reference_date"] = self.meta.reference_date
        df["_extracted_at"]  = pd.Timestamp.utcnow()

        tbl = table_name(
            self.meta.ticker,
            self.meta.period,
            self.meta.doc_type,
            "transcript",
        )
        print(f"[PDF] {self.meta.filename} — {len(df)} páginas → {tbl}")
        return {tbl: df}


# ── ExcelParser ───────────────────────────────────────────────────────────────
class ExcelParser:
    """Extrai abas de arquivos .xlsx. (Futuro)"""

    def __init__(self, meta: FileNameParser):
        self.meta = meta

    def parse(self) -> dict[str, pd.DataFrame]:
        import openpyxl
        wb = openpyxl.load_workbook(self.meta.filepath, data_only=True)
        results = {}

        for sheet_name in wb.sheetnames:
            if sheet_name in SHEETS_TO_IGNORE:
                print(f"[EXCEL] Ignorando aba: {sheet_name}")
                continue

            ws   = wb[sheet_name]
            data = list(ws.values)
            if not data:
                continue

            headers = [str(h) if h is not None else f"col_{i}" for i, h in enumerate(data[0])]
            df = pd.DataFrame(data[1:], columns=headers).dropna(how="all")
            df["ticker"]         = self.meta.ticker
            df["period"]         = self.meta.period
            df["reference_date"] = self.meta.reference_date
            df["_extracted_at"]  = pd.Timestamp.utcnow()

            tbl = table_name(self.meta.ticker, self.meta.period, self.meta.doc_type, sheet_name)
            results[tbl] = df
            print(f"[EXCEL] '{sheet_name}' → {tbl} — {len(df)} linhas")

        return results


# ── AudioTranscriber ──────────────────────────────────────────────────────────
class AudioTranscriber:
    """Transcreve áudio via OpenAI Whisper API. (Futuro)"""

    def __init__(self, meta: FileNameParser):
        self.meta = meta

    def transcribe(self) -> dict[str, pd.DataFrame]:
        import openai
        client = openai.OpenAI()

        with open(self.meta.filepath, "rb") as f:
            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="verbose_json",
            )

        segments = [
            {"segment": i, "start": s.start, "end": s.end, "text": s.text}
            for i, s in enumerate(result.segments)
        ]
        df = pd.DataFrame(segments)
        df["ticker"]         = self.meta.ticker
        df["period"]         = self.meta.period
        df["reference_date"] = self.meta.reference_date
        df["_extracted_at"]  = pd.Timestamp.utcnow()

        tbl = table_name(self.meta.ticker, self.meta.period, self.meta.doc_type, "transcript")
        print(f"[AUDIO] {len(df)} segmentos → {tbl}")
        return {tbl: df}


# ── TXTTranscriptParser ───────────────────────────────────────────────────────
class TXTTranscriptParser:
    """Lê transcrições em .txt e retorna um DataFrame com o conteúdo."""

    def __init__(self, meta: FileNameParser):
        self.meta = meta

    def parse(self) -> dict[str, pd.DataFrame]:
        text = self.meta.filepath.read_text(encoding="utf-8", errors="replace")
        # Divide em chunks de ~2000 chars para simular páginas
        chunk_size = 2000
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

        rows = [{"page": i+1, "text": chunk.strip()} for i, chunk in enumerate(chunks)]
        df = pd.DataFrame(rows)
        df["ticker"]         = self.meta.ticker
        df["period"]         = self.meta.period
        df["reference_date"] = self.meta.reference_date
        df["_extracted_at"]  = pd.Timestamp.utcnow()

        tbl = table_name(self.meta.ticker, self.meta.period, self.meta.doc_type, "transcript")
        print(f"[TXT] {self.meta.filename} — {len(df)} chunks → {tbl}")
        return {tbl: df}


# ── Factory ───────────────────────────────────────────────────────────────────
def get_parser(filepath: Path):
    """Retorna o parser correto baseado no nome e extensão do arquivo."""
    meta = FileNameParser(filepath)
    meta.validate_ticker()

    ext = meta.extension
    if ext in ("mp3", "mp4", "wav"):
        return AudioTranscriber(meta)
    elif ext == "xlsx":
        return ExcelParser(meta)
    elif ext == "pdf":
        return PDFTranscriptParser(meta)
    elif ext == "txt":
        return TXTTranscriptParser(meta)
    else:
        raise ValueError(f"Extensão não suportada: {ext}")
