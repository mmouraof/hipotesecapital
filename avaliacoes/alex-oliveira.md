# Avaliacao - Alex Oliveira

**Repositorio:** https://github.com/alexoliveiraFGV24/charles-river-case-dsia
**Commits:** 14 (23/mar a 30/mar)

---

## 1. Qualidade do Prompt / LLM Engineering (Fase 1)

**Nota do criterio: 3.5/5**

O candidato utilizou **duas LLMs** (Gemini para resumo/noticias e Claude para traducao/relatorio), o que demonstra conhecimento de diferentes modelos. O prompt do relatorio final gera um HTML formatado com analise fundamentalista, incluindo indicadores, noticias e perguntas do analista.

**Pontos positivos:**
- Uso de dois modelos diferentes (Gemini + Claude) para tarefas distintas
- Classificacao de noticias com escala de impacto (-1.0 a 1.0)
- Relatorio em HTML formatado para PDF

**Pontos negativos:**
- O prompt nao reflete claramente a otica de value investing (qualidade do negocio, protecao de downside)
- O conteudo do prompt de `generate_ai_report()` foi resumido pelo WebFetch, mas pela descricao parece mais generico do que calibrado para a gestora
- Falta instrucao explicita para o LLM nao fabricar dados

---

## 2. Coleta Automatizada e Fontes de Dados (Fase 1)

**Nota do criterio: 4/5**

Boa diversificacao de fontes com fallback entre dois scrappers.

**Fontes utilizadas:**
- yfinance (scrapper1.py) - dados cadastrais, cotacao, indicadores
- BeautifulSoup/scrapper2.py - backup alternativo
- Status Invest, Investidor 10, B3, TradingView, Fundamentus (mencionados no README)
- Google News RSS para noticias

**Indicadores cobertos:** P/L, ROE, Divida Liq./EBITDA (calculado manualmente), Margem Liquida, Dividend Yield - todos os solicitados.

**Pontos negativos:**
- O calculo de Divida Liquida/EBITDA e manual (`totalDebt - totalCash / ebitda`) - simplificado demais
- Tratamento de ticker invalido e basico (retorna dict vazio)
- `get_full_data()` no scrapper1 retorna `{}` se falhar, mas a logica no database.py chama `s1.get_full_data(ticker)` duas vezes (ineficiente)

---

## 3. Interface e Usabilidade (Fase 1)

**Nota do criterio: 3/5**

O `main.py` apenas chama `generate_dashboard_report()`, indicando uso de Streamlit. O screenshot no `/public/dashboard.png` sugere um dashboard funcional.

**Pontos negativos:**
- O main.py nao tem ponto de entrada claro via Streamlit (o README diz `streamlit run main.py` mas o main.py so importa uma funcao)
- Falta evidencia de que o usuario pode digitar um ticker e receber o relatorio
- A interface parece depender de `generate_dashboard_report()` que nao foi completamente analisada

---

## 4. Modelagem do Banco de Dados e Pipeline (Fase 2)

**Nota do criterio: 4/5**

Boa separacao entre dados permanentes e temporais usando MySQL/MariaDB com SQLAlchemy ORM.

**Estrutura:**
- `Ativos` (permanente) - ticker como PK, empresa, setor, segmento, resumo
- `DadosCotacao` (temporal) - DataConsulta como parte da chave
- `IndicadoresFundamentalistas` (temporal) - DataConsulta como parte da chave
- `Noticias` (temporal) - DataConsulta como parte da chave

**Pontos positivos:**
- Separacao correta entre dados estaticos (Ativos) e temporais (cotacao, indicadores, noticias)
- Upsert para Ativos (so insere se nao existir)
- Foreign keys no Ticker
- Scripts SQL separados (CREATE_TABLES.sql, DROP_TABLES.sql)
- Uso de ORM (SQLAlchemy)

**Pontos negativos:**
- Rodadas subsequentes PODEM sobrescrever dados? Nao ha constraint unico em (DataConsulta, Ticker) visivel no schema
- Falta tabela de relatorios LLM para historico

---

## 5. Tratamento de Erros e Robustez (Fase 2)

**Nota do criterio: 2.5/5**

**Cobertura dos 3 casos obrigatorios:**
- API fora do ar: Fallback entre scrapper1 e scrapper2, mas tratamento generico com `except Exception as e: print(f"Erro em {ticker}: {e}")`
- Ticker invalido: Retorna dict vazio, sem mensagem clara ao usuario
- Resposta LLM fora do formato: Nao ha validacao visivel do output do LLM

**Problemas:**
- Usa `print()` em vez de logging em todo o codigo
- Try/except generico sem especificar tipos de excecao
- Sem retry com backoff para APIs

---

## 6. Documentacao e Versionamento (Fases 1 e 2)

**Nota do criterio: 3.5/5**

**README:**
- Descreve objetivos, stack, setup e execucao
- Faltam detalhes do codigo (conforme observado)
- Template de .env fornecido
- Imagem do dashboard incluida

**Versionamento:**
- 14 commits progressivos ao longo de 7 dias
- Mensagens descritivas em portugues
- Evolucao visivel (estrutura -> scrapper -> banco -> dashboard)

---

## 7. Visao Arquitetural e RAG (Fase 3)

Nao implementado.

---

## Nota Final: 3.5/5

O candidato entregou as fases obrigatorias com qualidade razoavel. A arquitetura com dois scrappers em fallback e banco MySQL com ORM demonstra pensamento de engenharia. O prompt ao LLM e funcional mas nao calibrado para value investing. O tratamento de erros e o ponto mais fraco, com uso extensivo de `print()` e `except Exception` generico. O README poderia ter mais detalhes tecnicos do codigo.

**Diferenciais:** Uso de duas LLMs (Gemini + Claude), MySQL com SQLAlchemy ORM, dois scrappers em fallback
**Lacunas:** Falta logging, tratamento de erros superficial, prompt generico, sem testes
