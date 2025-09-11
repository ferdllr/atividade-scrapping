from dataclasses import dataclass, field
from typing import Dict, List, Optional
import re


@dataclass
class DetalhesProduto:
    coletado_em: str
    descricao: str
    material: str
    cores_disponiveis: List[str] = field(default_factory=list)
    tamanhos_disponiveis: List[str] = field(default_factory=list)


@dataclass
class Produto:
    nome: str
    preco: float
    preco_original: float
    url: str
    percentual_desconto: float = 0.0
    frequencia: int = 0
    detalhes: Optional[DetalhesProduto] = None

    def __post_init__(self):
        if self.preco_original > self.preco:
            self.percentual_desconto = round(((self.preco_original - self.preco) / self.preco_original) * 100, 2)

def formatar_preco(preco_str: str) -> float:
    if not preco_str:
        return 0.0
    preco_limpo = re.sub(r'[R$\s]', '', preco_str).replace('.', '').replace(',', '.')
    try:
        return float(preco_limpo)
    except ValueError:
        return 0.0

def normalizar_nome_produto(nome: str) -> str:
    normalizado = re.sub(r'\b(PP|P|M|G|GG|XG|XXG)\b', '', nome.upper())
    normalizado = re.sub(r'\b(PRETO|BRANCO|AZUL|VERDE|VERMELHO|AMARELO|ROSA|ROXO)\b', '', normalizado)
    normalizado = re.sub(r'\s+', ' ', normalizado).strip()
    return normalizado