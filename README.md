# Hipótese Capital — Briefing Automatizado

Ferramenta interna que gera relatórios automatizados de ativos para a reunião de comitê da segunda-feira. Dado um ticker, entrega: resumo do negócio, indicadores fundamentalistas interpretados, notícias recentes classificadas por impacto e três perguntas investigativas.

Desenvolvido como case técnico para a posição de Data Science & AI na Hipótese Capital.

## Início Rápido

### Pré-requisitos

- Python 3.11+
- Uma API key da [Anthropic](https://console.anthropic.com/)
- Uma API key da [OpenAI](https://platform.openai.com/)
- Uma API key da [GoogleAI](https://aistudio.google.com/)

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
GOOGLE_API_KEY=sua-chave-aqui     
```

> **Segurança:** O arquivo `.env` está no `.gitignore` e nunca será commitado. Nunca compartilhe sua chave diretamente no código ou em commits.

### Execução completa (coleta + análise + dashboard)

```bash
python src/main.py
```

O script coleta os dados, gera as análises via API, salva um snapshot no banco SQLite e monta o dashboard em `dashboard/output/index.html`. Abra esse arquivo diretamente no navegador — nenhum servidor local é necessário. Ao final da execução, o arquivo é aberto automaticamente no navegador padrão.

### Regenerar dashboard sem coletar dados novos

```bash
# Dashboard da última execução armazenada no banco
python src/main.py --apenas-dashboard

# Dashboard de uma data específica
python src/main.py --data 2026-03-14
```

Antes de iniciar a coleta, o script exibe uma etapa interativa no terminal para revisar os ativos. Digite a letra do comando desejado e pressione Enter:

- **A** — adicionar um ativo à lista (o terminal pedirá o ticker e o nome da empresa, um por vez)
- **R** — remover um ativo da lista (o terminal pedirá o ticker ou o nome da empresa)
- **G** — gerar o relatório com a lista atual (o terminal exibirá a lista final e pedirá confirmação: **S** para gerar, **N** para voltar)

Caso não haja nenhum input por 1 minuto, o relatório é gerado automaticamente com a lista atual. A lista confirmada é salva automaticamente em `data/ativos.txt`.

### Testar o dashboard sem rodar o pipeline

Para visualizar o layout sem consumir a API, abra `dashboard/index_mock.html` diretamente no navegador. Ele contém dados fictícios de 3 ativos (PRIO3, ITUB4, SLCE3) já embutidos e funciona offline.

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
│   ├── briefing.db             # Banco SQLite local (gerado automaticamente, no .gitignore)
│   └── output/                 # JSONs gerados (backup por execução, no .gitignore)
├── src/
│   ├── main.py                 # Orquestrador principal
│   ├── database.py             # Persistência SQLite e consulta a dados históricos
│   ├── coleta_indicadores.py   # Scraping do Fundamentus + fallbacks
│   ├── coleta_noticias.py      # Coleta de notícias via RSS (Google News)
│   ├── analise_llm.py          # Análise e seleção de indicadores via Claude, GPT e Gemini
│   └── gera_dashboard.py       # Injeta dados no template HTML
└── dashboard/
    ├── template.html           # Template com placeholder para dados
    ├── index_mock.html         # Versão com dados mock para testes (abrir no navegador)
    └── output/                 # HTML gerado pelo pipeline (criado na primeira execução)
```

### Fluxo de dados

```
ativos.txt → coleta_indicadores.py  (scraping Fundamentus → Investidor10 → GPT-4o)
                                     → indicadores completos em JSON
           → coleta_noticias.py     (RSS Google News)
                                     → notícias em JSON
           → analise_llm.py         (Claude Sonnet  → análise A)
                                     (GPT-4o         → análise B)
                                     (Gemini 2.5 Flash → síntese de A+B)
                                     → análise final + indicadores_dashboard selecionados
           → database.py            → snapshot salvo em data/briefing.db (SQLite)
           → data/output/YYYY-MM-DD.json   (backup legível por execução)
           → gera_dashboard.py      → consulta histórico do banco por ticker
           → dashboard/output/index.html   (histórico embutido no JSON)
```

### Coleta de indicadores

A coleta segue uma estratégia em três estágios:

1. **Scraping do Fundamentus (primário):** extrai diretamente a página `fundamentus.com.br/detalhes.php` via `curl_cffi` + `BeautifulSoup`. O `curl_cffi` impersona o TLS do Chrome, contornando a proteção Cloudflare que bloqueia bibliotecas HTTP convencionais (`requests`, `httpx`) quando executadas em IPs de datacenter — como GitHub Codespaces, Google Cloud Run ou AWS. Retorna o conjunto completo de indicadores: cotação, valuation (P/L, P/VP, EV/EBITDA…), rentabilidade (ROE, ROIC, margens…), balanço patrimonial e demonstrativo de resultados.

2. **Scraping do Investidor10 (fallback):** acionado se o Fundamentus falhar. Extrai os cards do topo (cotação, P/L, P/VP, DY), indicadores fundamentalistas com comparativos por setor/subsetor, histórico de dividendos e informações cadastrais da empresa. Também usa `curl_cffi` para contornar eventuais bloqueios.

3. **GPT-4o com web search (último recurso):** acionado se ambos os scrapings falharem e `OPENAI_API_KEY` estiver configurada. Usa a Responses API da OpenAI com `web_search_preview` para buscar os mesmos indicadores em B3, Fundamentus, Status Invest e Yahoo Finance, com limite de tokens para controle de custo.

### Análise em três modelos

A etapa de análise executa um pipeline de três modelos em sequência:

1. **Claude Sonnet** e **GPT-4o** recebem o mesmo prompt de análise de forma independente, cada um produzindo: resumo do negócio, interpretação dos indicadores, seleção de indicadores para o dashboard, classificação de sentimento das notícias e perguntas investigativas.

2. **Gemini 2.5 Flash** recebe as duas análises e as sintetiza — sem gerar dados novos. Sua única função é selecionar e combinar o melhor conteúdo já produzido: resume o negócio em exatamente 3 frases, divide a interpretação dos indicadores em 3 seções temáticas (Valuation, Rentabilidade, Endividamento), classifica o ativo como *atrativo*, *neutro* ou *cautela* com justificativa, copia o `indicadores_dashboard` do Claude sem alteração (pois vem de dados reais do scraping), seleciona o sentimento mais bem fundamentado para cada notícia e escolhe as 3 perguntas mais relevantes e distintas entre as 6 disponíveis.

Se GPT-4o ou Claude Sonnet falharem, o pipeline degrada graciosamente seguindo a ordem de preferência para o enriquecimento: **Gemini 2.5 Flash** (síntese completa) → **Claude Haiku** (enriquecimento leve) → **GPT-4o-mini** (enriquecimento leve, acionado se Haiku falhar e `OPENAI_API_KEY` estiver disponível) → análise Claude no formato original (sem classificação nem sub-seções). O enriquecimento leve (Haiku ou GPT-mini) adiciona apenas a classificação semáforo e a divisão da interpretação em 3 seções temáticas, sem gerar dados novos.

### Seleção de indicadores para o dashboard

Claude e GPT-4o recebem o conjunto bruto completo de indicadores (incluindo DRE e balanço) e cada um seleciona entre 8 e 12 dos mais relevantes para value investing. O Gemini preserva a seleção do Claude no campo `indicadores_dashboard`, que é exibido diretamente no dashboard.

### Dashboard

O dashboard abre na tela de **Visão Geral**, exibindo a tabela resumida de todos os ativos com cotação e semáforo. Ao clicar em um ativo, a visualização detalha:

- **Semáforo** (*atrativo* / *neutro* / *cautela*) com razão em uma frase, exibido no cabeçalho
- **Interpretação em 3 seções**: Valuation, Rentabilidade e Endividamento
- **Notícias** com badge de sentimento, fonte, data e justificativa de impacto
- **Histórico**: tabela com as execuções anteriores do ativo (cotação, P/L, Div. Yield, classificação por data)

Em dispositivos móveis, a barra lateral é ocultada e acessível via botão de menu.

### Decisões técnicas

**Por que HTML autocontido em vez de Streamlit?**
O avaliador abre o arquivo no navegador sem instalar nada e sem rodar um servidor. O `main.py` injeta os dados diretamente no HTML como objeto JavaScript, eliminando problemas de CORS com `file://`. Separação clara entre backend (Python coleta e analisa) e frontend (HTML renderiza).

**Por que RSS para notícias em vez de web scraping?**
Google News RSS é gratuito, estável e não requer parsing de HTML frágil. Retorna título, link, data e fonte. A classificação de sentimento é feita pelo LLM na etapa de análise, não na coleta.

**Por que três modelos diferentes (Claude, GPT-4o e Gemini)?**
Cada modelo tem pontos fortes distintos na análise textual; usar dois modelos independentes para a análise e um terceiro para arbitrar e sintetizar reduz vieses individuais e tende a produzir textos mais equilibrados. O Gemini atua como editor — não como analista —, garantindo que nenhum dado seja fabricado fora dos dados de mercado coletados. O GPT-4o também serve como fallback de coleta de indicadores quando o scraping falha, aproveitando sua integração nativa com web search.

**Por que SQLite em vez de apenas arquivos JSON?**
O case exige versionamento temporal (dados de hoje não sobrescrevem os de ontem) e consulta a dados históricos no dashboard. O SQLite resolve ambos sem dependências externas: cada execução cria um snapshot por ticker na tabela `ativos_snapshot`, e queries com `JOIN` permitem recuperar o histórico de qualquer ativo nas últimas N execuções. O JSON em `data/output/` é mantido como backup legível por execução. O banco é criado automaticamente em `data/briefing.db` na primeira execução e está no `.gitignore`.

**Por que `curl_cffi` em vez de `requests` para o scraping?**
O Fundamentus é protegido por Cloudflare, que bloqueia requisições HTTP comuns vindas de IPs de datacenter com um desafio 403. O `curl_cffi` impersona o fingerprint TLS do Chrome, fazendo a requisição parecer um navegador real e contornando o bloqueio sem necessidade de Selenium ou Playwright.

**Como o pipeline lida com respostas fora do formato esperado do LLM?**
LLMs ocasionalmente retornam texto introdutório, blocos de código markdown (` ```json `) ou comentários após o JSON, mesmo quando instruídos a não fazê-lo. Em vez de depender de heurísticas frágeis como `startswith("```")`, o parser usa `re.search(r"\{.*\}", texto, re.DOTALL)` para extrair o bloco JSON mais externo da resposta completa, ignorando qualquer conteúdo antes ou depois das chaves. Se nenhum bloco for encontrado, a exceção é capturada e o ativo é marcado com `{"erro": ...}` sem interromper o pipeline dos demais.

## Variáveis de Ambiente

| Variável | Descrição | Obrigatória |
|---|---|---|
| `ANTHROPIC_API_KEY` | Chave de API da Anthropic (análise via Claude Sonnet + enriquecimento via Haiku) | Sim* |
| `OPENAI_API_KEY` | Chave de API da OpenAI (análise via GPT-4o + enriquecimento via GPT-mini + fallback de coleta) | Sim* |
| `GOOGLE_API_KEY` | Chave de API do Google (síntese via Gemini 2.5 Flash) | Não** |

*Pelo menos uma das duas é obrigatória. Com apenas `ANTHROPIC_API_KEY`: análise via Claude Sonnet, enriquecimento via Haiku. Com apenas `OPENAI_API_KEY`: análise via GPT-4o, enriquecimento via GPT-mini. Com ambas: Claude e GPT-4o analisam em paralelo; se `GOOGLE_API_KEY` também estiver presente, Gemini sintetiza as duas análises.

**Se `GOOGLE_API_KEY` não estiver configurada, a síntese Gemini é desativada e GPT-4o não é chamado para análise quando Claude estiver disponível.

## Lista de Ativos

Os tickers monitorados estão em `data/ativos.txt` no formato `TICKER|Nome da Empresa`. Para adicionar ou remover ativos, edite esse arquivo ou use a etapa interativa no terminal ao executar `main.py`.

## Dependências

Definidas em `requirements.txt`:

- `anthropic` — SDK oficial da API Claude (análise fundamentalista)
- `openai` — SDK oficial da API OpenAI (análise GPT-4o + fallback de coleta)
- `google-genai` — SDK oficial do Google (síntese via Gemini 2.5 Flash)
- `curl_cffi` — Requisições HTTP com impersonação de TLS do Chrome (contorna Cloudflare no Fundamentus)
- `beautifulsoup4` — Parsing do HTML do Fundamentus
- `feedparser` — Parsing de feeds RSS
- `python-dotenv` — Carregamento de variáveis do `.env`

## Licença

Projeto desenvolvido exclusivamente para o processo seletivo Charles River 2026.1.
