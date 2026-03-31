
Projeto para coleta recorrente de dados de ações da B3, persistência histórica em SQLite e visualização em dashboard Streamlit.

## Objetivo

- Coletar dados de múltiplas fontes (Yahoo Finance, Fundamentus e Google News RSS fallback).
- Persistir histórico sem sobrescrever execuções anteriores.
- Exibir dados atuais e históricos no dashboard.
- Gerar relatório estruturado com LLM (Gemini) opcionalmente.

## Como Rodar

### 1. Pré-requisitos

- Python 3.11+ (projeto validado com Python 3.13)
- pip
- Internet para coleta de dados

### 2. Entrar na pasta do projeto

```bash
cd "/Users/myname/.../Dashboard B3"
```

### 3. Criar e ativar ambiente virtual

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Instalar dependências

```bash
pip install streamlit pandas yfinance deep-translator requests beautifulsoup4
```

### 5. Configurar variável de ambiente (opcional para LLM)

Se quiser gerar relatório com IA (Gemini), configure a chave:

```bash
export GOOGLE_API_KEY="SUA_CHAVE_AQUI"
```
Para acessar sua chave de API, entre no site aistudio.google.com/api-keyse

Sem essa variável, o pipeline e dashboard funcionam normalmente, mas a geração de relatório LLM fica desabilitada.

### 6. Rodar pipeline (modo rápido recomendado)

```bash
"$PWD/venv/bin/python" pipeline_runner.py --no-llm --no-news --workers 12 --progress-every 25
```

Esse comando:
- coleta e persiste tickers e fundamentos
- não gera relatório LLM
- não coleta notícias (mais rápido)

### 7. Subir dashboard

```bash
streamlit run dashboard.py
```

## Variáveis de Ambiente

- `GOOGLE_API_KEY`: chave para geração de relatório LLM com Gemini.

Opcionalmente, no Streamlit Cloud, pode usar `st.secrets` com a mesma chave:

```toml
GOOGLE_API_KEY = "SUA_CHAVE_AQUI"
```

## Comandos Úteis

### Pipeline completo

```bash
"$PWD/venv/bin/python" pipeline_runner.py
```

### Pipeline com limite de tickers

```bash
"$PWD/venv/bin/python" pipeline_runner.py --limit 100 --no-llm --no-news --workers 12
```

### Pipeline para tickers específicos

```bash
"$PWD/venv/bin/python" pipeline_runner.py --tickers PETR4,VALE3,ITUB4 --no-llm --workers 8
```

### Banco SQLite: ver total de empresas cadastradas

```bash
sqlite3 data/pipeline.sqlite3 "select count(*) from companies;"
```

## Estrutura de Pastas

```text
Dashboard B3/
├── dashboard.py                  # App Streamlit (visualização + consulta de histórico)
├── pipeline_runner.py            # Pipeline recorrente (coleta + persistência)
├── data/
│   ├── tickers.py                # Coleta da lista de tickers
│   ├── yahoo_raw.py              # Coleta de dados do Yahoo + fallback Fundamentus
│   ├── fundamentus_api.py        # Coleta e normalização de dados Fundamentus
│   ├── news_sources.py           # Fontes de notícias com fallback e recência
│   ├── pipeline_db.py            # Camada SQLite (schema e consultas)
│   └── pipeline.sqlite3          # Banco gerado pelo pipeline
├── llm/
│   └── report_generator.py       # Geração de relatório estruturado (Gemini)
├── utils/
│   ├── formatters.py             # Formatação de valores/data
│   └── news_parser.py            # Normalização de notícias
└── venv/
```

## Modelo de Dados (Resumo)

- `companies`: dados estáticos/cadastrais por ticker.
- `pipeline_runs`: metadados de cada execução.
- `fundamentals_snapshots`: indicadores por execução (histórico).
- `news_snapshots`: notícias por execução (histórico).
- `llm_reports`: relatórios gerados por execução (histórico).

Esse desenho garante histórico temporal sem sobrescrever rodadas anteriores. Além disso, vale a pena notar que o histórico de indicadores será populado de acordo com a quantidade de vezes que o pipeline é executado.

## Troubleshooting Rápido

- Pipeline parece lento:
  - use `--no-news --no-llm --workers 12`
- Sem tickers no pipeline:
  - confira conectividade e fonte em `data/tickers.py`
- Relatório IA não gera:
  - confirme `GOOGLE_API_KEY`
- Dashboard sem histórico:
  - execute o pipeline ao menos uma vez

## Observações

- Alguns tickers podem falhar no Yahoo (`.SA`) e isso é esperado; o pipeline continua para os demais.
- O fallback Fundamentus tenta preencher lacunas de indicadores quando o Yahoo não retorna campos.
