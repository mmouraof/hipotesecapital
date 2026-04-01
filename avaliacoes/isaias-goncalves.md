# Avaliacao - Isaias Goncalves

**Repositorio:** https://github.com/isaiasgoncalves/CaseStudyFinance
**Commits:** 68 (27/mar a 30/mar)

---

## 1. Qualidade do Prompt / LLM Engineering (Fase 1)

**Nota do criterio: 4.5/5**

O `InvestmentAnalyzer` usa OpenAI GPT-4o-mini com prompt calibrado para value investing. O prompt inclui:
- Persona de analista fundamentalista
- Dados cadastrais, indicadores de mercado e manchetes de noticias
- Variaveis de template dinamicas (`{setor}`) preenchidas pelo codigo
- Instrucao para classificacao de sentimento baseada em impacto fundamental
- Output em JSON estruturado com `response_format` do OpenAI

**Pontos positivos:**
- Prompt especifico com perspectiva de value investing
- Output JSON deterministico (temperature baixa)
- Graceful degradation: erros retornam dicionario de erro em vez de exceptions
- Separacao clara entre coleta e analise

**Pontos negativos:**
- Sem instrucao anti-alucinacao explicita (ex: nao fabrique dados)
- Poderia incluir instrucoes sobre downside protection e qualidade do negocio mais explicitamente

---

## 2. Coleta Automatizada e Fontes de Dados (Fase 1)

**Nota do criterio: 4.5/5**

O `DataCollector` e o mais robusto entre os candidatos em termos de resiliencia.

**Fontes utilizadas:**
- yfinance com sessao `curl_cffi` (impersonate="chrome") - anti-blocking
- Yahoo Finance News como fonte primaria
- Google News RSS como fallback
- Filtragem temporal configuravel (NEWS_MAX_AGE_DAYS)

**Indicadores cobertos:** P/L (trailingPE), ROE (returnOnEquity), Divida/EBITDA (debtToEbitda), Margem Liquida (profitMargins), DY (dividendYield) - todos os 5 solicitados.

**Diferenciais tecnicos:**
- Anti-blocking com curl_cffi + Chrome impersonation + verify=False
- Dual-source news com deduplicacao (compara primeiros 30 chars do titulo)
- Filtragem temporal de noticias (suporta timestamp unix, ISO, RFC)
- Validacao de ticker (`if 'symbol' not in info`)
- Historico de precos como metodo separado configuravel

**Pontos negativos:**
- Fontes limitadas ao yfinance (sem Fundamentus, Status Invest, CVM)
- verify=False em producao e um risco de seguranca

---

## 3. Interface e Usabilidade (Fase 1)

**Nota do criterio: 5/5**

O **unico candidato a entregar um dashboard interativo completo** com deploy via Docker.

**Funcionalidades:**
- Input de ticker com geracao de relatorio sob demanda
- Visualizacao de analises historicas com seletor de datas
- Grafico de retornos com janelas selecionaveis (12M, 6M, YTD, MTD)
- Metricas em grid de 3 colunas
- Noticias com analise de sentimento do LLM
- Secao de briefing com resumo, indicadores, sintese de noticias e perguntas
- Branding customizado "Hipotese Capital"
- Streamlit session state para persistencia de resultados

**Deploy:**
- Dockerfile + docker-compose.yml
- DEPLOY_GUIDE.md separado com instrucoes
- Suporta execucao local e Docker

---

## 4. Modelagem do Banco de Dados e Pipeline (Fase 2)

**Nota do criterio: 5/5**

A modelagem mais sofisticada em termos de boas praticas de engenharia de software.

**Estrutura SQLite com migracoes:**
- `companies` (permanente) - perfil corporativo
- `market_data` (temporal) - indicadores por data
- `news` (temporal) - com hash MD5 para deduplicacao
- `ai_analyses` (temporal) - resultados do LLM separados
- `schema_version` - controle de migracoes

**Pipeline (`AnalyticalOrchestrator`):**
- Decide entre buscar dados do banco ou da API
- Live pipeline: coleta -> analise -> persistencia
- Historico reconstruivel por timestamp
- Expiracao de 7 dias para dados de empresa

**Pontos positivos:**
- **Sistema de migracoes** com arquivos SQL versionados (`001_initial_schema.sql`)
- MD5 hash para deduplicacao de noticias
- Separacao entre dados de mercado e analises LLM em tabelas distintas
- `DatabaseManager` com rollback e logging
- Foreign keys e transacoes
- Testes unitarios para o banco (`test_database.py`)

---

## 5. Tratamento de Erros e Robustez (Fase 2)

**Nota do criterio: 5/5**

O melhor tratamento de erros entre todos os candidatos.

**Cobertura dos 3 casos obrigatorios:**
- API fora do ar: curl_cffi com impersonation, fallback Yahoo->Google News, try/except com logging em toda coleta
- Ticker invalido: `if 'symbol' not in info` retorna dict vazio com log de erro especifico
- Resposta LLM fora do formato: `LLMGenerationError` exception customizada, graceful degradation com `llm_error` no resultado

**Pontos positivos:**
- **Logging customizado** (utils/logger.py) em todo o codigo
- Exception customizada `LLMGenerationError` com `raw_response`
- Orchestrator decide entre live e historico com fallback
- Debug info retornado no `BriefingResult` (sources, news_count, etc.)
- **Testes unitarios** (test_analyzer.py, test_collector.py, test_database.py)
- pytest.ini configurado

**Pontos negativos:**
- Sem retry com backoff explicito para APIs

---

## 6. Documentacao e Versionamento (Fases 1 e 2)

**Nota do criterio: 5/5**

**README:**
- Muito bem escrito e detalhado (conforme observado)
- Explica arquitetura com pipeline em 4 estagios
- Documenta anti-blocking measures e decisoes tecnicas
- Setup local E Docker com instrucoes claras
- GEMINI.md adicional sobre integracao de IA
- DEPLOY_GUIDE.md separado
- `.envexample` com template
- Licenca MIT

**Versionamento:**
- **68 commits** - o maior numero entre todos os candidatos
- Progressao clara: fase 1 -> refatoracao -> banco -> migracoes -> Docker -> README
- Mensagens descritivas em portugues

---

## 7. Visao Arquitetural e RAG (Fase 3)

Nao implementado explicitamente, porem o `GEMINI.md` sugere reflexao sobre integracao de IA.

---

## Nota Final: 5/5

O candidato demonstrou **dominio tecnico completo** nas fases obrigatorias. O codigo e limpo, bem estruturado, com separacao de responsabilidades clara (Collector, Analyzer, Orchestrator, DatabaseManager). O tratamento de erros e o mais robusto (exceptions customizadas, logging, testes unitarios). O banco de dados tem migracoes versionadas e deduplicacao por hash. O dashboard e completo e deployavel via Docker.

A unica lacuna e a limitacao de fontes de dados (basicamente yfinance) e a ausencia de RAG. Mas a qualidade da engenharia compensa amplamente.

**Diferenciais:** 68 commits, testes unitarios, migracoes de banco, Docker deploy, exception customizada para LLM, anti-blocking com curl_cffi, unico com dashboard interativo completo
**Lacunas:** Fontes limitadas ao yfinance, sem RAG, verify=False em producao
