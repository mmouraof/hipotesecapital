# Hipótese Capital — Briefing Automatizado

Ferramenta interna que gera relatórios automatizados de ativos para a reunião de comitê da segunda-feira. Dado um ticker, entrega: resumo do negócio, indicadores fundamentalistas interpretados, notícias recentes classificadas por impacto e três perguntas investigativas.

Desenvolvido como case técnico para a posição de Data Science & AI na Hipótese Capital.

## Início Rápido

### Pré-requisitos

- Python 3.11+
- Uma API key da [Anthropic](https://console.anthropic.com/)

### Instalação local

```bash
git clone https://github.com/mmouraof/hipotesecapital.git
cd hipotesecapital
pip install -r requirements.txt
```

### Configuração da API Key

Crie um arquivo `.env` na raiz do projeto a partir do exemplo:

```bash
cp .env.example .env
```

Abra o `.env` e substitua o valor placeholder pela sua chave:

```
ANTHROPIC_API_KEY=sk-ant-sua-chave-aqui
```

> **Segurança:** O arquivo `.env` está no `.gitignore` e nunca será commitado. Nunca compartilhe sua chave diretamente no código ou em commits.

### Execução completa (coleta + análise + dashboard)

```bash
python src/main.py
```

O script coleta os dados, gera as análises via API e monta o dashboard com os resultados embutidos em `dashboard/index.html`. Abra esse arquivo diretamente no navegador — nenhum servidor local é necessário. Ao final da execução, o arquivo é aberto automaticamente no navegador padrão.

### Testar o dashboard sem rodar o pipeline

Para visualizar o layout sem consumir a API, abra `dashboard/index_mock.html` diretamente no navegador. Ele contém dados fictícios de 3 ativos (PRIO3, ITUB4, SLCE3) já embutidos e funciona offline.

> `index_mock.html` é gerado a partir do mesmo template, mas com o bloco mock ativo. Não edite `template.html` para isso — o template deve permanecer intacto para o pipeline de produção.

## Usando GitHub Codespaces

O repositório inclui configuração de Dev Container para execução imediata.

1. No GitHub, clique em **Code** → **Codespaces** → **Create codespace on main**
2. Aguarde o setup automático (instala dependências via `requirements.txt`)
3. Configure a API key de uma das duas formas:
   - **Via Secret (recomendado):** antes de criar o Codespace, vá em Settings → Secrets and variables → Codespaces → New repository secret → nome `ANTHROPIC_API_KEY`
   - **Via `.env`:** no terminal do Codespace, execute `cp .env.example .env` e edite com sua chave
4. Para visualizar o layout imediatamente (sem consumir a API), abra `dashboard/index_mock.html` no navegador
5. Para rodar o pipeline completo: `python src/main.py` — o `dashboard/index.html` gerado será aberto automaticamente

## Arquitetura

```
hipotese-capital/
├── .devcontainer/
│   └── devcontainer.json       # Config do GitHub Codespaces
├── .vscode/
│   └── settings.json           # Settings do VS Code
├── .env.example                # Template da API key
├── .gitignore
├── requirements.txt
├── data/
│   ├── ativos.txt              # Tickers + nomes das empresas
│   └── output/                 # JSONs gerados (um por execução)
├── src/
│   ├── main.py                 # Orquestrador principal
│   ├── coleta_indicadores.py   # Extração de indicadores via web_fetch (API Claude)
│   ├── coleta_noticias.py      # Coleta de notícias via RSS (Google News)
│   ├── analise_llm.py          # Geração de resumos e insights via API Claude
│   └── gera_dashboard.py       # Injeta dados no template HTML
└── dashboard/
    ├── template.html           # Template com placeholder para dados
    ├── index_mock.html         # Versão com dados mock para testes (abrir no navegador)
    └── index.html              # HTML final gerado pelo pipeline (autocontido)
```

### Fluxo de dados

```
ativos.txt → coleta_indicadores.py (web_fetch) → indicadores em JSON
           → coleta_noticias.py (RSS)           → notícias em JSON
           → analise_llm.py (Claude API)        → resumos e insights
           → data/output/YYYY-MM-DD.json        → dashboard/index.html
```

### Decisões técnicas

**Por que HTML autocontido em vez de Streamlit?**
O avaliador abre o arquivo no navegador sem instalar nada e sem rodar um servidor. O `main.py` injeta os dados diretamente no HTML como objeto JavaScript, eliminando problemas de CORS com `file://`. Separação clara entre backend (Python coleta e analisa) e frontend (HTML renderiza).

**Por que RSS para notícias em vez de web scraping?**
Google News RSS é gratuito, estável e não requer parsing de HTML frágil. Retorna título, link, data e fonte. A classificação de sentimento é feita pelo LLM na etapa de análise, não na coleta.

**Por que duas chamadas à API por ticker?**
A primeira usa `web_fetch` para extrair indicadores de páginas financeiras (extração estruturada, sem análise). A segunda recebe os indicadores + títulos das notícias e gera a análise completa. Isso minimiza o consumo de tokens.

## Variáveis de Ambiente

| Variável | Descrição | Obrigatória |
|---|---|---|
| `ANTHROPIC_API_KEY` | Chave de API da Anthropic | Sim |

## Lista de Ativos

Os tickers monitorados estão em `data/ativos.txt` no formato `TICKER|Nome da Empresa`. Para adicionar ou remover ativos, edite esse arquivo.

## Dependências

Definidas em `requirements.txt`:

- `anthropic` — SDK oficial da API Claude
- `feedparser` — Parsing de feeds RSS
- `python-dotenv` — Carregamento de variáveis do `.env`

## Licença

Projeto desenvolvido exclusivamente para o processo seletivo Charles River 2026.1.
