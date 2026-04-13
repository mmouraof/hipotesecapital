# Avaliacao - Janys Guenn

**Repositorio:** https://github.com/Jancice/Case-Janys
**Commits:** 7 (incluindo Initial commit)

---

## 1. Qualidade do Prompt / LLM Engineering (Fase 1)

**Nota do criterio: 3.5/5**

O prompt em `ai_analyzer.py` usa Groq (llama-3.3-70b-versatile) com persona de "Analista de Acoes Senior na gestora Hipotese Capital (foco em Value Investing)".

**Pontos positivos:**
- Menciona "Value Investing", "alta conviccao", "protecao de downside" e "qualidade do negocio"
- System prompt como "API de processamento de dados financeiros" — forca resposta estritamente JSON
- `response_format={"type": "json_object"}` garante JSON valido
- Temperature 0.1 para output deterministico
- Instrucao inteligente: "Utilize os campos 'setor_origem' e 'industria_origem' fornecidos. Nao tente adivinhar ou traduzir"
- Instrucao para nao fazer recomendacoes de compra/venda
- Classificacao individual de noticias com sentimento e justificativa

**Pontos negativos:**
- Sem instrucao anti-alucinacao explicita ("nao fabrique dados")
- Prompt curto para o system message — nao define a gestora ou filosofia no system, so no user prompt
- Sem thresholds de indicadores (ex: ROE >15% bom, Divida/Equity >2x perigoso)
- Sem instrucao sobre como tratar dados faltantes ("N/D")

---

## 2. Coleta Automatizada e Fontes de Dados (Fase 1)

**Nota do criterio: 4/5**

**Fontes utilizadas:**
- Fundamentus (web scraping via requests + BeautifulSoup) — setor, subsetor, indicadores de mercado
- yfinance — fallback para dados cadastrais + EBITDA + descricao do negocio
- Google News RSS via feedparser — noticias recentes

**Indicadores cobertos:** Cotacao, P/L, ROE, Margem Liquida, Dividend Yield, Divida Liq./EBITDA — todos os 5 solicitados.

**Diferenciais tecnicos:**
- Calculo derivado de Divida Liq./EBITDA: busca divida liquida no Fundamentus e EBITDA no yfinance, calcula manualmente; fallback para campo pronto do Fundamentus
- `limpar_numero()` trata formatacao brasileira (pontos de milhares, virgula decimal, percentagem)
- User-Agent customizado para scraping
- Busca de classificacao B3 (setor/subsetor) diretamente no Fundamentus

**Pontos negativos:**
- Fundamentus e bloqueado por Cloudflare em muitos ambientes — fallback funciona mas perde a classificacao B3 (retorna em ingles via yfinance)
- Logging do erro do Fundamentus e muito verboso (despeja HTML inteiro da pagina)
- Sem retry/backoff para requests HTTP
- Sem cache de tickers validos
- bare `except:` em `buscar_dados_cadastrais` (linha 58)

---

## 3. Interface e Usabilidade (Fase 1)

**Nota do criterio: 3.5/5**

Dashboard Streamlit com:
- Input de ticker (text_input com uppercase automatico)
- Botao "Gerar Analise IA"
- Layout em duas colunas: sintese IA (esquerda) + dados brutos (direita)
- Metricas em grid: Cotacao, P/L, ROE, Margem Liq., DY, Divida/EBITDA
- Noticias com links clicaveis
- Classificacao individual de noticias com emojis de sentimento
- Perguntas investigativas do analista
- Historico do banco de dados exibido como DataFrame no rodape
- Cache Streamlit para coleta e LLM (`@st.cache_data`)

**Pontos positivos:**
- Interface limpa e funcional
- Validacao de ticker (detecta ativo invalido pelo par cotacao=N/D + nome=N/D, usa `st.stop()`)
- Formatacao brasileira de numeros (`formatar_valor` com R$, %, multiplos)
- Historico persistente exibido no dashboard

**Pontos negativos:**
- Sem graficos de preco/retorno
- Sem comparacao entre tickers
- Sem opcao de export para PDF
- Sem branding visual customizado (usa Streamlit padrao)

---

## 4. Modelagem do Banco de Dados e Pipeline (Fase 2)

**Nota do criterio: 3.5/5**

**Estrutura SQLite:**
- `empresas` (permanente) — ticker PK, nome, setor_origem, industria_origem
- `historico_analises` (temporal) — autoincrement ID, ticker FK, data_execucao, cotacao_atual, p_l, sintese_ia, classificacao_b3

**Pontos positivos:**
- Separacao clara entre dados estaticos e temporais (documentada no README)
- `INSERT OR IGNORE` para empresas (nao duplica dados fixos)
- `INSERT` sempre para historico (preserva historico entre execucoes)
- Foreign key definida
- JOIN entre tabelas para exibicao no dashboard
- Dados formatados para leitura humana no DataFrame

**Pontos negativos:**
- Historico salva apenas cotacao_atual, p_l e sintese_ia — perde ROE, margem, DY, divida/ebitda
- `p_l` armazenado como TEXT (dificulta queries numericas)
- `hipotese_capital.db` commitado no repositorio (deveria estar no .gitignore)
- Sem migracoes versionadas
- Sem indices alem das PKs
- Sem tabela de noticias separada
- `INSERT OR IGNORE` para empresas nunca atualiza dados cadastrais (nome/setor) se a empresa ja existir — deveria ser `INSERT OR REPLACE` ou UPSERT

---

## 5. Tratamento de Erros e Robustez (Fase 2)

**Nota do criterio: 3.5/5**

**Cobertura dos 3 casos obrigatorios:**
- API fora do ar: Fallback Fundamentus → yfinance para dados cadastrais; try/except com logging em toda coleta
- Ticker invalido: Validacao no app.py (`cotacao_atual == "N/D" and nome == "N/D"`) com `st.stop()` fail-fast
- Resposta LLM fora do formato: `response_format={"type": "json_object"}` garante JSON; try/except retorna `{"erro": ...}`

**Pontos positivos:**
- **Logging consistente** (logging.basicConfig no data_fetcher.py)
- Fallback de dados cadastrais bem implementado
- Calculo derivado de Divida/EBITDA com multiplas tentativas (manual + campo pronto)
- Pattern fail-fast com `st.stop()` para tickers invalidos
- Mensagens de erro user-friendly no Streamlit

**Pontos negativos:**
- bare `except:` sem tipo de excecao em `buscar_dados_cadastrais` (linha 58)
- Sem retry/backoff para APIs
- Sem exception customizada para LLM
- Erro do Fundamentus despeja HTML inteiro no log (deveria ser truncado)

---

## 6. Documentacao e Versionamento (Fases 1 e 2)

**Nota do criterio: 2.5/5**

**README:**
- Descreve arquitetura em 4 modulos, requisitos e instrucoes de setup
- Setup basico mas completo (install, .env, streamlit run)
- Menciona Groq como provedor e link para obter API key
- Arquivo sem extensao `.md` — nao renderiza formatacao no GitHub

**Versionamento:**
- 7 commits incluindo Initial commit
- Progressao clara: primeira versao → Fase 1 melhorada → Fase 2 (3 versoes) → Fase 3
- Mensagens descritivas em portugues

**Problemas:**
- `.env` commitado no repositorio (chave Groq API exposta!) — apesar do `.gitignore` listar `.env`
- `__pycache__` commitado (apesar do `.gitignore` listar)
- `hipotese_capital.db` commitado (banco com dados de execucoes anteriores)
- `banco_vetorial_simples/chroma.sqlite3` commitado (vector store)
- Dois arquivos `requirements.txt` e `requirements (1).txt` — confuso
- `readme` sem extensao `.md`
- Poucos commits (7) para o escopo entregue

---

## 7. Visao Arquitetural e RAG (Fase 3)

**Nota do criterio: 4/5**

Implementacao funcional de RAG com ChromaDB em `app_rag.py`:

**Documentos ficticios (6 memos):**
- memo_energia_2010.txt, memo_eletrica_2021.txt, memo_energia_2025.txt
- memo_bancos_2023.txt, memo_saneamento_2023.txt, memo_varejo_2022.txt
- Cobertura diversificada de setores e periodos temporais

**Pipeline RAG:**
- ETL: extracao de metadados (ano, setor) via regex + keywords
- Chunking: fragmentos de 150 palavras
- Vetorizacao: ChromaDB PersistentClient com upsert (idempotente)
- Busca: 10 resultados de similaridade vetorial
- **Reranking via LLM**: IA filtra fragmentos por setor e prioriza mais recentes
- Parsing estruturado da resposta (LAUDO_DE_RELEVANCIA + FONTES_UTILIZADAS + RESPOSTA)

**Pontos positivos:**
- Conceito de reranking via LLM e sofisticado e bem implementado
- Metadados enriquecidos (ano, setor) permitem filtragem inteligente
- Fontes utilizadas sao rastreadas e exibidas ao usuario
- Laudo de relevancia mostra o raciocinio da IA
- Memos ficticios demonstram evolucao temporal de teses de investimento
- Interface separada e funcional

**Pontos negativos:**
- App RAG (`app_rag.py`) nao integrado com o app principal (`app.py`)
- Extracao de setor e rudimentar (keywords hardcoded) — nao detecta "bancos"
- Embeddings defaultam para o modelo nativo do ChromaDB (sem fine-tuning)
- `requirements.txt` principal nao inclui chromadb — so o `requirements (1).txt`

---

## 8. Resultado da Execucao (13/abr/2026)

**Ambiente:** Python 3.13, Windows 11, Groq API key

**Instalacao:** `pip install -r requirements.txt` — sucesso sem erros (8 pacotes limpos)

**Coleta de dados:** FUNCIONAL
- Fundamentus retornou Cloudflare challenge (403) — fallback yfinance acionado automaticamente
- yfinance retornou: nome, setor (Energy), industria (Oil & Gas Integrated), descricao, cotacao (R$49.03), P/L (5.74), ROE (26.5%), Margem Liq. (22.2%), DY (6.6%), Divida/EBITDA (1.60)
- Google News RSS retornou 5 noticias recentes em portugues
- Todos os 5 indicadores do case cobertos

**LLM (Groq / Llama 3.3 70b):** FUNCIONAL
- Resposta JSON estruturada com todas as chaves esperadas
- classificacao_b3, resumo_negocio, interpretacao_indicadores, analise_noticias (classificacao_individual + sintese_geral), perguntas_investigacao
- Classificacao individual de 5 noticias com sentimento e justificativa

**Banco de dados:** FUNCIONAL
- Tabelas criadas automaticamente
- PETR4 salvo com sucesso (empresa + historico)
- Banco pre-existente (commitado): 5 empresas, 9 analises historicas
- Historico preservado entre execucoes (confirmado: VALE3 com 3 entradas em datas diferentes)

**RAG (Fase 3):** FUNCIONAL
- 6 chunks indexados no ChromaDB a partir de 6 memos ficticios
- Query "energia" retorna corretamente os 3 memos de energia no topo
- Requer `pip install chromadb` separado (nao esta no requirements.txt principal)

---

## Nota Final: 3.5/5

A candidata entregou as **tres fases do case** (unica entre os candidatos que usa Groq a entregar Fase 3). O pipeline funciona end-to-end: coleta de dados com fallback, LLM gera analise estruturada, banco persiste historico, e RAG com ChromaDB e reranking funciona.

O prompt menciona value investing e protecao de downside, mas poderia ser mais prescritivo. A coleta de dados e diversificada (Fundamentus + yfinance + Google News) com fallback funcional. O banco de dados separa dados estaticos e temporais corretamente, mas perde indicadores importantes no historico (so salva cotacao e P/L). A interface Streamlit e funcional mas basica.

O diferencial da Fase 3 (RAG com reranking via LLM) e bem implementado e demonstra visao arquitetural. Porem, problemas de higiene de codigo (`.env` com API key commitada, DB commitado, `__pycache__`, dois requirements.txt, readme sem extensao) e poucos commits (7) reduzem a nota.

**Diferenciais:** Pipeline end-to-end funcional, RAG com ChromaDB e reranking via LLM (Fase 3), fallback Fundamentus→yfinance, calculo derivado de Divida/EBITDA, logging consistente, response_format JSON, Groq gratuito
**Lacunas:** .env commitada (API key exposta), DB e __pycache__ commitados, historico perde indicadores (so cotacao+P/L), readme sem .md, dois requirements.txt, poucos commits, sem graficos, sem retry/backoff, Fundamentus bloqueado por Cloudflare
