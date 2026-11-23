"""
Simulador de Memória Cache (Instruções e Dados) para o MIC-1.

Suporta didaticamente dois modos clássicos de organização:
- Mapeamento Direto (vias = 1)
- Associativo por Conjunto (vias = 2 ou 4, com política de substituição LRU)

Política de escrita na D-Cache: Write-Through com Write-Allocate
(atualiza a cache e a memória principal ao mesmo tempo, facilitando a visualização).
"""

import math
from .constantes import para_u16


class LinhaCache:
    """Representa um bloco/linha armazenado dentro de um conjunto da cache."""

    def __init__(self, palavras_por_bloco: int):
        self.valido = False
        self.tag = 0
        self.dados = [0] * palavras_por_bloco
        self.ultimo_uso = 0  # Contador lógico para política LRU


class Cache:
    def __init__(
        self,
        nome: str,
        memoria_principal,
        num_conjuntos: int = 4,
        vias: int = 1,
        palavras_por_bloco: int = 4,
    ):
        self.nome = nome
        self.memoria = memoria_principal
        self.configurar(num_conjuntos, vias, palavras_por_bloco)

    def configurar(self, num_conjuntos: int, vias: int, palavras_por_bloco: int) -> None:
        """Reconfigura a geometria da cache e zera estatísticas."""
        self.num_conjuntos = max(1, int(num_conjuntos))
        self.vias = max(1, int(vias))
        self.palavras_por_bloco = max(1, int(palavras_por_bloco))

        self.bits_offset = int(math.log2(self.palavras_por_bloco))
        self.bits_indice = int(math.log2(self.num_conjuntos))
        self.bits_tag = 12 - self.bits_indice - self.bits_offset
        self.resetar()

    def resetar(self) -> None:
        self.conjuntos = [
            [LinhaCache(self.palavras_por_bloco) for _ in range(self.vias)]
            for _ in range(self.num_conjuntos)
        ]
        self.acessos = 0
        self.hits = 0
        self.misses = 0
        self.relogio_lru = 0
        self.ultimo_evento = None

    def _decodificar_endereco(self, endereco: int):
        """Divide um endereço de 12 bits em (tag, indice_conjunto, offset, base_bloco)."""
        end = endereco & 0x0FFF
        offset = end & ((1 << self.bits_offset) - 1) if self.bits_offset > 0 else 0
        indice = (end >> self.bits_offset) & ((1 << self.bits_indice) - 1) if self.bits_indice > 0 else 0
        tag = end >> (self.bits_offset + self.bits_indice)
        base_bloco = end - offset
        return tag, indice, offset, base_bloco

    def _carregar_bloco_da_ram(self, conjunto_linhas, tag: int, base_bloco: int) -> LinhaCache:
        """Escolhe uma linha livre ou a menos recentemente usada (LRU) e traz o bloco da RAM."""
        alvo = None
        for linha in conjunto_linhas:
            if not linha.valido:
                alvo = linha
                break
        if alvo is None:
            alvo = min(conjunto_linhas, key=lambda l: l.ultimo_uso)

        alvo.valido = True
        alvo.tag = tag
        alvo.dados = [
            self.memoria.ler((base_bloco + i) & 0x0FFF)
            for i in range(self.palavras_por_bloco)
        ]
        alvo.ultimo_uso = self.relogio_lru
        return alvo

    def ler(self, endereco: int) -> tuple:
        """
        Lê uma palavra de 16 bits através da cache.
        Retorna (valor, hit: bool).
        """
        self.acessos += 1
        self.relogio_lru += 1
        tag, indice, offset, base_bloco = self._decodificar_endereco(endereco)
        conjunto = self.conjuntos[indice]

        # 1. Procura a tag no conjunto selecionado
        for via_idx, linha in enumerate(conjunto):
            if linha.valido and linha.tag == tag:
                self.hits += 1
                linha.ultimo_uso = self.relogio_lru
                valor = linha.dados[offset]
                self.ultimo_evento = {
                    "tipo": "LEITURA",
                    "resultado": "HIT",
                    "endereco": endereco & 0x0FFF,
                    "tag": tag,
                    "conjunto": indice,
                    "via": via_idx,
                    "offset": offset,
                    "valor": valor,
                }
                return valor, True

        # 2. Cache Miss: busca o bloco inteiro da Memória Principal
        self.misses += 1
        linha = self._carregar_bloco_da_ram(conjunto, tag, base_bloco)
        via_idx = conjunto.index(linha)
        valor = linha.dados[offset]
        self.ultimo_evento = {
            "tipo": "LEITURA",
            "resultado": "MISS",
            "endereco": endereco & 0x0FFF,
            "tag": tag,
            "conjunto": indice,
            "via": via_idx,
            "offset": offset,
            "valor": valor,
        }
        return valor, False

    def escrever(self, endereco: int, valor: int) -> bool:
        """
        Escreve uma palavra usando Write-Through + Write-Allocate.
        Retorna hit: bool.
        """
        valor = para_u16(valor)
        self.acessos += 1
        self.relogio_lru += 1
        tag, indice, offset, base_bloco = self._decodificar_endereco(endereco)
        conjunto = self.conjuntos[indice]

        # Write-Through: sempre atualiza a memória principal
        self.memoria.escrever(endereco, valor)

        for via_idx, linha in enumerate(conjunto):
            if linha.valido and linha.tag == tag:
                self.hits += 1
                linha.dados[offset] = valor
                linha.ultimo_uso = self.relogio_lru
                self.ultimo_evento = {
                    "tipo": "ESCRITA",
                    "resultado": "HIT",
                    "endereco": endereco & 0x0FFF,
                    "tag": tag,
                    "conjunto": indice,
                    "via": via_idx,
                    "offset": offset,
                    "valor": valor,
                }
                return True

        # Miss de escrita: traz o bloco atualizado para a cache (Write-Allocate)
        self.misses += 1
        linha = self._carregar_bloco_da_ram(conjunto, tag, base_bloco)
        via_idx = conjunto.index(linha)
        self.ultimo_evento = {
            "tipo": "ESCRITA",
            "resultado": "MISS",
            "endereco": endereco & 0x0FFF,
            "tag": tag,
            "conjunto": indice,
            "via": via_idx,
            "offset": offset,
            "valor": valor,
        }
        return False

    def exportar_estado(self) -> dict:
        taxa_hit = (self.hits / self.acessos * 100.0) if self.acessos > 0 else 0.0
        linhas = []
        for idx_conj, conjunto in enumerate(self.conjuntos):
            for idx_via, linha in enumerate(conjunto):
                linhas.append({
                    "conjunto": idx_conj,
                    "via": idx_via,
                    "valido": linha.valido,
                    "tag": linha.tag,
                    "dados": list(linha.dados),
                    "ultimo_uso": linha.ultimo_uso,
                })

        modo = "Mapeamento Direto" if self.vias == 1 else f"Associativo {self.vias}-vias (LRU)"
        return {
            "nome": self.nome,
            "modo": modo,
            "num_conjuntos": self.num_conjuntos,
            "vias": self.vias,
            "palavras_por_bloco": self.palavras_por_bloco,
            "bits_tag": self.bits_tag,
            "bits_indice": self.bits_indice,
            "bits_offset": self.bits_offset,
            "acessos": self.acessos,
            "hits": self.hits,
            "misses": self.misses,
            "taxa_hit": round(taxa_hit, 1),
            "ultimo_evento": self.ultimo_evento,
            "linhas": linhas,
        }
