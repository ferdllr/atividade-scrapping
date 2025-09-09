import requests
from bs4 import BeautifulSoup

html = requests.get(url="https://www.bawclothing.com.br/busca?busca=cal%C3%A7a")
soup = BeautifulSoup(html.text, "html.parser")
###print(soup)
divs = soup.find_all("div", class_="flex w-auto")
for div in divs:
    nome = div.find(
        "p",
        class_="text-left truncate lg:w-full w-[165px] overflow-hidden whitespace-nowrap lg:text-sm text-xs text-primaryBlack font-medium leading-[21px] lg:mr-[10px] mr-0 uppercase lg:text-left",
    )
    preco = div.find("h2")
    print(f"nome: {nome.text.strip()} preco: {preco.text.strip()}")
