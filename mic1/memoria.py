"""
Memória Principal da máquina MAC-1 / MIC-1.
Possui 4096 palavras de 16 bits (endereços 0x000 a 0xFFF).
"""

from .constantes import TAMANHO_MEMORIA, para_u16


class MemoriaPrincipal:
    def __init__(self, tamanho: int = TAMANHO_MEMORIA):
        self.tamanho = tamanho
        self.palavras = [0] * tamanho

    def limpar(self) -> None:
        self.palavras = [0] * self.tamanho

    def ler(self, endereco: int) -> int:
        end = endereco & 0x0FFF
        return self.palavras[end]

    def escrever(self, endereco: int, valor: int) -> None:
        end = endereco & 0x0FFF
        self.palavras[end] = para_u16(valor)

    def carregar_programa(self, mapa_palavras: dict) -> None:
        """Carrega um dicionário {endereco: valor_16bits} na memória."""
        self.limpar()
        for end, val in mapa_palavras.items():
            self.escrever(end, val)
