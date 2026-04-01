# Resumo Comparativo - Avaliacoes Case DS&AI

## Ranking Final

| # | Candidato | Nota | Prompt/LLM | Fontes | Interface | Banco/Pipeline | Erros | Doc/Git | Diferencial |
|---|-----------|------|------------|--------|-----------|---------------|-------|---------|-------------|
| 1 | **Isaias Goncalves** | **5/5** | 4.5 | 4.5 | 5 | 5 | 5 | 5 | Dashboard interativo + deploy ao vivo, testes, Docker, migracoes |
| 2 | **Walleria Simoes** | **3.5/5** | 4.5 | 4 | 4 | 3.5 | 4 | 3 | Bancos vs empresas, prompt value investing, logging |
| 3 | **Lucas Sodre** | **3.5/5** | 3 | 4 | 3.5 | 4.5 | 3.5 | 3.5 | Modos de pipeline, coleta paralela, pipeline_runs |
| 4 | **Joao Felipe** | **3/5** | 5 | 4.5 | 4 | 1 | 3.5 | 2 | Melhor prompt de value investing, 5 fontes de dados |
| 5 | **Felipe Schowantz** | **3/5** ¹ | 3.5 | 5 | 4 | 3.5 | 3.5 | 4.5 | Airflow+dbt+Docker, CVM DFs, PRs com gitflow, RAG chat |
| 6 | **Diego Gadelha** | **2.5/5** ² | 4 | 3.5 | 3.5 | 3.5 | 4 | 3 | Prompt Buffett/Munger, logging, retry backoff, Groq gratuito |
| 7 | **Alex Oliveira** | **2.5/5** ³ | 3.5 | 4 | 3 | 4 | 2.5 | 3.5 | Dois LLMs, MySQL+ORM, dois scrappers |

*¹ Felipe revisado de 3.5/5 para 3/5: extracao funciona (BCB 366 rows, CVM 3576 rows, yfinance OK), mas dbt falha em 13/17 modelos — camada de transformacao quebrada.*
*² Diego revisado de 3.5/5 para 2.5/5: dois bugs criticos — import order impede carregamento da GROQ_API_KEY, salvar_snapshot_no_db() com corpo `pass` impede persistencia.*
*³ Alex revisado de 3.5/5 para 2.5/5: projeto inoperante — requer MySQL + GTK libs (WeasyPrint) + chaves reais (placeholder no .env), cadeia de imports impede qualquer execucao.*

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

**Destaque: Felipe Schowantz (3.5/5 revisado)**
- 44 commits com 11 PRs e gitflow
- README bem estruturado com tabelas, known issues, Mermaid diagram
- Apresentacao PPTX inclusa
- *Penalizado: URL ausente no git clone, .env ≠ .envexample, Docker nao declarado como prerequisito*

---

## Alertas e Observacoes Criticas

| Candidato | Alerta | Severidade | Verificado em execucao |
|-----------|--------|------------|----------------------|
| Diego Gadelha | `salvar_snapshot_no_db()` com corpo `pass` — nada persiste em snapshots/noticias | CRITICO | Sim (01/abr) |
| Diego Gadelha | Import order bug: `load_dotenv()` apos import do LLM — GROQ_API_KEY nunca carregada | CRITICO | Sim (01/abr) |
| Diego Gadelha | Pipeline reporta "3/3 analises geradas" quando LLM falhou em todas — mensagem enganosa | ALTO | Sim (01/abr) |
| Alex Oliveira | Projeto inoperante: MySQL + WeasyPrint (GTK libs) + chaves placeholder | CRITICO | Sim (01/abr) |
| Alex Oliveira | Cadeia de imports (scrapper1→scrapper2→llm_utils→weasyprint) impede qualquer modulo | CRITICO | Sim (01/abr) |
| Alex Oliveira | 133 dependencias incluindo Django, Selenium, LangChain nao usados | MEDIO | Sim (01/abr) |
| Felipe Schowantz | dbt transformation layer quebrada: 13/17 modelos falham com Database Error | CRITICO | Sim (01/abr) |
| Felipe Schowantz | TRUNCATE destroi historico no PostgreSQL | ALTO | Confirmado em analise |
| Felipe Schowantz | Mismatch de colunas staging→gold (ex: `data` vs `ref_date` em gold_macro) | ALTO | Sim (01/abr) |
| Felipe Schowantz | Credenciais (keys.env) vazadas no historico git | ALTO | Confirmado em analise |
| Felipe Schowantz | Co-autoria explicita com Claude Sonnet em 2 commits | MEDIO | Confirmado em analise |
| Joao Felipe | `.env` define `OPENAI_MODEL=gpt-5.4-mini` (modelo inexistente) — LLM falha OOTB | ALTO | Sim (01/abr) |
| Joao Felipe | Apenas 6 commits, sem banco de dados (Fase 2 ausente) | ALTO | Confirmado |
| Walleria Simoes | `.env` e `__pycache__` commitados (sem .gitignore!) | MEDIO | Confirmado |
| Walleria Simoes | `main.py` batch nao integra com banco — persiste apenas em Excel | MEDIO | Sim (01/abr) |
| Walleria Simoes | Duplicatas em `market_data` (sem UNIQUE constraint em ticker+date) | MEDIO | Sim (01/abr) |
| Lucas Sodre | Instrucoes de setup exclusivas para Linux sem aviso (funciona em Windows) | BAIXO | Sim (01/abr) |
| Lucas Sodre | `venv/`, `__pycache__` no repo; bare `except:` em yahoo_raw | MEDIO | Confirmado |
| Isaias Goncalves | Path de migracao relativo ao CWD — falha se executado de dentro de `src/` | BAIXO | Sim (01/abr) |
| Isaias Goncalves | GEMINI.md revela uso de IA como assistente de codigo | INFO | Confirmado |
| Isaias Goncalves | `verify=False` no curl_cffi (risco de seguranca) | BAIXO | Confirmado |

---

## Arquivos de Avaliacao

Avaliacoes individuais detalhadas na pasta `avaliacoes/` desta branch:

- [avaliacoes/isaias-goncalves.md](avaliacoes/isaias-goncalves.md) - Nota 5/5 *(confirmado em execucao)*
- [avaliacoes/walleria-simoes.md](avaliacoes/walleria-simoes.md) - Nota 3.5/5 *(confirmado em execucao)*
- [avaliacoes/lucas-sodre.md](avaliacoes/lucas-sodre.md) - Nota 3.5/5 *(confirmado em execucao)*
- [avaliacoes/joao-felipe.md](avaliacoes/joao-felipe.md) - Nota 3/5 *(confirmado em execucao)*
- [avaliacoes/felipe-schowantz.md](avaliacoes/felipe-schowantz.md) - Nota 3/5 *(revisado de 3.5/5 — dbt quebrado)*
- [avaliacoes/diego-gadelha.md](avaliacoes/diego-gadelha.md) - Nota 2.5/5 *(revisado de 3.5/5 — 2 bugs criticos)*
- [avaliacoes/alex-oliveira.md](avaliacoes/alex-oliveira.md) - Nota 2.5/5 *(revisado de 3.5/5 — inoperante)*
