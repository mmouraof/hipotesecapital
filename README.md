# Hipótese Capital — Briefing Automatizado

Ferramenta interna que gera relatórios automatizados de ativos para a reunião de comitê da segunda-feira. Dado um ticker, entrega: resumo do negócio, indicadores fundamentalistas interpretados, notícias recentes classificadas por impacto e três perguntas investigativas.

Desenvolvido como case técnico para a posição de Data Science & AI na Hipótese Capital.

## Início Rápido

### Pré-requisitos

- Python 3.11+
- Uma API key da [Anthropic](https://console.anthropic.com/)
- Uma API key da [OpenAI](https://platform.openai.com/)

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

Abra o `.env` e substitua os valores placeholder pelas suas chaves:

```
ANTHROPIC_API_KEY=sk-ant-sua-chave-aqui
OPENAI_API_KEY=sk-sua-chave-aqui
```

> **Segurança:** O arquivo `.env` está no `.gitignore` e nunca será commitado. Nunca compartilhe sua chave diretamente no código ou em commits.

### Execução completa (coleta + análise + dashboard)

```bash
python src/main.py
```

O script coleta os dados, gera as análises via API e monta o dashboard em `dashboard/output/index.html`. Abra esse arquivo diretamente no navegador — nenhum servidor local é necessário. Ao final da execução, o arquivo é aberto automaticamente no navegador padrão.

Antes de iniciar a coleta, o script exibe uma etapa interativa no terminal para revisar os ativos. Digite a letra do comando desejado e pressione Enter:

- **A** — adicionar um ativo à lista (o terminal pedirá o ticker e o nome da empresa, um por vez)
- **R** — remover um ativo da lista (o terminal pedirá o ticker ou o nome da empresa)
- **G** — gerar o relatório com a lista atual (o terminal exibirá a lista final e pedirá confirmação: **S** para gerar, **N** para voltar)

A lista confirmada é salva automaticamente em `data/ativos.txt`.

### Testar o dashboard sem rodar o pipeline

Para visualizar o layout sem consumir a API, abra `dashboard/index_mock.html` diretamente no navegador. Ele contém dados fictícios de 3 ativos (PRIO3, ITUB4, SLCE3) já embutidos e funciona offline.

> `index_mock.html` é gerado a partir do mesmo template, mas com o bloco mock ativo. Não edite `template.html` para isso — o template deve permanecer intacto para o pipeline de produção.

## Usando GitHub Codespaces

O repositório inclui configuração de Dev Container para execução imediata.

1. No GitHub, clique em **Code** → **Codespaces** → **Create codespace on main**
2. Aguarde o setup automático (instala dependências via `requirements.txt`)
3. Configure as API keys de uma das duas formas:
   - **Via Secret (recomendado):** antes de criar o Codespace, vá em Settings → Secrets and variables → Codespaces → New repository secret → adicione `ANTHROPIC_API_KEY` e `OPENAI_API_KEY`
   - **Via `.env`:** no terminal do Codespace, execute `cp .env.example .env` e edite com suas chaves
4. Para visualizar o layout imediatamente (sem consumir a API), baixe `dashboard/index_mock.html` e abra no navegador
5. Para rodar o pipeline completo: `python src/main.py` — ao finalizar, baixe `dashboard/output/index.html` e abra no navegador

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
│   ├── coleta_indicadores.py   # Extração de indicadores via web_search (API OpenAI)
│   ├── coleta_noticias.py      # Coleta de notícias via RSS (Google News)
│   ├── analise_llm.py          # Geração de resumos e insights via API Claude
│   └── gera_dashboard.py       # Injeta dados no template HTML
└── dashboard/
    ├── template.html           # Template com placeholder para dados
    ├── index_mock.html         # Versão com dados mock para testes (abrir no navegador)
    └── output/                 # HTML gerado pelo pipeline (criado na primeira execução)
```

### Fluxo de dados

```
ativos.txt → coleta_indicadores.py (OpenAI web_search) → indicadores em JSON
           → coleta_noticias.py (RSS)                  → notícias em JSON
           → analise_llm.py (Claude API)               → resumos e insights
           → data/output/YYYY-MM-DD.json               → dashboard/output/index.html
```

### Decisões técnicas

**Por que HTML autocontido em vez de Streamlit?**
O avaliador abre o arquivo no navegador sem instalar nada e sem rodar um servidor. O `main.py` injeta os dados diretamente no HTML como objeto JavaScript, eliminando problemas de CORS com `file://`. Separação clara entre backend (Python coleta e analisa) e frontend (HTML renderiza).

**Por que RSS para notícias em vez de web scraping?**
Google News RSS é gratuito, estável e não requer parsing de HTML frágil. Retorna título, link, data e fonte. A classificação de sentimento é feita pelo LLM na etapa de análise, não na coleta.

**Por que duas APIs diferentes (OpenAI e Anthropic)?**
A OpenAI (`gpt-4o` com `web_search_preview`) é usada na coleta de indicadores por ter acesso nativo à web via Responses API. O Claude (`claude-sonnet-4-6`) é usado na análise por sua capacidade de raciocínio estruturado e geração de JSON confiável. Cada chamada tem responsabilidade única, o que facilita substituição ou ajuste individual.

## Variáveis de Ambiente

| Variável | Descrição | Obrigatória |
|---|---|---|
| `ANTHROPIC_API_KEY` | Chave de API da Anthropic (análise via Claude) | Sim |
| `OPENAI_API_KEY` | Chave de API da OpenAI (coleta de indicadores via GPT-4o) | Sim |

## Lista de Ativos

Os tickers monitorados estão em `data/ativos.txt` no formato `TICKER|Nome da Empresa`. Para adicionar ou remover ativos, edite esse arquivo.

## Dependências

Definidas em `requirements.txt`:

- `anthropic` — SDK oficial da API Claude (análise)
- `openai` — SDK oficial da API OpenAI (coleta de indicadores)
- `feedparser` — Parsing de feeds RSS
- `python-dotenv` — Carregamento de variáveis do `.env`

## Licença

Projeto desenvolvido exclusivamente para o processo seletivo Charles River 2026.1.
