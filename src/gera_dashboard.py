"""Módulo de geração do dashboard HTML a partir dos dados analisados."""

import json
import logging
import os

logger = logging.getLogger(__name__)


def gerar_dashboard(dados: dict, template_path: str, output_path: str, db_path: str | None = None) -> None:
    """Injeta os dados no template HTML e salva o dashboard final.

    Substitui o placeholder __DATA_PLACEHOLDER__ no template pelo JSON
    serializado dos dados e salva o resultado em output_path.

    Se db_path for fornecido, enriquece cada ativo com seu histórico de
    execuções anteriores e adiciona a lista de datas disponíveis no banco.

    Args:
        dados: Dicionário completo com todos os ativos e suas análises.
        template_path: Caminho para o arquivo dashboard/template.html.
        output_path: Caminho de saída para o arquivo index.html gerado.
        db_path: Caminho opcional para o banco SQLite. Se None ou inexistente,
                 o campo historico será uma lista vazia para cada ativo.
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    import database

    # Enriquece com dados históricos se o banco estiver disponível
    datas_disponiveis: list[str] = []
    if db_path and os.path.exists(db_path):
        try:
            datas_disponiveis = database.listar_datas_execucao(db_path)
        except Exception as e:
            logger.warning("Não foi possível listar datas do banco: %s", e)

    dados["datas_disponiveis"] = datas_disponiveis

    ativos = dados.get("ativos", {})
    data_atual = dados.get("data_geracao", "")
    historico_completo: dict[str, list] = {}

    for ticker, ativo in ativos.items():
        historico: list[dict] = []
        hist_completo: list[dict] = []

        if db_path and os.path.exists(db_path):
            try:
                historico = database.buscar_historico_ticker(db_path, ticker)
                historico = [h for h in historico if h["data"] != data_atual]
            except Exception as e:
                logger.warning("[%s] Não foi possível buscar histórico: %s", ticker, e)
            try:
                hist_completo = database.buscar_historico_completo_ticker(db_path, ticker)
                hist_completo = [h for h in hist_completo if h["data"] != data_atual]
            except Exception as e:
                logger.warning("[%s] Não foi possível buscar histórico completo: %s", ticker, e)

        ativo["historico"] = historico
        historico_completo[ticker] = hist_completo

    dados["historico_completo"] = historico_completo

    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    dados_json = json.dumps(dados, ensure_ascii=False, indent=2)
    html = template.replace("__DATA_PLACEHOLDER__", dados_json)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info("Dashboard gerado: %s", output_path)
