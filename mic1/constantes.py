"""
Constantes da Microarquitetura MIC-1 (Tanenbaum).
Contém os registradores (0 a 15), códigos dos sinais de controle do MIR
e funções auxiliares para aritmética de 16 bits em complemento de 2.
"""

# Índices dos 16 registradores internos do caminho de dados (4 bits: 0..15)
REG_NOMES = [
    "PC",     # 0  - Program Counter (Contador de Programa)
    "AC",     # 1  - Accumulator (Acumulador)
    "SP",     # 2  - Stack Pointer (Ponteiro de Pilha)
    "IR",     # 3  - Instruction Register (Registrador de Instrução)
    "TIR",    # 4  - Temporary Instruction Register
    "0",      # 5  - Constante 0
    "+1",     # 6  - Constante +1
    "-1",     # 7  - Constante -1 (0xFFFF)
    "AMASK",  # 8  - Máscara de endereço de 12 bits (0x0FFF)
    "SMASK",  # 9  - Máscara de pilha de 8 bits (0x00FF)
    "A",      # 10 - Registrador auxiliar A
    "B",      # 11 - Registrador auxiliar B
    "C",      # 12 - Registrador auxiliar C
    "D",      # 13 - Registrador auxiliar D
    "E",      # 14 - Registrador auxiliar E
    "F",      # 15 - Registrador auxiliar F
]

REG_INDICE = {nome: idx for idx, nome in enumerate(REG_NOMES)}

# Registradores somente leitura (constantes em hardware)
REGS_SOMENTE_LEITURA = {5, 6, 7, 8, 9}

# Valores iniciais dos registradores constantes
CONSTANTES_HARDWARE = {
    5: 0x0000,  # 0
    6: 0x0001,  # +1
    7: 0xFFFF,  # -1 em complemento de 2
    8: 0x0FFF,  # AMASK (4095)
    9: 0x00FF,  # SMASK (255)
}

# Códigos do campo AMUX (1 bit)
AMUX_LATCH_A = 0
AMUX_MBR = 1

# Códigos do campo COND (2 bits)
COND_NAO_DESVIA = 0
COND_DESVIA_N = 1
COND_DESVIA_Z = 2
COND_DESVIA_SEMPRE = 3

# Códigos do campo ALU (2 bits)
ALU_SOMA = 0      # A + B
ALU_AND = 1       # A AND B
ALU_PASSA_A = 2   # A
ALU_NOT_A = 3     # NOT A

# Códigos do campo SH (Deslocador - 2 bits, conforme especificação do curso)
SH_NENHUM = 0     # não desloca
SH_ESQUERDA = 1   # desloca 1 bit à esquerda (lshift)
SH_DIREITA = 2    # desloca 1 bit à direita (rshift)

# Parâmetros da Memória Principal MAC-1 (endereços de 12 bits: 0..4095)
TAMANHO_MEMORIA = 4096
SP_INICIAL = 4096  # Primeiro PUSH decrementa para 4095 (0x0FFF)


def para_u16(valor: int) -> int:
    """Converte um inteiro para 16 bits sem sinal (0..65535)."""
    return valor & 0xFFFF


def para_s16(valor: int) -> int:
    """Converte um valor de 16 bits para inteiro com sinal (-32768..32767)."""
    v = valor & 0xFFFF
    return v - 0x10000 if (v & 0x8000) else v


def para_bin16(valor: int) -> str:
    """Retorna representação binária de 16 bits agrupada de 4 em 4."""
    b = f"{valor & 0xFFFF:016b}"
    return f"{b[0:4]} {b[4:8]} {b[8:12]} {b[12:16]}"


def para_hex16(valor: int) -> str:
    """Retorna representação hexadecimal de 16 bits (ex: 0x002A)."""
    return f"0x{valor & 0xFFFF:04X}"
