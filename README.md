# Resumo Comparativo - Avaliacoes Case DS&AI

## Ranking Final

| # | Candidato | Nota | Prompt/LLM | Fontes | Interface | Banco/Pipeline | Erros | Doc/Git | Diferencial |
|---|-----------|------|------------|--------|-----------|---------------|-------|---------|-------------|
| 1 | **Isaias Goncalves** | **5/5** | 4.5 | 4.5 | 5 | 5 | 5 | 5 | Dashboard interativo + deploy ao vivo, testes, Docker, migracoes |
| 2 | **Felipe Schowantz** | **4/5** | 3.5 | 5 | 4 | 3.5 | 3.5 | 4.5 | Airflow+dbt+Docker, CVM DFs, PRs com gitflow, RAG chat |
| 3 | **Walleria Simoes** | **3.5/5** | 4.5 | 4 | 4 | 3.5 | 4 | 3 | Bancos vs empresas, prompt value investing, logging |
| 4 | **Diego Gadelha** | **3.5/5** | 4 | 3.5 | 3.5 | 3.5 | 4 | 3 | Prompt Buffett/Munger, logging, retry backoff, Groq gratuito |
| 5 | **Lucas Sodre** | **3.5/5** | 3 | 4 | 3.5 | 4.5 | 3.5 | 3.5 | Modos de pipeline, coleta paralela, pipeline_runs |
| 6 | **Alex Oliveira** | **3.5/5** | 3.5 | 4 | 3 | 4 | 2.5 | 3.5 | Dois LLMs, MySQL+ORM, dois scrappers |
| 7 | **Joao Felipe** | **3/5** | 5 | 4.5 | 4 | 1 | 3.5 | 2 | Melhor prompt de value investing, 5 fontes de dados |

---

## Analise Detalhada por Criterio

### 1. Prompt / LLM Engineering
**Destaque: Joao Felipe (5/5)**
- Unico prompt com "value-oriented analyst", "downside protection", "business quality"
- Anti-alucinacao, anti-filler, tratamento de lacunas
- JSON schema enforcement com fallback

**Outros destaques:**
- Walleria (4.5): Prompt com value investing explicito ("valor intrinseco", "abordagem bottom-up", "protecao de downside"), anti-alucinacao forte
- Isaias (4.5): Persona de fundo de R$1.2B AUM com posicoes concentradas, moats, margem de seguranca
- Diego (4): Hierarquia correta Buffett/Munger (qualidade antes de valuation), "NUNCA repita numeros"

### 2. Coleta de Dados
**Destaque: Felipe Schowantz (5/5)**
- Unico a coletar dados direto das DFs da CVM (DRE, BPA, BPP, DFC)
- 5 series macro do BCB com codigos especificos
- Upload de transcritos de calls em PDF

**Outros destaques:**
- Joao Felipe (4.5): 5 fontes (B3 API, yfinance, CVM, Status Invest, Google News) com pattern primary/fallback
- Isaias (4.5): Anti-blocking com curl_cffi + Chrome impersonation, dual-source news com dedup

### 3. Interface e Usabilidade
**Destaque: Isaias Goncalves (5/5)**
- Unico com deploy ao vivo (hipotesecapital.duckdns.org) com Docker + Nginx + SSL
- Graficos de retorno, historico, branding, tooltips em metricas
- DEPLOY_GUIDE.md completo

### 4. Banco de Dados e Pipeline
**Destaque: Isaias Goncalves (5/5)**
- Migracoes versionadas (001_initial_schema.sql)
- MD5 dedup para noticias
- Politica de refresh de 7 dias para companies
- `get_full_run_by_timestamp()` para reconstruir analises historicas

**Destaque: Lucas Sodre (4.5)**
- pipeline_runs para auditoria com status tracking
- ThreadPoolExecutor para coleta paralela
- Modos configuravies (--no-llm, --no-news, --workers)

**Problemas criticos:**
- Joao Felipe (1/5): sem banco de dados
- Felipe (3.5): TRUNCATE destroi historico no PostgreSQL
- Diego (3.5): `salvar_snapshot_no_db()` tem corpo `pass`

### 5. Tratamento de Erros
**Destaque: Isaias Goncalves (5/5)**
- Unico com testes unitarios (10 tests com mocking)
- Exception customizada LLMGenerationError com raw_response
- Logging customizado (console + arquivo)
- Debug info completo no resultado

### 6. Documentacao e Versionamento
**Destaque: Isaias Goncalves (5/5)**
- 68 commits progressivos
- README + DEPLOY_GUIDE + GEMINI.md
- pytest.ini configurado, Licenca MIT

**Destaque: Felipe Schowantz (4.5/5)**
- 44 commits com 11 PRs e gitflow
- README exemplar com tabelas, known issues, Mermaid diagram
- Apresentacao PPTX inclusa

---

## Alertas e Observacoes Criticas

| Candidato | Alerta | Severidade |
|-----------|--------|------------|
| Diego Gadelha | `salvar_snapshot_no_db()` com corpo `pass` - dados NAO persistidos | CRITICO |
| Felipe Schowantz | TRUNCATE destroi historico no PostgreSQL | ALTO |
| Felipe Schowantz | DAG `llm_synthesis` referencia funcoes inexistentes | ALTO |
| Felipe Schowantz | Credenciais (keys.env) vazadas no historico git | ALTO |
| Felipe Schowantz | Co-autoria explicita com Claude Sonnet em 2 commits | MEDIO |
| Joao Felipe | Apenas 6 commits, sem banco de dados | ALTO |
| Walleria Simoes | `.env` e `__pycache__` commitados (sem .gitignore!) | MEDIO |
| Lucas Sodre | `venv/`, `__pycache__` no repo; bare `except:` em yahoo_raw | MEDIO |
| Alex Oliveira | Bug: chaves do dict no insert_data nao batem com output dos scrappers | ALTO |
| Alex Oliveira | 133 dependencias incluindo Django, Selenium, LangChain nao usados | BAIXO |
| Isaias Goncalves | GEMINI.md revela uso de IA como assistente de codigo | INFO |
| Isaias Goncalves | `verify=False` no curl_cffi (risco de seguranca) | BAIXO |

---

## Branches de Avaliacao

Cada candidato tem avaliacao detalhada na respectiva branch:

- `avaliacao/alex-oliveira` - Nota 3.5/5
- `avaliacao/diego-gadelha` - Nota 3.5/5
- `avaliacao/felipe-schowantz` - Nota 4/5
- `avaliacao/isaias-goncalves` - Nota 5/5
- `avaliacao/joao-felipe` - Nota 3/5
- `avaliacao/lucas-sodre` - Nota 3.5/5
- `avaliacao/walleria-simoes` - Nota 3.5/5
