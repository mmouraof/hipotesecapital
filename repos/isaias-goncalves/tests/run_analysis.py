from core.collector import DataCollector
from core.analyzer import InvestmentAnalyzer
import json
import sys
from utils.logger import logger

def main():
    print("\n" + "="*50)
    print("      HIPÓTESE CAPITAL - PIPELINE DE ANÁLISE")
    print("="*50 + "\n")

    # 1. Entrada do Ticker
    ticker_input = input("Digite o ticker para análise (ex: ASAI3, ITUB4): ").strip() or "ASAI3"
    
    try:
        # 2. Executa a Coleta
        print(f"[*] Coletando dados reais para {ticker_input}...")
        collector = DataCollector(ticker_input)
        raw_data = collector.collect_all_data()
        
        if not raw_data:
            print("[!] Erro: Não foi possível coletar dados para este ticker.")
            return

        # 3. Executa a Análise via LLM
        print(f"[*] Enviando dados para OpenAI ({ticker_input})...")
        analyzer = InvestmentAnalyzer()
        analysis = analyzer.analyze_ticker(ticker_input, raw_data)
        
        if "error" in analysis:
            print(f"[!] Erro na análise: {analysis['error']}")
            return

        # 4. Exibe o Resultado Final
        print("\n" + "#"*60)
        print(f"  RELATÓRIO DE INVESTIMENTO: {ticker_input}")
        print("#"*60)
        
        print(f"\n[RESUMO DO NEGÓCIO]\n{analysis.get('resumo_negocio')}")
        
        print(f"\n[ANÁLISE DE INDICADORES (VALUE INVESTING)]\n{analysis.get('analise_indicadores')}")
        
        print(f"\n[SENTIMENTO DAS NOTÍCIAS]\n{analysis.get('sentimento_noticias')}")
        
        print(f"\n[PERGUNTAS INVESTIGATIVAS CRUCIAIS]")
        for i, pergunta in enumerate(analysis.get('perguntas_investigativas', []), 1):
            print(f"{i}. {pergunta}")
            
        print("\n" + "="*60)
        print("Pipeline finalizado com sucesso.")
        print("="*60 + "\n")

    except Exception as e:
        logger.error(f"Erro crítico no pipeline: {str(e)}")
        print(f"\n[!] Ocorreu um erro inesperado: {e}")

if __name__ == "__main__":
    main()
