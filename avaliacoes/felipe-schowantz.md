# Avaliacao - Felipe Schowantz

**Repositorio:** https://github.com/FelipeSchowantz/centralizador_de_analise
**Commits:** 44 (29/mar a 30/mar, com 11 PRs)

---

## 1. Qualidade do Prompt / LLM Engineering (Fase 1)

**Nota do criterio: 3.5/5**

O system prompt em `synthesis/llm_report.py` instrui o LLM como assistente de analise para fundo de value investing:

> "You are an investment analyst assistant for a value investing fund... Relate findings to a value investing thesis: downside protection, cash generation, leverage trends. Be concise and factual -- no generic qualitative opinions. Always cite the specific data point you are referencing."

**Pontos positivos:**
- Menciona value investing, downside protection, geracao de caixa, tendencias de alavancagem
- Instrucao para citar dados especificos e ser factual
- Guardrail: "If the data does not contain enough information to answer, say so clearly"
- Chat interativo no dashboard funciona com contexto RAG dos dados gold

**Pontos negativos:**
- Prompt competente mas generico - funciona mais como "assistente de analise fundamental" do que "assistente de value investing"
- Nao menciona valor intrinseco, margem de seguranca, moats competitivos ou frameworks Graham/Buffett
- Nao define a tese de investimento especifica para as empresas monitoradas
- `max_completion_tokens` nao configurado (pode truncar respostas)

---

## 2. Coleta Automatizada e Fontes de Dados (Fase 1)

**Nota do criterio: 5/5**

A melhor diversificacao de fontes entre todos os candidatos, com dados extraidos diretamente das **Demonstracoes Financeiras (DFs) da CVM**.

**Fontes utilizadas:**
- **BCB (Banco Central):** 5 series macro com codigos especificos (432-Selic, 433-IPCA, 24369-cambio, 1-desemprego, 22707-balanca comercial)
- **Yahoo Finance:** Precos, multiplos (P/L, P/VPA, EV/EBITDA), margens
- **CVM (dados.cvm.gov.br):** Download direto de ZIPs com DRE, BPA, BPP, DFC - filtrado por CNPJ
- **Upload de transcritos de calls** em PDF (pdfplumber, openpyxl)

**Diferenciais tecnicos:**
- Extrator CVM busca ITR (trimestral) com fallback para DFP (anual)
- Filtragem por prefixos contabeis (3. para DRE, 1. para BPA, 2. para BPP, 6. para DFC)
- Output em Parquet para camada bronze do data lakehouse
- Dados macro contextualizando a analise micro
- Retry com backoff no extrator BCB (3 tentativas, 2s sleep)
- Config centralizada em `company_config.py` (adicionar empresa = 1 entrada no dict)

---

## 3. Interface e Usabilidade (Fase 1)

**Nota do criterio: 4/5** (revisado para cima - dashboard existe e funciona)

O dashboard Streamlit (`dashboard/app.py`) tem 4 tabs:
- **MACRO:** Graficos Plotly de Selic, USD/BRL, IPCA, desemprego
- **EMPRESA:** Metricas (P/E, EV/EBITDA, P/B, ROE, margens, divida/equity)
- **FINANCEIRO:** Barras de receita/lucro das DFs
- **CHAT:** Interface de chat interativa com RAG contextualizado por ticker

**Pontos positivos:**
- Branding institucional ("HYPOTHETICAL FIA" com cores gold/navy)
- CSS customizado (Avenir, chrome do Streamlit escondido)
- Chat interativo com contexto RAG por ticker selecionado
- Cache de 300s, session state para historico de chat
- Sidebar com seletor de ticker e indicador de estagio do pipeline

**Pontos negativos:**
- ASAI3 nao esta na lista de tickers do dashboard (so PRIO3 e RENT3)
- O analista nao gera um "relatorio de briefing" como os outros candidatos - a interface e mais exploratoria
- **Dashboard inacessivel na pratica (verificado rodando)**: Docker e obrigatorio para subir PostgreSQL + Airflow, mas o README nao explicita isso como pre-requisito essencial — sem Docker rodando, o dashboard nao funciona; sem PostgreSQL acessivel, os dados nao existem
- **PDF/PPTX inacessiveis via dashboard**: o upload de transcritos funciona na interface mas depende do pipeline ter rodado com sucesso end-to-end

---

## 4. Modelagem do Banco de Dados e Pipeline (Fase 2)

**Nota do criterio: 3.5/5** (revisado para baixo - TRUNCATE pattern e grave)

Arquitetura medalha (bronze/staging/gold) com PostgreSQL, dbt e Airflow.

**Estrutura PostgreSQL:**
- Schema `staging`: raw_bcb, raw_yfinance, raw_cvm, transcripts (todas com `_extracted_at`)
- Schema `gold` (via dbt): gold_macro, gold_market, gold_{ticker}_dre/balance/cf

**Pipeline Airflow:**
- DAG `monday_briefing`: toda segunda as 8h
- Extracao paralela (BCB, yfinance, CVM) -> Load no Postgres -> dbt run + dbt test
- Docker Compose com 6 servicos (Postgres 14.22, Airflow 2.9.2, Adminer)

**PROBLEMA CRITICO - TRUNCATE pattern:**
O loader faz `cur.execute(f"TRUNCATE TABLE {table}")` antes de cada carga. Isso **destroi todos os dados anteriores** no PostgreSQL a cada execucao! A premissa de "rodadas nao sobrescrevem" so vale para os Parquets datados na camada bronze.

Alem disso, `stg_yfinance` e configurado como `incremental` no dbt, mas o loader faz TRUNCATE no raw - contradizendo a estrategia incremental.

**Pontos positivos:**
- Parquets datados na bronze preservam historico raw
- dbt test como camada de validacao
- Infra como codigo (Docker, init_db.sql)
- Loader com rollback em caso de erro

**Pontos negativos:**
- TRUNCATE destroi historico no PostgreSQL
- Contradicao incremental vs TRUNCATE
- Sem migracoes versionadas no PostgreSQL

---

## 5. Tratamento de Erros e Robustez (Fase 2)

**Nota do criterio: 3.5/5**

**Cobertura dos 3 casos obrigatorios:**
- API fora do ar: Airflow retries (2x, 5min delay), BCB com retry+backoff, CVM com fallback ITR->DFP
- Ticker invalido: Filtragem por CNPJ no CVM, mas sem validacao explicita no yfinance
- Resposta LLM fora do formato: Chat interativo com try/except, mas DAG de sintese nao funciona

**Pontos positivos:**
- Retry com backoff no BCB (3 tentativas)
- Fallback ano atual -> ano anterior no CVM
- Loader com transacao e rollback
- RAG context loading com try/except por secao (se tabela gold nao existe, pula silenciosamente)

**Pontos negativos:**
- DAG `llm_synthesis` referencia funcoes inexistentes (`fetch_context` e `generate_reports` em vez de `build_context` e `chat`) - nao funciona em runtime
- Mismatch de colunas: `gold_macro.sql` espera `ref_date` mas `stg_bcb.sql` produz `data`
- Risco de SQL injection em `rag.py`: `f"FROM {dre_table}"` com interpolacao f-string
- `print()` em vez de logging (aceitavel no contexto Airflow)

---

## 6. Documentacao e Versionamento (Fases 1 e 2)

**Nota do criterio: 4.5/5** (revisado para baixo - credential leak)

**README:**
- Extremamente bem detalhado com tabelas de tecnologias, versoes e codigos de series BCB
- Diagrama de arquitetura em Mermaid (`docs/arquitetura_pipeline.md`)
- Secao de known issues (ASAI3 CNPJ, BCB NULL)
- Status transparente com checkboxes
- Apresentacao em PPTX inclusa

**Versionamento:**
- 44 commits com **11 PRs** e branches organizadas
- Mensagens seguem convencao (feat:, fix:, docs:)
- `.gitignore`, `.dockerignore`, `.gitattributes` presentes

**PROBLEMAS (verificado rodando):**
- **Credential leak**: `keys.env` foi commitado e depois removido - credenciais no historico git!
- **Co-autoria explicita com Claude Sonnet 4.6** em 2 commits (README e gold layer)
- `pixi.toml` com dependencias vazias
- **URL do repositorio ausente no git clone**: o README instrui o usuario a clonar mas nao inclui o link do repo — o candidato omitiu o proprio URL
- **`.env` inconsistente com `.env.example`**: o arquivo de exemplo nao reflete as variaveis reais usadas no codigo, dificultando o setup sem inspeção manual do codigo
- **Docker obrigatorio nao documentado como prerequisito**: a stack inteira depende de Docker Compose (PostgreSQL + Airflow + Adminer), mas o README nao declara Docker como requisito antes das instrucoes de uso

---

## 7. Visao Arquitetural e RAG (Fase 3)

**Nota do criterio: 4/5** (revisado para cima - RAG funciona)

O candidato implementou RAG como context stuffing no `synthesis/rag.py`:
- Busca dados macro (12 meses) da tabela gold
- Busca multiplos de mercado (ultimo)
- Busca linhas-chave da DRE (ultimas 20 linhas)
- Busca transcrito de call (max 8000 chars)
- Concatena tudo como texto formatado no contexto do LLM

**Racional documentado no README:**
> "Os documentos de tese sao pequenos o suficiente para caber no contexto do modelo diretamente, sem necessidade de embeddings e busca vetorial"

**Pontos positivos:**
- Decisao pragmatica e documentada de nao usar vector DB
- Contexto rico com dados macro + micro + DFs + transcritos
- Chat interativo funcional no dashboard
- Reconhece limitacoes e trade-offs

**Pontos negativos:**
- Nao e RAG no sentido tecnico (sem embeddings, sem vector store)
- Risco de SQL injection na construcao de queries
- DAG de sintese batch nao funciona (function name mismatch)

---

## Nota Final: 3.5/5

*(Revisado de 4/5 para 3.5/5 apos tentativa de execucao em 31/mar/2026)*

O candidato demonstrou a **melhor visao arquitetural** entre todos os avaliados. A escolha de Airflow + PostgreSQL + dbt + Docker e a coleta de dados direto da CVM (DFs) sao diferenciais claros. O README e bem estruturado e o uso de PRs demonstra maturidade. O dashboard com chat RAG e um diferencial da Fase 3.

Porem, a experiencia de rodar o codigo revelou gaps criticos de execucao: o pipeline nao e executavel sem Docker (nao documentado como prerequisito essencial), o PostgreSQL nao ficou acessivel, o dashboard nao carregou, a URL do repo esta ausente nas instrucoes de clone, e o `.env` diverge do `.envexample`. Isso confirma que as pecas nao foram testadas end-to-end:
- TRUNCATE destroi historico no PostgreSQL
- DAG de sintese referencia funcoes inexistentes
- Mismatch de colunas entre staging e gold
- Credenciais vazadas no git history
- Co-autoria explicita com IA (2 commits)
- Dashboard inacessivel sem infraestrutura Docker completa

O candidato priorizou amplitude arquitetural sobre profundidade de implementacao — entregou muito escopo mas com gaps severos de integracao que impedem execucao sem modificacoes.

**Diferenciais:** Airflow + dbt + Docker, dados CVM (DFs), 11 PRs com gitflow, RAG com chat interativo, dados macro BCB, apresentacao PPTX
**Lacunas:** TRUNCATE destroi historico, DAG de sintese quebrada, credential leak, co-autoria com IA, mismatch de colunas, prompt generico, Docker nao documentado como prerequisito, .env ≠ .envexample, URL ausente no git clone, dashboard inacessivel na pratica
