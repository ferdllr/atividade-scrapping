import pandas as pd
import re
import time
from dataclasses import asdict
from typing import Dict, List, Optional

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from model import DetalhesProduto, Produto, formatar_preco, normalizar_nome_produto
from selenium.webdriver.support.ui import Select, WebDriverWait

class ScraperProduto:
    def __init__(self, url_base: str = "https://www.bawclothing.com.br", headless: bool = False):
        self.url_base = url_base
        self.driver = self._configurar_driver(headless)
        self.todos_produtos: List[Produto] = [] 
        
    def _configurar_driver(self, headless: bool = False) -> webdriver.Firefox:
        options = webdriver.FirefoxOptions()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--start-maximized')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        return webdriver.Firefox(options=options)

    def mudar_filtro_ordem(self, valor_filtro: str = "PRICE:ASC") -> bool:
        try:
            elemento_select_ordem = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "sort_options"))
            )
            select_ordem = Select(elemento_select_ordem)
            select_ordem.select_by_value(valor_filtro)
            time.sleep(5)
            return True
        except TimeoutException:
            return False

    def coletar_resultados_pagina(self) -> List[Produto]:
        produtos = []
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.spot[data-id]"))
            )
            
            elementos_produto = self.driver.find_elements(By.CSS_SELECTOR, "div.spot[data-id]")
            
            for elemento_produto in elementos_produto:
                try:
                    elem_nome = elemento_produto.find_element(By.CSS_SELECTOR, "p.text-left.truncate")
                    nome = elem_nome.text.strip()
                    
                    elem_url = elemento_produto.find_element(By.CSS_SELECTOR, "a.urlColor")
                    url = elem_url.get_attribute('href')
                    
                    elem_preco = elemento_produto.find_element(By.CSS_SELECTOR, "h2 b")
                    preco = formatar_preco(elem_preco.text)
                    
                    preco_original = preco
                    try:
                        elem_preco_original = elemento_produto.find_element(By.CSS_SELECTOR, "p.line-through")
                        preco_original = formatar_preco(elem_preco_original.text)
                    except NoSuchElementException:
                        pass
                    
                    if nome and preco > 0:
                        produto = Produto(
                            nome=nome,
                            preco=preco,
                            preco_original=preco_original,
                            url=url
                        )
                        produtos.append(produto)
                        
                except NoSuchElementException:
                    continue
                    
        except TimeoutException:
            print("  - Nenhum produto encontrado na página ou tempo de espera esgotado.")
            
        return produtos

    def coletar_de_paginas(self, num_paginas: int = 3) -> List[Produto]:
        print(f"Coletando produtos de {num_paginas} páginas...")
        for num_pagina in range(1, num_paginas + 1):
            print(f"  - Processando página {num_pagina}...")
            produtos_pagina = self.coletar_resultados_pagina()
            print(f"    Coletados {len(produtos_pagina)} produtos.")
            self.todos_produtos.extend(produtos_pagina)
            
            if num_pagina < num_paginas:
                try:
                    botao_proximo = self.driver.find_element(By.ID, "pagination_next")
                    if botao_proximo.is_enabled():
                        botao_proximo.click()
                        time.sleep(5)
                    else:
                        break
                except NoSuchElementException:
                    break
                    
        print(f"Total de {len(self.todos_produtos)} produtos coletados.")
        return self.todos_produtos

    def rankear_produtos_por_frequencia(self) -> List[Produto]:
        print("Analisando frequência de produtos...")
        grupos_produto = {}
        for produto in self.todos_produtos:
            nome_normalizado = normalizar_nome_produto(produto.nome)
            
            if nome_normalizado not in grupos_produto:
                grupos_produto[nome_normalizado] = []
            grupos_produto[nome_normalizado].append(produto)
        
        produtos_rankeados = []
        for nome_grupo, produtos in grupos_produto.items():
            melhor_produto = min(produtos, key=lambda p: p.preco)
            melhor_produto.frequencia = len(produtos)
            
            todas_cores = {cor for p in produtos for cor in p.nome.split() if normalizar_nome_produto(cor) == ''}
            todos_tamanhos = {tam for p in produtos for tam in p.nome.split() if normalizar_nome_produto(tam) == ''}

            melhor_produto.detalhes = DetalhesProduto(coletado_em="", descricao="", material="", cores_disponiveis=list(todas_cores), tamanhos_disponiveis=list(todos_tamanhos))
            produtos_rankeados.append(melhor_produto)
            
        produtos_rankeados.sort(key=lambda x: (-x.frequencia, x.preco))
        return produtos_rankeados

    def obter_detalhes_produto(self, produto: Produto) -> Optional[DetalhesProduto]:
        print(f"    Coletando detalhes de: {produto.nome}")
        try:
            self.driver.get(produto.url)
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#description-title"))
            )

            try:
                self.driver.find_element(By.ID, "description-title").click()
                conteudo_descricao = WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.ID, "description-content")))
            except Exception:
                conteudo_descricao = self.driver.find_element(By.ID, "description-content")

            descricao = conteudo_descricao.text.strip()

            elementos_cor = self.driver.find_elements(By.CSS_SELECTOR, 'div.selectColorContainer img')
            cores_disponiveis = {elem.get_attribute("alt") for elem in elementos_cor if elem.get_attribute("alt")}
            if produto.detalhes and produto.detalhes.cores_disponiveis:
                cores_disponiveis.update(produto.detalhes.cores_disponiveis)

            elementos_tamanho = self.driver.find_elements(By.CSS_SELECTOR, 'div.selectedSize input[onclick^="selectAttribute"]:not([disabled])')
            tamanhos_disponiveis = {elem.get_attribute("attribute-value") for elem in elementos_tamanho}

            material = "Material não especificado"
            for linha in descricao.split('\n'):
                if "composição:" in linha.lower():
                    material = linha.strip()
                    break
            
            produto.detalhes.coletado_em = time.strftime("%Y-%m-%d %H:%M:%S")
            produto.detalhes.descricao = descricao
            produto.detalhes.material = material
            produto.detalhes.cores_disponiveis = list(cores_disponiveis)
            produto.detalhes.tamanhos_disponiveis = list(tamanhos_disponiveis)
            return produto.detalhes
        except (WebDriverException, TimeoutException) as e:
            print(f"      Erro ao coletar detalhes para {produto.nome}: {e}")
            return None

    def executar_analise_completa(self, termo_busca: str = "calça") -> None:
        try:
            url_inicial = f"{self.url_base}/busca?busca={termo_busca}"
            print(f"Acessando: {url_inicial}")
            self.driver.get(url_inicial)
            self.mudar_filtro_ordem("PRICE:ASC")
            self.coletar_de_paginas(3)
            
            if not self.todos_produtos:
                print("Nenhum produto foi coletado. Encerrando.")
                return
            
            produtos_rankeados = self.rankear_produtos_por_frequencia()
            
            top_5_produtos = produtos_rankeados[:5]
            print("\nColetando informações detalhadas para os 5 melhores produtos...")
            for produto in top_5_produtos:
                produto.detalhes = self.obter_detalhes_produto(produto)
                time.sleep(1)
            
            df = pd.DataFrame([asdict(p) for p in top_5_produtos])
            
            detalhes_df = pd.json_normalize(df['detalhes'])
            df_final = pd.concat([df.drop(columns=['detalhes']), detalhes_df], axis=1)
            
            if 'cores_disponiveis' in df_final.columns:
                df_final['cores_disponiveis'] = df_final['cores_disponiveis'].apply(
                    lambda cores: ', '.join(sorted(list(set(cores)))) if isinstance(cores, list) else ''
                )
            if 'tamanhos_disponiveis' in df_final.columns:
                df_final['tamanhos_disponiveis'] = df_final['tamanhos_disponiveis'].apply(
                    lambda tamanhos: ', '.join(sorted(list(set(tamanhos)))) if isinstance(tamanhos, list) else ''
                )

            # Limpa a coluna de descrição para melhor visualização no CSV
            if 'descricao' in df_final.columns:
                df_final['descricao'] = df_final['descricao'].str.replace('\n', ' ', regex=False).str.strip()

            # Renomeia as colunas para o relatório final
            mapa_nomes = {
                'nome': 'Produto',
                'preco': 'Preço (R$)',
                'preco_original': 'Preço Original (R$)',
                'percentual_desconto': 'Desconto (%)',
                'frequencia': 'Variações Encontradas',
                'url': 'Link',
                'descricao': 'Descrição',
                'material': 'Material',
                'cores_disponiveis': 'Cores Disponíveis',
                'tamanhos_disponiveis': 'Tamanhos Disponíveis',
                'coletado_em': 'Data da Coleta'
            }
            df_final = df_final.rename(columns=mapa_nomes)
            
            # Define uma ordem de colunas mais legível para o relatório
            colunas_ordenadas = [
                'Produto',
                'Variações Encontradas',
                'Preço (R$)',
                'Preço Original (R$)',
                'Desconto (%)',
                'Cores Disponíveis',
                'Tamanhos Disponíveis',
                'Material',
                'Descrição',
                'Link',
                'Data da Coleta'
            ]
            colunas_existentes = [col for col in colunas_ordenadas if col in df_final.columns]
            df_final = df_final[colunas_existentes]
            
            nome_arquivo_csv = f"top_5_produtos_{termo_busca}.csv"
            df_final.to_csv(nome_arquivo_csv, index=False, encoding='utf-8-sig')
            print(f"\nRelatório com os 5 melhores produtos salvo com sucesso em '{nome_arquivo_csv}'")

        except (WebDriverException, Exception) as e:
            print(f"Erro durante a análise: {e}")
        finally:
            self.finalizar()

    def finalizar(self) -> None:
        print("Finalizando e fechando navegador...")
        if self.driver:
            self.driver.quit()