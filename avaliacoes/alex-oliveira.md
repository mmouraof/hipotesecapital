Avaliacao - Joao Felipe
Repositorio: https://github.com/joaoleal02/DashboardCR
Commits: 6 (23/mar a 26/mar)
---
1. Qualidade do Prompt / LLM Engineering (Fase 1)
Nota do criterio: 5/5
O melhor prompt entre todos os candidatos. O SYSTEM_PROMPT em `prompts.py` reflete claramente a otica de value investing:
> "Think like a value-oriented analyst. Prioritize business quality, downside protection, capital structure, profitability quality, and what could go wrong."
Pontos positivos:
Instrucoes explicitas sobre value investing: business quality, downside protection, capital structure
"Distinguish factual inputs from analytical inference" - separacao entre fato e opiniao
"Never fabricate facts that are not present in the input" - anti-alucinacao
"Avoid generic finance filler and motivational language" - foco em utilidade
"If a field is unavailable, acknowledge the gap and reason around it" - tratamento de lacunas
Output em JSON estruturado com schema definido
Funcoes auxiliares de formatacao (`format_metric_value`, `safe_text`) para sanitizar input
Classificacao de noticias com sentimento e rationale
Pontos negativos:
Prompt em ingles (menor relevancia para analistas brasileiros, mas tecnicamente correto)
---
2. Coleta Automatizada e Fontes de Dados (Fase 1)
Nota do criterio: 4.5/5
A maior diversificacao de APIs publicas entre os candidatos, com collectors separados por responsabilidade.
Fontes utilizadas:
B3 company registry API (dados cadastrais)
Yahoo Finance (fundamentals: P/L, ROE, margens, DY, EBITDA)
CVM (setor, descricao, metricas contabeis)
Status Invest API (precos e dividendos)
Google News RSS (noticias recentes)
Indicadores cobertos: P/L, ROE, Divida Liq./EBITDA, Margem Liquida, DY - todos os 5.
Arquitetura de coleta:
`CompanyDataCollector` - perfil corporativo via API publica
`MarketDataCollector` - indicadores via yfinance
`NewsDataCollector` - noticias com fallback
`public_api.py` - wrapper para APIs publicas (B3, CVM)
Fallback entre fontes com merge de dados
Pontos positivos:
Collectors desacoplados por responsabilidade
Merge de perfil com fallbacks (`_merge_company_profile`)
"Missing data displays as 'Unavailable' rather than causing failures"
---
3. Interface e Usabilidade (Fase 1)
Nota do criterio: 4/5
Dashboard Streamlit funcional com:
Seletor de ticker (universo limitado a 10 ativos)
Geracao de briefing sob demanda
Grafico de retornos com janelas (12M, 6M, YTD, MTD)
Metricas em grid
Noticias com analise de sentimento
Session state para persistencia
Pontos negativos:
Universo de tickers hardcoded (10 ativos)
Sem historico de analises
Sem banco de dados (conforme observado: "sem mencao ao banco de dados")
---
4. Modelagem do Banco de Dados e Pipeline (Fase 2)
Nota do criterio: 1/5
Nao ha banco de dados implementado. O pipeline e stateless - cada execucao busca dados frescos e nao persiste nada. Nao ha historico, nao ha snapshots, nao ha tabelas.
O candidato entregou apenas a Fase 1. A Fase 2 esta ausente.
---
5. Tratamento de Erros e Robustez (Fase 2)
Nota do criterio: 3.5/5
Cobertura dos 3 casos obrigatorios:
API fora do ar: Try/except em cada collector com retorno de valores padrao
Ticker invalido: Validacao via `ticker_universe.py` (lista fechada)
Resposta LLM fora do formato: `LLMGenerationError` com `raw_response`, tratado no `BriefingService`
Pontos positivos:
Exception para LLM (`LLMGenerationError`)
Debug info completo no `BriefingResult` (sources, news_count, llm_configured, etc.)
"Application remains functional even if LLM processing encounters errors"
`schemas.py` para validacao do output LLM
Pontos negativos:
Sem logging (usa print implicito do Streamlit)
Sem retry/backoff
---
6. Documentacao e Versionamento (Fases 1 e 2)
Nota do criterio: 2/5
README:
Descricao clara do escopo da Fase 1
Lista de tickers suportados e fontes de dados
Setup instructions basico
Design notes sobre graceful degradation
Versionamento:
Apenas 6 commits - o menor numero entre todos os candidatos
Historico muito condensado, dificil rastrear evolucao
Parece ter sido desenvolvido localmente e pushado em poucos blocos
Mensagens descritivas mas poucas
---
7. Visao Arquitetural e RAG (Fase 3)
Nao implementado.
---
8. Resultado da Execucao (01/abr/2026)
Ambiente: Python 3.13, Windows 11, OpenAI API key
Instalacao: `pip install -r requirements.txt` — sucesso sem erros
Coleta de dados: EXCELENTE
B3 Listed Companies API: retorna dados cadastrais (nome, setor, segmento, descricao)
CVM Open Data: dados contabeis
Status Invest API: precos e dividendos
yfinance: fundamentals (P/L 5.73, ROE 28.18%, Net Debt/EBITDA 1.60, Net Margin 22.13%, DY 803%)
Google News RSS: 5 noticias recentes com links
Debug info rastreia source de cada metrica: `metric_sources` com status `direct`/`fallback`
LLM com modelo correto (gpt-4o-mini): FUNCIONAL
Gera JSON estruturado com 4 campos: business_summary, fundamentals_interpretation, news_analysis (com per-item sentiment + rationale), analyst_questions
Qualidade da analise alta: interpreta P/L, ROE, alavancagem, DY, margem liquida
Sentimento de noticias individual com justificativa
LLM com modelo do .env (gpt-5.4-mini): FALHA
`.env` e `.env.example` ambos definem `OPENAI_MODEL=gpt-5.4-mini`
Este modelo NAO EXISTE na API da OpenAI → resposta vazia
Erro: `The LLM response was not valid JSON`
`llm_report: None`, `llm_error` preenchido
Graceful degradation funciona: dados de mercado e noticias ainda exibidos, apenas LLM ausente
Banco de dados: AUSENTE (confirmado)
Pipeline e completamente stateless
Sem persistencia de historico
---
Nota Final: 3/5
(Confirmado em execucao em 01/abr/2026)
O candidato demonstrou excelente qualidade de prompt engineering - o melhor entre todos os avaliados, com clara compreensao da otica de value investing. A arquitetura de codigo e limpa com boa separacao de responsabilidades (collectors, services, schemas). A coleta de dados e diversificada e funcional com 5 APIs publicas.
Execucao confirmou: coleta de dados funciona perfeitamente com 5 fontes. LLM funciona com modelo correto (gpt-4o-mini) e produz analises de alta qualidade. Porem, o `.env` e `.env.example` ambos definem `gpt-5.4-mini` (modelo inexistente), tornando o LLM inoperante out of the box. A graceful degradation funciona corretamente.
A ausencia completa de banco de dados (Fase 2) permanece o gap mais significativo. O historico de apenas 6 commits sugere desenvolvimento condensado.
Diferenciais: Melhor prompt de value investing, arquitetura limpa de collectors, 5 fontes de dados diferentes, LLMGenerationError, debug_info com metric_sources
Lacunas: Sem banco de dados (Fase 2 ausente), modelo LLM inexistente no .env (gpt-5.4-mini), apenas 6 commits, sem logging, universo de tickers hardcoded
