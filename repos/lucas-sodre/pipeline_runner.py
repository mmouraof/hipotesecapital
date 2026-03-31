import argparse
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from data.news_sources import get_news_with_fallback
from data.pipeline_db import (
    DEFAULT_DB_PATH,
    finish_pipeline_run,
    init_db,
    insert_fundamental_snapshot,
    insert_llm_report,
    insert_news_snapshots,
    start_pipeline_run,
    upsert_company,
)
from data.tickers import get_all_tickers
from data.yahoo_raw import get_info_ticker, get_price_history
from llm.report_generator import generate_structured_report_with_llm, summarize_price_data
from utils.news_parser import extract_news_item


def _get_gemini_api_key():
    # Chave usada apenas quando geração de relatório estiver habilitada.
    return os.getenv("GOOGLE_API_KEY")


def _collect_ticker_payload(ticker, collect_news, reports_enabled, history_period, api_key):
    # Coleta dados de um ticker de forma isolada para execução paralela.
    try:
        info_dict = get_info_ticker(ticker) or {}
        if not info_dict:
            return {"ticker": ticker, "ok": False, "error": "missing_info"}

        parsed_news_items = []
        if collect_news:
            # Notícias são opcionais para permitir modo rápido no pipeline.
            raw_news = get_news_with_fallback(ticker=ticker, min_results=5, max_results=15)
            parsed_news_items = [extract_news_item(item) for item in raw_news]

        report_text = None
        if reports_enabled:
            # Relatório LLM é gerado sob demanda e pode ser desligado por flag.
            data = get_price_history(ticker, history_period)
            price_summary = summarize_price_data(data)
            report_text, report_error = generate_structured_report_with_llm(
                ticker=ticker,
                info_dict=info_dict,
                period_label=history_period,
                price_summary=price_summary,
                parsed_news=parsed_news_items,
                api_key=api_key,
            )
            if report_error:
                report_text = None

        return {
            "ticker": ticker,
            "ok": True,
            "info_dict": info_dict,
            "parsed_news_items": parsed_news_items,
            "report_text": report_text,
        }
    except Exception as ex:
        return {"ticker": ticker, "ok": False, "error": str(ex)}


def run_pipeline(
    tickers,
    db_path=DEFAULT_DB_PATH,
    generate_reports=True,
    history_period="6mo",
    collect_news=True,
    max_workers=8,
    progress_every=25,
):
    # Inicializa banco e abre a execução atual.
    init_db(db_path)
    run_id = start_pipeline_run(total_tickers=len(tickers), db_path=db_path)

    processed = 0
    errors = 0
    api_key = _get_gemini_api_key()
    reports_enabled = bool(generate_reports and api_key)

    # Registra todos os tickers no cadastro logo no início da rodada.
    for ticker in tickers:
        upsert_company(ticker=ticker, info_dict={}, db_path=db_path)

    # Garante pelo menos um worker para evitar configuração inválida.
    workers = max(1, int(max_workers))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                _collect_ticker_payload,
                ticker,
                collect_news,
                reports_enabled,
                history_period,
                api_key,
            ): ticker
            for ticker in tickers
        }

        for future in as_completed(futures):
            # Persistência fica no fluxo principal para simplificar concorrência no SQLite.
            payload = future.result()
            ticker = payload["ticker"]

            if not payload.get("ok"):
                errors += 1
                processed += 1
                continue

            info_dict = payload["info_dict"]
            parsed_news_items = payload.get("parsed_news_items", [])
            report_text = payload.get("report_text")

            upsert_company(ticker=ticker, info_dict=info_dict, db_path=db_path)
            insert_fundamental_snapshot(run_id=run_id, ticker=ticker, info_dict=info_dict, db_path=db_path)

            if collect_news and parsed_news_items:
                insert_news_snapshots(run_id=run_id, ticker=ticker, parsed_news_items=parsed_news_items, db_path=db_path)

            if reports_enabled and report_text:
                insert_llm_report(
                    run_id=run_id,
                    ticker=ticker,
                    provider="gemini",
                    model="gemini-flash-latest",
                    report_markdown=report_text,
                    db_path=db_path,
                )

            processed += 1

            if progress_every and processed % int(progress_every) == 0:
                print(f"[pipeline] progresso: {processed}/{len(tickers)} tickers processados")

    status = "finished" if errors == 0 else "finished_with_errors"
    notes = None if reports_enabled else "LLM report generation skipped (missing GOOGLE_API_KEY or disabled)."
    finish_pipeline_run(
        run_id=run_id,
        processed_tickers=processed,
        error_count=errors,
        status=status,
        notes=notes,
        db_path=db_path,
    )

    return {
        "run_id": run_id,
        "total": len(tickers),
        "processed": processed,
        "errors": errors,
        "reports_enabled": reports_enabled,
    }


def _parse_args():
    # Flags para controlar performance e escopo da execução.
    parser = argparse.ArgumentParser(description="Pipeline recorrente de coleta B3 com persistência SQLite")
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="Caminho do banco SQLite")
    parser.add_argument("--tickers", default="", help="Lista de tickers separados por vírgula")
    parser.add_argument("--limit", type=int, default=0, help="Limite de tickers processados")
    parser.add_argument("--no-llm", action="store_true", help="Não gerar relatórios LLM")
    parser.add_argument("--no-news", action="store_true", help="Não coletar notícias (modo mais rápido)")
    parser.add_argument("--workers", type=int, default=8, help="Número de workers para coleta paralela")
    parser.add_argument("--progress-every", type=int, default=25, help="Intervalo de log de progresso")
    parser.add_argument("--period", default="6mo", help="Período para resumo de preço no relatório")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    if args.tickers.strip():
        tickers = [item.strip().upper() for item in args.tickers.split(",") if item.strip()]
    else:
        tickers = get_all_tickers()

    if not tickers:
        raise RuntimeError("Nenhum ticker foi coletado. Verifique a fonte de tickers e tente novamente.")

    print(f"[pipeline] total de tickers carregados: {len(tickers)}")

    if args.limit and args.limit > 0:
        tickers = tickers[: args.limit]

    result = run_pipeline(
        tickers=tickers,
        db_path=args.db,
        generate_reports=not args.no_llm,
        history_period=args.period,
        collect_news=not args.no_news,
        max_workers=args.workers,
        progress_every=args.progress_every,
    )
    print(result)