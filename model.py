from bs4 import BeautifulSoup


class Product:
    def __init__(self, nome, preco) -> None:
        self.nome = nome
        self.preco = preco

    def __repr__(self) -> str:
        return f"nome: {self.nome} preco: {self.preco}"


class ProductList:
    def __init__(self, divs):
        self.divs = divs
        self.products = self.get_produtos()

    def get_produtos(self):
        products = []
        for div in self.divs:
            nome = div.find(
                "p",
                class_="text-left truncate lg:w-full w-[165px] overflow-hidden whitespace-nowrap lg:text-sm text-xs text-primaryBlack font-medium leading-[21px] lg:mr-[10px] mr-0 uppercase lg:text-left",
            )
            preco = div.find("h2")
            products.append(
                Product(nome.get_text(strip=True), preco.get_text(strip=True))
            )
        return products
