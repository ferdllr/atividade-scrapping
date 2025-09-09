import requests
from bs4 import BeautifulSoup
from model import ProductList, Product

html = requests.get(url="https://www.bawclothing.com.br/busca?busca=cal%C3%A7a")
soup = BeautifulSoup(html.text, "html.parser")
###print(soup)
divs = soup.find_all("div", class_="flex w-auto")
products = ProductList(divs).products
for product in products:
    print(product)
