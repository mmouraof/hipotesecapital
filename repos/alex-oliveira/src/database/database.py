from dotenv import load_dotenv
from src.database import *
import src.backend.scrapper1 as s1
import src.backend.scrapper2 as s2



load_dotenv()



def _existing_ticker(session: Session, ticker: str) -> bool:
    return session.get(Ativo, ticker) is not None



def insert_data(session: Session, ticker: str, dados: dict) -> None:
    hoje = dados["data_coleta"]
    c    = dados["dados_cadastrais"]
    q    = dados["dados_cotacao"]
    i    = dados["indicadores_fundamentalistas"]
    n    = dados["noticias"]

    # Ativos (upsert simples: só insere se ainda não existir)
    if not _existing_ticker(session, ticker.upper()):
        session.add(Ativo(
            Ticker                 = c["ticker"],
            EmpresaAtivo           = c["empresa"],
            SetorAtuacaoEmpresa    = c["setor"],
            SegmentoAtuacaoEmpresa = c["segmento"],
            ResumoEmpresa          = c["resumo"],
        ))
        session.flush()   # garante FK antes das próximas inserções

    # DadosCotacao
    session.add(DadosCotacao(
        DataConsulta        = hoje,
        Ticker              = c["ticker"],
        Cotacao             = q["cotacao"],
        DataUltimaCotacao   = q["data_ultima_cotacao"],
        Min52semanas        = q["min_52"],
        Max52semanas        = q["max_52"],
        VolumeMedio2Meses   = q["volume_medio_2m"],
        ValorMercado        = q["valor_mercado"],
        NumeroAcoes         = q["num_acoes"],
        DataUltimoBalanco   = q["data_ultimo_balanco"],
    ))

    # IndicadoresFundamentalistas
    session.add(IndicadoresFundamentalistas(
        DataConsulta        = hoje,
        Ticker              = c["ticker"],
        PL                  = i["pl"],
        ROE                 = i["roe"],
        DividaLiquidaEBITDA = i["div_liq_ebitda"],
        MargemLiquida       = i["margem_liquida"],
        DividendYield       = i["dividend_yield"],
    ))

    # Noticias
    for i in range(5):
        session.add(Noticias(
            DataConsulta = hoje,
            Ticker       = c["ticker"],
            URLNoticia   = n[f"noticia_{i+1}"][0],
            Resumo       = n[f"noticia_{i+1}"][1],
            Classificador= n[f"noticia_{i+1}"][2],
            Escala       = n[f"noticia_{i+1}"][3],
        ))



# ══════════════════════════════════════════════════════════════════════════════
#  EXECUÇÃO PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def main():

    # Cria as tabelas caso ainda não existam
    Base.metadata.create_all(engine)
    print("Tabelas verificadas/criadas.\n")

    with Session(engine) as session:
        for ticker in os.getenv("TICKERS"):
            print(f"Coletando {ticker}...")
            try:

                # Tenta algum dos dois métodos de obtenção dos dados
                if s1.get_full_data(ticker) != {}:
                    dados = s1.get_full_data(ticker)
                else:
                    dados = s2.get_full_data(ticker, os.getenv("MAX_TRIES"), os.getenv("SLEEP"))
                
                # Inserindo os dados
                insert_data(session, ticker,dados)
                print(f"{ticker} inserido.")
            except Exception as e:
                print(f"Erro em {ticker}: {e}")

        session.commit()
        print("\nCommit realizado. Transação finalizada!")


# Exemplo
# if __name__ == "__main__":
#     main()