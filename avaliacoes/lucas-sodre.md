# Avaliacao - Lucas Sodre

**Repositorio:** https://github.com/sodrelds/Dashboard-B3
**Commits:** 23 (26/mar a 30/mar)

---

## 1. Qualidade do Prompt / LLM Engineering (Fase 1)

**Nota do criterio: 3/5**

O prompt no `report_generator.py` e funcional mas generico:
- System prompt: "Voce e um analista financeiro senior. Gere um relatorio em portugues do Brasil, com linguagem objetiva e sem recomendar compra ou venda."
- Pede 4 secoes: resumo do negocio, interpretacao de indicadores, sintese de noticias por sentimento, 3 perguntas
- "Interprete os indicadores (nao apenas repita numeros)"

**Pontos positivos:**
- Instrucao para interpretar, nao repetir numeros
- Estrutura de output em Markdown com secoes definidas
- Temperature 0.2 para output mais deterministico
- Gemini Flash (gratuito)

**Pontos negativos:**
- Prompt nao menciona value investing, protecao de downside ou qualidade do negocio
- Nao ha instrucao anti-alucinacao
- System prompt muito curto e generico
- Sem instrucao sobre como tratar dados faltantes
- Poderia ser o output de qualquer analista, sem calibracao para a gestora

---

## 2. Coleta Automatizada e Fontes de Dados (Fase 1)

**Nota do criterio: 4/5**

**Fontes utilizadas:**
- Yahoo Finance (yfinance) - precos, indicadores, historico
- Fundamentus API (`fundamentus_api.py`) - indicadores complementares
- Google News RSS + Yahoo News - dual source com fallback
- Dados de Mercado (fonte de tickers, substituindo InfoMoney)

**Indicadores cobertos:** P/L, ROE, Divida/Equity, Margem Liquida, DY, preco atual, moeda.

**Pontos positivos:**
- Multiplas fontes com fallback (Google News + Yahoo News)
- API do Fundamentus como fonte complementar
- Funcao `summarize_price_data` para contextualizar dados de preco
- Calculo de variacao percentual no periodo

**Pontos negativos:**
- Chamada direta a API do Gemini via urllib (sem SDK) - fragil
- Noticias limitadas a 8 items

---

## 3. Interface e Usabilidade (Fase 1)

**Nota do criterio: 3.5/5**

Dashboard Streamlit mencionado no README com visualizacao de dados atuais e historicos. O `dashboard.py` (nao analisado em detalhe) aparenta ter interface funcional.

**Pontos positivos:**
- Separacao entre `pipeline_runner.py` (coleta) e `dashboard.py` (visualizacao)
- O analista pode rodar o pipeline e depois consultar o dashboard

**Pontos negativos:**
- Dois comandos separados para usar (pipeline + dashboard)
- Nao e one-click: precisa rodar o pipeline antes

---

## 4. Modelagem do Banco de Dados e Pipeline (Fase 2)

**Nota do criterio: 4.5/5**

**Estrutura SQLite com 5 tabelas:**
- `companies` (permanente) - ticker, nome, setor, industria, descricao
- `pipeline_runs` (meta) - rastreia cada execucao com status, timestamps, contagem de erros
- `fundamentals_snapshots` (temporal) - indicadores por run_id
- `news_snapshots` (temporal) - noticias por run_id
- `llm_reports` (temporal) - relatorios LLM por provider/model e run_id
- 3 indices de performance

**Pipeline (`pipeline_runner.py`):**
- **ThreadPoolExecutor** para coleta paralela (configuravel, default 8 workers)
- Argparse com flags: `--no-llm`, `--no-news`, `--workers`, `--period`, `--limit`, `--progress-every`
- Pipeline registra run_id, conta processados vs erros, finaliza com status
- Persistencia no thread principal (evita problemas de concorrencia SQLite)

**Pontos positivos:**
- **Diferentes modos do pipeline** (conforme diferencial observado): com/sem LLM, com/sem noticias, paralelo configuravel
- `pipeline_runs` para rastrear cada execucao - excelente para auditoria
- Relatorios LLM separados com provider e model registrados
- Timestamps UTC ISO para consistencia
- Upsert para companies
- Snapshots imutaveis (nunca sobrescreve)

**Pontos negativos:**
- Sem migracoes versionadas
- `pipeline.sqlite3` commitado no repo (deveria estar no .gitignore)

---

## 5. Tratamento de Erros e Robustez (Fase 2)

**Nota do criterio: 3.5/5**

**Cobertura dos 3 casos obrigatorios:**
- API fora do ar: Try/except por ticker com contagem de erros; `HTTPError` tratado na chamada Gemini
- Ticker invalido: `if not info_dict` retorna `{"ok": False, "error": "missing_info"}`
- Resposta LLM fora do formato: Try/except na chamada Gemini com `err_body` detalhado

**Pontos positivos:**
- Pipeline reporta status final ("finished" vs "finished_with_errors")
- Notas registradas quando LLM e desabilitado
- Erro por ticker nao interrompe o pipeline inteiro
- Progress logging a cada N tickers

**Pontos negativos:**
- Usa `print()` em vez de logging
- Chamada HTTP raw ao Gemini (urllib) sem retry
- Sem validacao do JSON retornado pelo LLM

---

## 6. Documentacao e Versionamento (Fases 1 e 2)

**Nota do criterio: 3.5/5**

**README:**
- Descreve objetivos, setup e estrutura do banco
- Instrucoes de configuracao de API key
- Menciona historico temporal e modos do pipeline

**Versionamento:**
- 23 commits ao longo de 4 dias
- Progressao visivel: scraping -> grafico -> noticias -> Gemini -> Fundamentus -> banco -> README
- Mensagens em portugues, descritivas
- `venv/` no repo (deveria estar no .gitignore)

**Problemas de setup (verificado rodando):**
- **Instrucoes exclusivas para Linux sem aviso**: os comandos do README (`python3`, paths de venv, etc.) pressupõem ambiente Linux/Mac sem nenhuma menção — usuario Windows nao consegue seguir as instrucoes diretamente

---

## 7. Visao Arquitetural e RAG (Fase 3)

Nao implementado.

---

## Nota Final: 3.5/5

O candidato entregou um pipeline robusto com o **melhor sistema de modos de execucao** entre todos os avaliados. A capacidade de rodar `--no-llm --no-news --workers 4` demonstra pensamento de engenharia para diferentes cenarios (testes rapidos vs coleta completa). O banco de dados com `pipeline_runs` e snapshots imutaveis e bem modelado. A coleta paralela com ThreadPoolExecutor e um diferencial tecnico.

Porem, o prompt LLM e generico, sem calibracao para value investing. O uso de `print()` e a chamada HTTP raw ao Gemini (sem SDK) reduzem a robustez. O `venv/` e o `pipeline.sqlite3` nao deveriam estar no repositorio. As instrucoes de setup assumem Linux sem aviso — reduz acessibilidade do README.

**Diferenciais:** Pipeline com multiplos modos (--no-llm, --no-news, --workers), coleta paralela ThreadPoolExecutor, pipeline_runs para auditoria, Fundamentus API
**Lacunas:** Prompt generico, print() em vez de logging, venv/ e .sqlite3 no repo, sem testes, chamada HTTP raw ao Gemini, instrucoes de setup exclusivas para Linux sem aviso
