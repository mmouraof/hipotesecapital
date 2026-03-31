# Centralizador de Análise — PoC

Ferramenta de coleta, transformação e síntese automatizada de dados públicos de empresas listadas na B3, desenvolvida como solução para o Case Study DS&AI da Charles River Capital 2026.

O projeto automatiza a coleta semanal de dados que um analista realiza manualmente antes da reunião de comitê: dados macro (BCB), múltiplos de mercado (Yahoo Finance) e demonstrações financeiras (CVM), processados via arquitetura medallion e sintetizados por LLM ancorada na tese de investimento.

---

## Empresas Monitoradas — PoC

| Ticker | Empresa | Setor |
|--------|---------|-------|
| ASAI3 | Assaí Atacadista | Varejo Alimentar |
| PRIO3 | PetroRio | Commodities / Petróleo |
| RENT3 | Localiza | Serviços / Mobilidade |

> A escolha cobre três setores distintos para validar a generalidade do pipeline. Qualquer ticker B3 pode ser adicionado em `data-pipeline/utils/company_config.py` sem alterações estruturais.

---

## Arquitetura

```
┌──────────────────────────────────────────────────────────────┐
│                     FONTES DE DADOS                          │
│                                                              │
│  BCB (api.bcb.gov.br)     — Macro: Selic, IPCA, câmbio...  │
│  Yahoo Finance (yfinance) — Micro: preço, P/L, EV/EBITDA... │
│  CVM (dados.cvm.gov.br)   — DRE, Balanço, Fluxo de Caixa   │
│  uploads/ (PDF/XLSX)      — Transcrições earnings calls      │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼  Apache Airflow 2.9.2
                       │  DAG monday_briefing — toda segunda às 8h
                       │  DAG site_ingestion  — FileSensor em uploads/
                       │  DAG llm_synthesis   — toda segunda às 9h
                       │
┌──────────────────────▼───────────────────────────────────────┐
│            DATA-LAKEHOUSE — Medallion Architecture           │
│                                                              │
│  bronze/   → Parquet bruto por fonte (auditável, imutável)  │
│  staging/  → Tabelas tipadas no PostgreSQL (via dbt)        │
│  gold/     → Tabelas analíticas por empresa e tema (dbt)    │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼  PostgreSQL 14 + dbt-core
                       │
┌──────────────────────▼───────────────────────────────────────┐
│                   CAMADA GOLD                                │
│                                                              │
│  gold_macro          — Selic, IPCA, câmbio, desemprego      │
│  gold_market         — Múltiplos de mercado (3 empresas)    │
│  gold_{ticker}_dre   — Income Statement por empresa         │
│  gold_{ticker}_balance — Balance Sheet por empresa          │
│  gold_{ticker}_cf    — Cash Flow por empresa                │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼  LLM (Anthropic / OpenAI)
                       │  Detecta mudanças relevantes pela tese
                       │  Lê transcrições de earnings calls (RAG)
                       │
┌──────────────────────▼───────────────────────────────────────┐
│              DASHBOARD — Streamlit + Plotly                  │
│  Macro · Múltiplos · DRE/Balanço · Síntese LLM             │
└──────────────────────────────────────────────────────────────┘
```

---

## Stack

| Camada | Tecnologia | Versão |
|--------|-----------|--------|
| Orquestração | Apache Airflow | 2.9.2 |
| Containerização | Docker + Docker Compose | — |
| Banco de dados | PostgreSQL | 14.22 |
| Transformação | dbt-core + dbt-postgres | — |
| Extração macro | python-bcb | — |
| Extração mercado | yfinance | — |
| Extração DRE | requests + CVM API pública | — |
| Ingestão docs | pdfplumber + openpyxl | — |
| Conexão DB | psycopg2 | — |
| Síntese LLM | Anthropic / OpenAI | — |
| Dashboard | Streamlit + Plotly | — |
| Inspeção SQL | Adminer | 4.8.1 |

---

## Estrutura do Projeto

```
centralizador_de_analise/
│
├── data-pipeline/
│   ├── dags/
│   │   ├── monday_briefing.py   # Extração → PostgreSQL → dbt (toda segunda às 8h)
│   │   ├── llm_synthesis.py     # RAG + síntese LLM (toda segunda às 9h)
│   │   └── site_ingestion.py    # FileSensor → parse PDF/XLSX → staging
│   ├── extractors/
│   │   ├── macro_bcb.py         # BCB: Selic, IPCA, câmbio, desemprego
│   │   ├── market_yfinance.py   # Yahoo Finance: preço e múltiplos (.SA automático)
│   │   └── fundamentals_cvm.py  # CVM: DRE/Balanço/CF via ITR + fallback DFP
│   ├── loaders/
│   │   └── postgres_loader.py   # Parquet → PostgreSQL (psycopg2) + dbt run
│   ├── utils/
│   │   ├── company_config.py    # Config central: tickers, CNPJs, padrão de arquivo
│   │   ├── file_parser.py       # Parser de PDF/XLSX por nome de arquivo
│   │   └── site_writer.py       # Bronze (Parquet) + Silver (PostgreSQL) writer
│   └── synthesis/
│       ├── rag.py               # Busca contexto nas tabelas gold
│       └── llm_report.py        # Gera relatório via LLM
│
├── dbt/
│   ├── models/
│   │   ├── staging/
│   │   │   ├── sources.yml      # Declaração das fontes raw
│   │   │   ├── stg_bcb.sql      # Tipagem + NaN→NULL + renomeia colunas
│   │   │   ├── stg_yfinance.sql # Tipagem + strip .SA + limpeza company_name
│   │   │   └── stg_cvm.sql      # Tipagem + NUMERIC(18,2) para valores
│   │   └── gold/
│   │       ├── gold_macro.sql         # Macro BCB deduplicado por data
│   │       ├── gold_market.sql        # Múltiplos yFinance deduplicados por ticker
│   │       ├── gold_{ticker}_dre.sql  # Income Statement (contas 3.xx)
│   │       ├── gold_{ticker}_balance.sql # Balance Sheet (1.xx + 2.xx)
│   │       └── gold_{ticker}_cf.sql   # Cash Flow (contas 6.xx)
│   ├── macros/
│   │   └── generate_schema_name.sql  # Override: usa schema customizado sem prefixo
│   ├── profiles.yml
│   └── dbt_project.yml
│
├── infra/
│   └── init_db.sql              # Criação do banco, schemas e tabelas raw
│
├── uploads/                     # Drop zone para PDFs e XLSXs de earnings
│   └── processed/               # Arquivos processados pelo site_ingestion
│
├── Dockerfile                   # airflow:2.9.2-python3.11 + dependências
├── docker-compose.yml           # postgres + airflow-init + webserver + scheduler + adminer
├── .env.example                 # Template de variáveis de ambiente
└── requirements.txt             # Dependências Python do pipeline
```

---

## Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado e rodando
- Git

---

## Como Executar

### 1. Clonar o repositório

```bash
git clone <repo-url>
cd centralizador_de_analise
```

### 2. Configurar variáveis de ambiente

```bash
cp .env.example .env
```

Abra o arquivo `.env` e preencha as variáveis:

```env
# Provedor LLM: "anthropic" ou "openai"
LLM_PROVIDER=anthropic
LLM_API_KEY=sua_chave_aqui

# Banco de dados (padrão funciona com docker-compose)
PG_HOST=postgres
PG_DB=hipotetical_fia
PG_USER=airflow
PG_PASSWORD=airflow
```

#### Onde obter a chave de API

| Provedor | Link | Modelo utilizado |
|----------|------|-----------------|
| **Anthropic** (padrão) | [console.anthropic.com](https://console.anthropic.com) → API Keys | `claude-haiku-4-5-20251001` |
| **OpenAI** | [platform.openai.com](https://platform.openai.com) → API Keys | `gpt-4o-mini` |

> **Nota:** A chave fica em `.env` na raiz do projeto. Esse arquivo está no `.gitignore` e **nunca deve ser commitado**.

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `LLM_PROVIDER` | Provedor do modelo | `anthropic` |
| `LLM_API_KEY` | Chave de API do provedor escolhido | — |
| `PG_HOST` | Host do PostgreSQL | `postgres` |
| `PG_DB` | Nome do banco | `hipotetical_fia` |
| `PG_USER` | Usuário | `airflow` |
| `PG_PASSWORD` | Senha | `airflow` |

### 3. Subir os containers

```bash
docker-compose up --build -d
```

Aguardar ~60 segundos para o Airflow inicializar.

### 4. Acessar as interfaces

| Interface | URL | Credenciais |
|-----------|-----|-------------|
| Airflow | http://localhost:8080 | admin / admin |
| Adminer (SQL) | http://localhost:8888 | Sistema: PostgreSQL / servidor: postgres / usuário: airflow / senha: airflow / banco: hipotetical_fia |

### 5. Rodar o pipeline

No Airflow (`localhost:8080`), acionar manualmente a DAG **`monday_briefing`**.

O pipeline executa na ordem:
```
[extract_bcb, extract_yfinance, extract_cvm] → load_to_postgres → dbt_run
```

Após conclusão, as tabelas gold estarão disponíveis no PostgreSQL.

### 6. Ingerir transcrições de earnings calls

Copiar PDF para a pasta `uploads/` com o padrão de nome:
```
YYYY-MM-DD_TICKER_PERIODO_transcricao.pdf
Exemplo: 2026-01-12_ASAI3_4T25_transcricao.pdf
```

A DAG **`site_ingestion`** detecta automaticamente o arquivo via FileSensor e processa.

---

## Fontes de Dados

| Fonte | Tipo | Séries / Campos |
|-------|------|-----------------|
| [BCB SGS](https://api.bcb.gov.br) | Macro | Selic (432), IPCA (433), Desemprego (24369), USD/BRL (1), Balança Comercial (22707) |
| [Yahoo Finance](https://finance.yahoo.com) | Mercado | Preço, Market Cap, P/L, P/VP, EV/EBITDA, ROE, Margens, DY |
| [CVM](https://dados.cvm.gov.br) | Fundamentalista | DRE, Balanço Patrimonial, Fluxo de Caixa (ITR trimestral + DFP anual) |

Todas as fontes são **públicas e gratuitas**, sem autenticação paga.

---

## Papel da LLM

A LLM atua como **detector de mudanças relevantes pela tese**, não como analista autônomo.

- **Faz:** descreve variações nos indicadores em relação ao período anterior e sinaliza impacto na tese de investimento (value investing, proteção ao downside)
- **Não faz:** emite opiniões qualitativas genéricas nem avalia fatores subjetivos

O contexto enviado ao modelo inclui: dados gold da empresa, indicadores macro e texto da transcrição do earnings call (RAG).

---

## Fase 3 — RAG do Método de Investimento

A Fase 3 implementa um protótipo de RAG para incorporar o método de investimento da gestora ao processo de análise.

**Fluxo:**
1. Documento da tese/método é ingerido via `uploads/` (PDF)
2. Texto é extraído e armazenado em `staging.transcripts`
3. Na geração do relatório, o contexto do documento é recuperado junto com os dados gold
4. O LLM responde ancorado tanto nos dados quantitativos quanto no método qualitativo da gestora

**Por que não usar vector DB:** os documentos de tese são pequenos o suficiente para caber no contexto do modelo diretamente, sem necessidade de embeddings e busca vetorial.

---

## Notas Conhecidas

| Issue | Status |
|-------|--------|
| ASAI3 sem dados CVM | CNPJ `06057223000171` não encontrado no ITR/DFP 2025. Investigar CNPJ correto na B3. |
| Séries BCB com NULL | Normal — câmbio não tem dados em fins de semana; desemprego é trimestral; IPCA é mensal. |

---

## Status das Fases

- [x] Fase 1 — Extração BCB, yFinance, CVM
- [x] Fase 1 — Carga no PostgreSQL (psycopg2)
- [x] Fase 1 — Transformação dbt (staging → gold)
- [x] Fase 2 — Pipeline recorrente com Airflow (toda segunda às 8h)
- [x] Fase 2 — Medallion architecture (bronze Parquet → staging → gold)
- [x] Fase 2 — Tratamento de erros (NaN, CNPJ ausente, fallback ITR→DFP)
- [ ] Fase 1 — Dashboard interativo (Streamlit) — em desenvolvimento
- [ ] Fase 1 — Síntese LLM pela tese — em desenvolvimento
- [ ] Fase 3 — RAG do método de investimento — em desenvolvimento

---

*PoC desenvolvida para o Case DS&AI — Charles River Capital, março/2026.*
