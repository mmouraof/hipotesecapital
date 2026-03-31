# Avaliacao - Diego Gadelha

**Repositorio:** https://github.com/DiegoFonseca256/CaseDataScience
**Commits:** 29 (25/mar a 30/mar)

---

## 1. Qualidade do Prompt / LLM Engineering (Fase 1)

**Nota do criterio: 4/5**

O candidato demonstrou boa calibracao do prompt com otica de value investing. O system prompt instrui o LLM a atuar como "analista-chefe" da Hipotese Capital, com enfase em:
- Qualidade do negocio
- Saude financeira
- Valuation
- Catalisadores e riscos

**Pontos positivos:**
- Instrucao explicita: "NUNCA repita los numeros literalmente - interprete o que eles significam"
- Estrutura de output em JSON com campos definidos (resumo, analise fundamental, noticias com sentimento, perguntas)
- Uso do modelo llama-3.3-70b-versatile via Groq (gratuito e rapido)
- Funcoes de formatacao (`_fmt`, `_fmt_grande`, `_variacao_fmt`) para contextualizar dados antes de enviar ao LLM
- Calculo da posicao no range de 52 semanas enviada no prompt

**Pontos negativos:**
- O prompt poderia ser mais especifico sobre a filosofia da gestora (concentrada, long-only, etc.)

---

## 2. Coleta Automatizada e Fontes de Dados (Fase 1)

**Nota do criterio: 3.5/5**

**Fontes utilizadas:**
- yfinance para dados de mercado e cadastrais
- NewsAPI para noticias (requer chave paga para producao; plano gratuito tem limite de 100 req/dia e so funciona em dev)

**Indicadores cobertos:** P/L, ROE, min/max 52 semanas, preco atual, market cap, beta, debt-to-equity, free cashflow, margens EBITDA, margem operacional, liquidez corrente, volume medio.

**Sobre a NewsAPI:**
- O plano Developer e gratuito (100 requests/dia), mas so retorna artigos de ate 1 mes atras
- Em producao, seria necessario plano pago ($449/mes para Business)
- O codigo trata graciosamente a ausencia da chave (`if not NEWS_API_KEY: logger.warning(...)`)

**Pontos negativos:**
- Pouca diversificacao de fontes (basicamente so yfinance + NewsAPI)
- Nao usa Fundamentus, Status Invest, CVM ou B3 diretamente
- Sem fallback se yfinance falhar
- Dividend Yield e coberto mas depende do yfinance

---

## 3. Interface e Usabilidade (Fase 1)

**Nota do criterio: 3.5/5**

Dashboard Streamlit com:
- Seletor de ticker no sidebar com fila de pendentes via `pendentes.txt`
- Metricas em 6 colunas (Market Cap, P/L, ROE, DY, Debt/Equity, Beta)
- Barra de progresso para range 52 semanas
- Grafico interativo Plotly com periodos selecionaveis
- Cards de noticias com badges de sentimento
- Secao de analise LLM com resumo e perguntas
- Cache de 10 minutos para performance

**Pontos positivos:**
- Interface rica e pensada para o analista
- Validacao de chaves API no dashboard

**Pontos negativos:**
- A fila de tickers via `pendentes.txt` e fragil (sem concorrencia, sem lock)

---

## 4. Modelagem do Banco de Dados e Pipeline (Fase 2)

**Nota do criterio: 3.5/5**

**Estrutura SQLite:**
- `empresas` (estatica) - ticker PK, nome, setor, segAtuacao, descricao
- `snapshots` (temporal) - autoincrement, data_coleta, todos os indicadores + resumo_llm e analise_llm
- `noticias_historico` (temporal) - autoincrement, data, titulo, fonte, sentimento, url

**Pontos positivos:**
- Separacao explicita entre dados estaticos e dinamicos (documentada no docstring)
- Garantia declarada: "Rodadas subsequentes NUNCA sobrescrevem dados anteriores"
- WAL mode e foreign keys habilitados
- Context manager com rollback automatico

**Pontos negativos:**
- A tabela `snapshots` mistura dados de mercado E resultados do LLM na mesma linha - deveria separar
- Nao ha tabela de `pipeline_runs` para rastrear execucoes
- `resumo_llm`, `analise_llm` e `perguntas_json` na tabela de snapshots e uma violacao de normalizacao
- O `salvar_snapshot_no_db()` no main.py tem o corpo como `pass` (nao implementado!)

---

## 5. Tratamento de Erros e Robustez (Fase 2)

**Nota do criterio: 4/5**

**Cobertura dos 3 casos obrigatorios:**
- API fora do ar: `try/except` com `logger.error()` em todas as funcoes de coleta; NewsAPI trata timeout de 10s
- Ticker invalido: Nao ha validacao explicita, mas erros sao logados
- Resposta LLM fora do formato: Retry com backoff exponencial e deteccao de rate-limit 429

**Pontos positivos:**
- **Uso consistente de logging** em vez de print (logging.basicConfig configurado)
- Retry com backoff exponencial para o LLM (extrai tempo de espera sugerido do erro 429)
- Tratamento de dados nulos com `pd.to_numeric(errors="coerce")`
- Pipeline reporta sucessos vs total ao final

**Pontos negativos:**
- `salvar_snapshot_no_db()` esta com `pass` - dados nao sao persistidos!
- Falta validacao do JSON retornado pelo LLM

---

## 6. Documentacao e Versionamento (Fases 1 e 2)

**Nota do criterio: 3/5**

**README:**
- Descreve proposito, arquitetura e setup
- Falta detalhes do codigo (conforme observado - "pior que o Alex Oliveira")
- Menciona dependencias mas sem explicacao detalhada da estrutura

**Versionamento:**
- 29 commits progressivos ao longo de 5 dias - bom ritmo
- Mensagens em portugues, descritivas
- Evolucao clara: coleta -> LLM -> dashboard -> banco de dados -> logging

---

## 7. Visao Arquitetural e RAG (Fase 3)

Nao implementado.

---

## Nota Final: 3.5/5

O candidato demonstrou bom dominio do prompt engineering com calibracao para value investing, e e o unico que implementou logging consistente desde o inicio. A interface Streamlit e rica e funcional. Porem, ha um problema critico: a funcao `salvar_snapshot_no_db()` tem corpo `pass`, significando que os dados temporais provavelmente nao estao sendo persistidos no banco. A modelagem do banco mistura dados de mercado com output do LLM na mesma tabela. A diversificacao de fontes e limitada (so yfinance + NewsAPI).

**Diferenciais:** Logging consistente, retry com backoff para LLM, prompt bem calibrado para value investing, uso de Groq (gratuito)
**Lacunas:** Funcao de persistencia nao implementada (pass), README fraco, pouca diversificacao de fontes, NewsAPI com limitacoes no plano gratuito
