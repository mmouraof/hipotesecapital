# Avaliacao - Walleria Simoes

**Repositorio:** https://github.com/WalleriaSimoes/CaseDS-AI
**Commits:** 17 (26/mar a 30/mar, com PR fase2)

---

## 1. Qualidade do Prompt / LLM Engineering (Fase 1)

**Nota do criterio: 4.5/5**

O `llm_report.py` usa Gemini 2.5 Flash com um dos melhores prompts entre os candidatos. O texto completo inclui:

- **Regras de seguranca anti-alucinacao**: "Baseie-se ESTRITAMENTE e EXCLUSIVAMENTE nos dados fornecidos", "JAMAIS invente numeros, multiplos ou cite noticias que nao estejam listadas"
- **Framing explicito de value investing**: "analista fundamentalista senior de um fundo de investimentos que segue a filosofia de Value Investing... abordagem bottom-up para identificar ativos cujos precos de mercado estejam consideravelmente inferiores aos seus valores intrinsecos"
- **Instrucao de downside protection**: "priorizando qualidade do negocio e protecao de downside"
- **Interpretacao, nao repeticao**: "Nao apenas liste os numeros. Explique o que eles sugerem. A empresa esta cara ou barata? E rentavel?"
- **Consciencia setorial**: "Considere as particularidades do setor"
- Temperature 0.0 para output deterministico
- Retorna "Dados insuficientes para analise" quando dados sao insuficientes

**Pontos positivos:**
- Um dos poucos prompts que menciona explicitamente valor intrinseco e filosofia de value investing
- Regras de seguranca fortes contra alucinacao
- 4 secoes estruturadas (resumo, indicadores, noticias, checklist do analista)
- Prompt iterativamente melhorado (commit "Added stricter rules for LLM")

**Pontos negativos:**
- Nao menciona margem de seguranca explicitamente
- Sem framework comparativo (setor, peers)
- Nao discute fluxo de caixa livre ou qualidade dos earnings

---

## 2. Coleta Automatizada e Fontes de Dados (Fase 1)

**Nota do criterio: 4/5**

**Fontes utilizadas:**
- Fundamentus (web scraping com BeautifulSoup) - indicadores fundamentalistas, nome, setor, segmento
- yfinance - descricao do negocio (business model) com fallback para banco local
- Google News RSS - noticias recentes (xml.etree.ElementTree)

**Indicadores cobertos:** Cotacao, P/L, ROE (%), Divida Liq./EBITDA (calculado: `ebitda = ev / ev_ebitda; net_debt_ebitda = net_debt / ebitda`), Margem Liquida (%), Dividend Yield (%) - todos os 5 solicitados.

**Diferencial - Tratamento de Intermediarios Financeiros:**
- O codigo distingue entre empresas regulares e bancos
- Deteccao dual: lista hardcoded de tickers bancarios + deteccao dinamica por setor ("Intermediarios Financeiros")
- Para bancos, retorna "N/A (Banco)" para Divida/EBITDA e Margem Liquida
- Funcao `to_float()` trata formatacao brasileira (pontos e virgulas)
- Cache de tickers validos do Fundamentus no banco

**Evolucao tecnica:**
- Pivoteou de BrAPI para web scraping (commit history mostra decisao consciente)
- Calculo derivado de Divida Liq./EBITDA demonstra conhecimento financeiro

**Pontos negativos:**
- Scraping fragil (depende do HTML do Fundamentus)
- Lista hardcoded de bancos incompleta (falta ABCB4, BMGB4, etc.) - deveria confiar mais na deteccao por setor
- Sem retry em requests HTTP (apenas timeout=10)

---

## 3. Interface e Usabilidade (Fase 1)

**Nota do criterio: 4/5**

Dashboard Streamlit com:
- Input de ticker B3 (max 6 caracteres, auto-uppercase)
- Botao "Gerar Relatorio" com `st.status()` mostrando progresso
- Layout adaptativo: 4 colunas para bancos, 6 para empresas regulares
- Historico de dashboards salvos acessivel no sidebar com seletor de datas
- Banner de aviso ao visualizar snapshots arquivados
- Branding Charles River com logo
- Cache de 1 hora para lista de tickers (`@st.cache_data(ttl=3600)`)
- Atribuicao de fontes no footer

**Pontos positivos:**
- Interface pensada para o analista com input direto de ticker
- Renderizacao condicional por tipo de instituicao (banco vs regular) - excelente UX
- Replay completo de historico com re-renderizacao dos dados armazenados
- Links clicaveis para noticias
- **`BM_Source` indicator** (confirmado rodando): o dashboard exibe a origem dos dados do modelo de negocio ("YFinance", "Database Fallback" ou "Failed") e mostra aviso visual em laranja quando usa o fallback - detalhe de UX nao documentado mas bem executado

**Pontos negativos:**
- Sem graficos de preco
- Sem opcao de export para PDF
- Sem comparacao entre tickers

---

## 4. Modelagem do Banco de Dados e Pipeline (Fase 2)

**Nota do criterio: 3.5/5**

**Estrutura SQLite:**
- `valid_tickers` (cache) - ticker + last_updated (DELETE-all + re-INSERT diario)
- `companies` (permanente) - ticker PK, nome, setor, segmento, business_model (INSERT OR REPLACE)
- `market_data` (temporal) - indicadores por data com autoincrement, preserva historico
- `saved_dashboards` (temporal) - snapshot completo em JSON + timestamp

**Pontos positivos:**
- Separacao entre dados estaticos e temporais
- `market_data` preserva historico diario (cada INSERT cria nova linha)
- Snapshots de dashboard em JSON para replay perfeito
- Foreign keys definidas
- Queries parametrizadas (seguro contra SQL injection)

**Pontos negativos:**
- `saved_dashboards` armazena JSON bruto - dificil de consultar/filtrar
- `debt_ebitda` como TEXT (por causa de "N/A (Banco)") - sacrifica capacidade de query
- `companies` usa INSERT OR REPLACE que sobrescreve silenciosamente
- `valid_tickers` usa DELETE-all destructivo em vez de UPSERT
- Sem indices alem das PKs
- Sem migracoes versionadas
- **Duplicatas em `market_data` confirmadas rodando**: sem constraint `UNIQUE(ticker, collection_date)`, duas execucoes no mesmo dia geram duas linhas identicas no banco (verificado: `INSERT` duplo produz 2 rows para WEGE3)
- **Tabela `ai_reports` orffa no banco commitado**: o arquivo `data/equity_research.db` (commitado no repo) contem uma tabela `ai_reports` que nao existe mais no `db_manager.py` - artefato de refactoring nao limpo; indica que o schema do banco e o codigo ficaram dessincronizados
- **`main.py` nao integrado com banco**: o script batch ignora completamente o DB (`save_market_data`, `save_company_static_data`, `save_dashboard_snapshot` nao sao chamados); persiste apenas em Excel - inconsistencia de design entre os dois pontos de entrada da aplicacao

---

## 5. Tratamento de Erros e Robustez (Fase 2)

**Nota do criterio: 4/5**

**Cobertura dos 3 casos obrigatorios (confirmado rodando):**
- API fora do ar: Fallback yfinance -> banco local para business model **confirmado funcionando** (Google News RSS OK; yfinance retornou dados de BBAS3 com sucesso; fallback DB carrega dados salvos quando API falha)
- Ticker invalido: Validacao contra lista do Fundamentus **confirmada** - retorna `"TICKER INVÁLIDO"` para ticker fora da lista de 994 tickers validos
- Resposta LLM fora do formato: Validacao de dados e API key antes da chamada; retorno de mensagens user-friendly

**Pontos positivos:**
- **Logging em vez de print** (commit explicito: "Build the pipeline and add logging instead of print")
- Tratamento especial de intermediarios financeiros (diferencial de dominio)
- Validacao de ticker contra base do Fundamentus
- Fallback em multiplas camadas
- Prompt iterativamente endurecido ("Added stricter rules for LLM")

**Pontos negativos:**
- Sem retry/backoff
- Sem exception customizada para LLM
- `to_float()` definida como funcao aninhada dentro de `collect_data()` - deveria ser utilitario de modulo

---

## 6. Documentacao e Versionamento (Fases 1 e 2)

**Nota do criterio: 3/5**

**README:**
- Descreve as duas fases
- Instrucoes de setup basicas
- Menciona fontes de dados e exemplo de tickers

**Versionamento:**
- 17 commits ao longo de 5 dias
- Uso de branch `fase2` com PR merge - bom workflow
- Progressao visivel: scraping -> pivot BrAPI -> LLM -> interface -> banco -> logging -> regras mais rígidas
- Mensagens descritivas em ingles

**Problemas:**
- `.env` commitado no repositorio (chaves de API potencialmente expostas!)
- `__pycache__` commitado (sem `.gitignore`!)
- README poderia ser mais detalhado (sem arquitetura, sem screenshots, sem decisoes de design)

---

## 7. Visao Arquitetural e RAG (Fase 3)

Nao implementado. Usa prompt injection simples com dados scraped.

---

## Nota Final: 3.5/5

*(Nota mantida apos execucao do codigo em 31/mar/2026 — achados confirmaram avaliacao original)*

A candidata demonstrou **excelente conhecimento de dominio financeiro**: o tratamento de intermediarios financeiros (bancos vs empresas regulares) e unico entre os candidatos e reflete compreensao real do mercado. O prompt e um dos melhores, com mencao explicita a value investing, valor intrinseco, abordagem bottom-up e protecao de downside. A evolucao iterativa do prompt ("stricter rules") mostra cuidado com a qualidade do output.

Porem, problemas de higiene de codigo (`.env` e `__pycache__` commitados, sem `.gitignore`) e modelagem de banco com JSON bruto reduzem a nota. Novos achados da execucao (tabela `ai_reports` orffa no DB commitado, `main.py` sem integracao com banco, duplicatas em `market_data` no mesmo dia) confirmam as lacunas na Fase 2. O README e funcional mas poderia ser mais detalhado.

**Validado rodando:** Google News RSS funcionando; yfinance OK; fallback DB funcionando; ticker invalido detectado; `BM_Source` indicator e detalhe de UX bem executado.
**Fundamentus 403:** Bloqueio de IP em ambiente cloud — codigo tecnicamente correto, falha de infraestrutura esperada em ambientes nao-browser.

**Diferenciais:** Tratamento de intermediarios financeiros (bancos), prompt com value investing explicito (valor intrinseco, bottom-up, downside), logging, pivot consciente de BrAPI para scraping, calculo derivado de Divida/EBITDA, `BM_Source` indicator no dashboard
**Lacunas:** .env e __pycache__ no repo (sem .gitignore!), banco com JSON bruto, sem graficos de preco, sem testes, sem retry/backoff, duplicatas em market_data por dia, main.py desconectado do banco, tabela ai_reports orffa no DB commitado
