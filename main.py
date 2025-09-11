import time
import json
import re
from collections import Counter
from dataclasses import dataclass
from typing import List, Optional, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException, TimeoutException

@dataclass
class Product:
    name: str
    price: float
    original_price: float
    url: str
    discount_percentage: float = 0.0
    frequency: int = 0
    details: Optional[Dict] = None

    def __post_init__(self):
        if self.original_price > self.price:
            self.discount_percentage = round(
                ((self.original_price - self.price) / self.original_price) * 100, 2
            )

class ProductScraper:
    def __init__(self, base_url: str = "https://www.bawclothing.com.br", headless: bool = False):
        self.base_url = base_url
        self.driver = self._setup_driver(headless)
        self.all_products: List[Product] = []
        
    def _setup_driver(self, headless: bool = False) -> webdriver.Firefox:
        options = webdriver.FirefoxOptions()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--start-maximized')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        return webdriver.Firefox(options=options)

    def change_sort_filter(self, filter_value: str = "PRICE:ASC") -> bool:
        try:
            sort_select_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "sort_options"))
            )
            sort_select = Select(sort_select_element)
            sort_select.select_by_value(filter_value)
            time.sleep(5)
            return True
        except TimeoutException:
            return False

    def _parse_price(self, price_str: str) -> float:
        if not price_str:
            return 0.0
        cleaned_price = re.sub(r'[R$\s]', '', price_str).replace('.', '').replace(',', '.')
        try:
            return float(cleaned_price)
        except ValueError:
            return 0.0

    def _normalize_product_name(self, name: str) -> str:
        normalized = re.sub(r'\b(PP|P|M|G|GG|XG|XXG)\b', '', name.upper())
        normalized = re.sub(r'\b(PRETO|BRANCO|AZUL|VERDE|VERMELHO|AMARELO|ROSA|ROXO)\b', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized

    def scrape_page_results(self) -> List[Product]:
        products = []
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.spot[data-id]"))
            )
            
            product_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.spot[data-id]")
            
            for product_element in product_elements:
                try:
                    name_elem = product_element.find_element(By.CSS_SELECTOR, "p.text-left.truncate")
                    name = name_elem.text.strip()
                    
                    url_elem = product_element.find_element(By.CSS_SELECTOR, "a.urlColor")
                    url = url_elem.get_attribute('href')
                    
                    price_elem = product_element.find_element(By.CSS_SELECTOR, "h2 b")
                    price = self._parse_price(price_elem.text)
                    
                    original_price = price
                    try:
                        original_price_elem = product_element.find_element(By.CSS_SELECTOR, "p.line-through")
                        original_price = self._parse_price(original_price_elem.text)
                    except NoSuchElementException:
                        pass
                    
                    if name and price > 0:
                        product = Product(
                            name=name,
                            price=price,
                            original_price=original_price,
                            url=url
                        )
                        products.append(product)
                        
                except (NoSuchElementException, Exception):
                    continue
                    
        except (TimeoutException, Exception):
            pass
            
        return products

    def collect_from_pages(self, num_pages: int = 3) -> List[Product]:
        print(f"Coletando produtos de {num_pages} páginas...")
        for page_num in range(1, num_pages + 1):
            print(f"  - Processando página {page_num}...")
            page_products = self.scrape_page_results()
            print(f"    Coletados {len(page_products)} produtos.")
            self.all_products.extend(page_products)
            
            if page_num < num_pages:
                try:
                    next_button = self.driver.find_element(By.ID, "pagination_next")
                    if next_button.is_enabled():
                        next_button.click()
                        time.sleep(5)
                    else:
                        break
                except NoSuchElementException:
                    break
                    
        print(f"Total de {len(self.all_products)} produtos coletados.")
        return self.all_products

    def rank_products_by_frequency(self) -> List[Product]:
        print("Analisando frequência de produtos...")
        product_groups = {}
        for product in self.all_products:
            normalized_name = self._normalize_product_name(product.name)
            
            if normalized_name not in product_groups:
                product_groups[normalized_name] = []
            product_groups[normalized_name].append(product)
        
        ranked_products = []
        for group_name, products in product_groups.items():
            frequency = len(products)
            best_product = min(products, key=lambda p: p.price)
            best_product.frequency = frequency
            ranked_products.append(best_product)
        
        ranked_products.sort(key=lambda x: (-x.frequency, x.price))
        return ranked_products

    def get_product_details(self, product: Product) -> Optional[Dict]:
        print(f"    Coletando detalhes de: {product.name}")
        try:
            self.driver.get(product.url)
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".vtex-store-components-3-x-productNameContainer"))
            )
            details = {
                "url": product.url,
                "collected_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            try:
                desc_elem = self.driver.find_element(By.CSS_SELECTOR, ".vtex-store-components-3-x-productDescriptionContainer .vtex-rich-text-0-x-container")
                details["description"] = desc_elem.text.strip()
            except NoSuchElementException:
                details["description"] = "Descrição não disponível"

            details["available_sizes"] = []
            details["available_colors"] = []
            try:
                sku_selectors = self.driver.find_elements(By.CSS_SELECTOR, ".vtex-store-components-3-x-skuSelectorContainer")
                for selector in sku_selectors:
                    label_text = selector.find_element(By.CSS_SELECTOR, ".vtex-store-components-3-x-skuSelectorName").text.strip().lower()
                    options = [opt.text.strip() for opt in selector.find_elements(By.CSS_SELECTOR, ".vtex-store-components-3-x-skuSelectorItem .vtex-store-components-3-x-skuSelectorName") if opt.text.strip()]
                    if "tamanho" in label_text:
                        details["available_sizes"] = options
                    elif "cor" in label_text:
                        details["available_colors"] = options
            except NoSuchElementException:
                pass
            try:
                material_elem = self.driver.find_element(By.CSS_SELECTOR, ".material-info, .fabric-info, .composition")
                details["material"] = material_elem.text.strip()
            except NoSuchElementException:
                details["material"] = "Material não especificado"
            return details
        except (TimeoutException, Exception) as e:
            print(f"    Erro ao coletar detalhes: {e}")
            return None

    def save_results(self, products: List[Product], filename: str = "top_5_produtos.json") -> None:
        print(f"Salvando resultados em '{filename}'...")
        data = []
        for product in products:
            data.append(product.__dict__)
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"Dados salvos com sucesso em '{filename}'!")
        except Exception as e:
            print(f"Erro ao salvar arquivo: {e}")

    def run_complete_analysis(self, search_term: str = "calça") -> None:
        try:
            initial_url = f"{self.base_url}/busca?busca={search_term}"
            print(f"Acessando: {initial_url}")
            self.driver.get(initial_url)
            self.change_sort_filter("PRICE:ASC")
            self.collect_from_pages(3)
            if not self.all_products:
                print("Nenhum produto foi coletado. Encerrando.")
                return
            ranked_products = self.rank_products_by_frequency()
            top_5 = ranked_products[:5]
            print("\nTop 5 produtos selecionados para análise detalhada:")
            for i, product in enumerate(top_5):
                print(f"  {i+1}. {product.name} - Freq: {product.frequency}x - R$ {product.price}")
                details = self.get_product_details(product)
                product.details = details
                time.sleep(2)
            self.save_results(top_5)
        except Exception as e:
            print(f"Erro durante a análise: {e}")
        finally:
            self.cleanup()

    def cleanup(self) -> None:
        print("Finalizando e fechando navegador...")
        if self.driver:
            self.driver.quit()

if __name__ == "__main__":
    scraper = ProductScraper(headless=True)
    try:
        scraper.run_complete_analysis("calça")
    except KeyboardInterrupt:
        print("Execução interrompida pelo usuário.")
    except Exception as e:
        print(f"Erro crítico: {e}")
