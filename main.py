from scraper import ScraperProduto

if __name__ == "__main__":
    scraper = ScraperProduto(headless=True)
    try:
        scraper.executar_analise_completa("calça")
    except KeyboardInterrupt:
        print("Execução interrompida pelo usuário.")
    except Exception as e:
        print(f"Erro crítico: {e}")
