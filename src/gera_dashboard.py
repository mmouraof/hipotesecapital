"""Módulo de geração do dashboard HTML a partir dos dados analisados."""

import json
import logging

logger = logging.getLogger(__name__)


def gerar_dashboard(dados: dict, template_path: str, output_path: str) -> None:
    """Injeta os dados no template HTML e salva o dashboard final.

    Substitui o placeholder __DATA_PLACEHOLDER__ no template pelo JSON
    serializado dos dados e salva o resultado em output_path.

    Args:
        dados: Dicionário completo com todos os ativos e suas análises.
        template_path: Caminho para o arquivo dashboard/template.html.
        output_path: Caminho de saída para o arquivo index.html gerado.
    """
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    dados_json = json.dumps(dados, ensure_ascii=False, indent=2)
    html = template.replace("__DATA_PLACEHOLDER__", dados_json)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info("Dashboard gerado: %s", output_path)
