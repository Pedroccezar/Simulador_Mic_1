"""
Memória de Controle (256 x 32 bits) contendo o Microprograma MIC-1 de Tanenbaum.

Formato da palavra de microinstrução no MIR (32 bits):
  Bit 31     : AMUX (1 bit)  - 0=Latch A, 1=MBR
  Bits 30-29 : COND (2 bits) - 0=não desvia, 1=se N=1, 2=se Z=1, 3=sempre
  Bits 28-27 : ALU  (2 bits) - 0=A+B, 1=A AND B, 2=A, 3=NOT A
  Bits 26-25 : SH   (2 bits) - 0=nenhum, 1=lshift (esq.), 2=rshift (dir.)
  Bit 24     : MBR  (1 bit)  - 1=escreve saída no MBR
  Bit 23     : MAR  (1 bit)  - 1=escreve Latch B no MAR
  Bit 22     : RD   (1 bit)  - 1=sinal de leitura de memória
  Bit 21     : WR   (1 bit)  - 1=sinal de escrita de memória
  Bit 20     : ENC  (1 bit)  - 1=habilita escrita no registrador C
  Bits 19-16 : C    (4 bits) - registrador destino no barramento C
  Bits 15-12 : B    (4 bits) - registrador fonte no barramento B
  Bits 11-8  : A    (4 bits) - registrador fonte no barramento A
  Bits 7-0   : ADDR (8 bits) - endereço de desvio na Memória de Controle
"""

from dataclasses import dataclass
from .constantes import (
    REG_INDICE,
    REG_NOMES,
    AMUX_LATCH_A,
    AMUX_MBR,
    COND_NAO_DESVIA,
    COND_DESVIA_N,
    COND_DESVIA_Z,
    COND_DESVIA_SEMPRE,
    ALU_SOMA,
    ALU_AND,
    ALU_PASSA_A,
    ALU_NOT_A,
    SH_NENHUM,
    SH_ESQUERDA,
)


@dataclass
class Microinstrucao:
    endereco: int
    texto: str
    comentario: str
    amux: int = AMUX_LATCH_A
    cond: int = COND_NAO_DESVIA
    alu: int = ALU_PASSA_A
    sh: int = SH_NENHUM
    mbr: int = 0
    mar: int = 0
    rd: int = 0
    wr: int = 0
    enc: int = 0
    c: int = 0
    b: int = 0
    a: int = 0
    addr: int = 0

    def codificar_32bits(self) -> int:
        """Empacota todos os campos na palavra de controle de 32 bits do MIR."""
        return (
            ((self.amux & 0x1) << 31)
            | ((self.cond & 0x3) << 29)
            | ((self.alu & 0x3) << 27)
            | ((self.sh & 0x3) << 25)
            | ((self.mbr & 0x1) << 24)
            | ((self.mar & 0x1) << 23)
            | ((self.rd & 0x1) << 22)
            | ((self.wr & 0x1) << 21)
            | ((self.enc & 0x1) << 20)
            | ((self.c & 0xF) << 16)
            | ((self.b & 0xF) << 12)
            | ((self.a & 0xF) << 8)
            | (self.addr & 0xFF)
        )

    def para_dict(self) -> dict:
        palavra = self.codificar_32bits()
        return {
            "endereco": self.endereco,
            "texto": self.texto,
            "comentario": self.comentario,
            "amux": self.amux,
            "cond": self.cond,
            "alu": self.alu,
            "sh": self.sh,
            "mbr": self.mbr,
            "mar": self.mar,
            "rd": self.rd,
            "wr": self.wr,
            "enc": self.enc,
            "c": self.c,
            "c_nome": REG_NOMES[self.c],
            "b": self.b,
            "b_nome": REG_NOMES[self.b],
            "a": self.a,
            "a_nome": REG_NOMES[self.a],
            "addr": self.addr,
            "bits32": f"{palavra:032b}",
            "hex32": f"0x{palavra:08X}",
        }


def _mi(endereco, texto, comentario="", **kwargs) -> Microinstrucao:
    """Atalho legível que converte nomes de registradores ('PC', 'AC'...) para índices."""
    for campo in ("a", "b", "c"):
        if campo in kwargs and isinstance(kwargs[campo], str):
            kwargs[campo] = REG_INDICE[kwargs[campo]]
    return Microinstrucao(endereco=endereco, texto=texto, comentario=comentario, **kwargs)


def criar_memoria_de_controle() -> list:
    """
    Constrói a ROM de Controle (256 posições) com as 79 microinstruções (0..78)
    do microprograma MIC-1 de Andrew S. Tanenbaum.
    """
    rom = [
        _mi(i, "nop", "Posição não utilizada")
        for i in range(256)
    ]

    definicoes = [
        # --- Ciclo de Busca (Fetch) e Início da Decodificação ---
        _mi(0,  "mar := pc; rd;", "Busca instrução: MAR recebe PC e inicia leitura na I-Cache",
            b="PC", mar=1, rd=1),
        _mi(1,  "pc := pc + 1; rd;", "Incrementa PC e conclui leitura da instrução para MBR",
            a="PC", b="+1", alu=ALU_SOMA, c="PC", enc=1, rd=1),
        _mi(2,  "ir := mbr; if n then goto 28;", "Salva instrução em IR; testa bit 15 (0xxx vs 1xxx)",
            amux=AMUX_MBR, alu=ALU_PASSA_A, c="IR", enc=1, cond=COND_DESVIA_N, addr=28),
        _mi(3,  "tir := lshift(ir + ir); if n then goto 19;", "Testa bit 14 (00xx vs 01xx) e desloca IR para TIR",
            a="IR", b="IR", alu=ALU_SOMA, sh=SH_ESQUERDA, c="TIR", enc=1, cond=COND_DESVIA_N, addr=19),
        _mi(4,  "tir := lshift(tir); if n then goto 11;", "Testa bit 13 (000x vs 001x)",
            a="TIR", alu=ALU_PASSA_A, sh=SH_ESQUERDA, c="TIR", enc=1, cond=COND_DESVIA_N, addr=11),
        _mi(5,  "alu := tir; if n then goto 9;", "Testa bit 12 (0000=LODD vs 0001=STOD)",
            a="TIR", alu=ALU_PASSA_A, cond=COND_DESVIA_N, addr=9),

        # --- 0000: LODD x (ac := m[x]) ---
        _mi(6,  "mar := ir; rd;", "LODD: carrega endereço x (12 bits de IR) no MAR e lê D-Cache",
            b="IR", mar=1, rd=1),
        _mi(7,  "rd;", "LODD/LODL: conclui leitura da memória para MBR",
            rd=1),
        _mi(8,  "ac := mbr; goto 0;", "LODD/LODL: transfere dado lido (MBR) para AC e volta ao ciclo 0",
            amux=AMUX_MBR, alu=ALU_PASSA_A, c="AC", enc=1, cond=COND_DESVIA_SEMPRE, addr=0),

        # --- 0001: STOD x (m[x] := ac) ---
        _mi(9,  "mar := ir; mbr := ac; wr;", "STOD: MAR recebe x, MBR recebe AC e inicia escrita",
            a="AC", b="IR", alu=ALU_PASSA_A, mar=1, mbr=1, wr=1),
        _mi(10, "wr; goto 0;", "Conclui escrita na D-Cache/RAM e retorna ao loop principal",
            wr=1, cond=COND_DESVIA_SEMPRE, addr=0),

        # --- 0010: ADDD x / 0011: SUBD x ---
        _mi(11, "alu := tir; if n then goto 15;", "Testa bit 12 (0010=ADDD vs 0011=SUBD)",
            a="TIR", alu=ALU_PASSA_A, cond=COND_DESVIA_N, addr=15),
        _mi(12, "mar := ir; rd;", "ADDD: carrega endereço x no MAR e inicia leitura",
            b="IR", mar=1, rd=1),
        _mi(13, "rd;", "ADDD/ADDL: conclui leitura do operando para MBR",
            rd=1),
        _mi(14, "ac := mbr + ac; goto 0;", "ADDD/ADDL: soma MBR + AC e guarda em AC",
            amux=AMUX_MBR, b="AC", alu=ALU_SOMA, c="AC", enc=1, cond=COND_DESVIA_SEMPRE, addr=0),
        _mi(15, "mar := ir; rd;", "SUBD: carrega endereço x no MAR e inicia leitura",
            b="IR", mar=1, rd=1),
        _mi(16, "ac := ac + 1; rd;", "SUBD/SUBL: prepara complemento de 2 (x - y = x + 1 + NOT y)",
            a="AC", b="+1", alu=ALU_SOMA, c="AC", enc=1, rd=1),
        _mi(17, "a := inv(mbr);", "SUBD/SUBL: inverte os bits do operando (NOT MBR) em A",
            amux=AMUX_MBR, alu=ALU_NOT_A, c="A", enc=1),
        _mi(18, "ac := ac + a; goto 0;", "SUBD/SUBL: conclui subtração (AC + 1 + NOT MBR)",
            a="AC", b="A", alu=ALU_SOMA, c="AC", enc=1, cond=COND_DESVIA_SEMPRE, addr=0),

        # --- 01xx: JPOS, JZER, JUMP, LOCO ---
        _mi(19, "tir := lshift(tir); if n then goto 25;", "Testa bit 13 (010x vs 011x)",
            a="TIR", alu=ALU_PASSA_A, sh=SH_ESQUERDA, c="TIR", enc=1, cond=COND_DESVIA_N, addr=25),
        _mi(20, "alu := tir; if n then goto 23;", "Testa bit 12 (0100=JPOS vs 0101=JZER)",
            a="TIR", alu=ALU_PASSA_A, cond=COND_DESVIA_N, addr=23),
        _mi(21, "alu := ac; if n then goto 0;", "JPOS: se AC < 0 (N=1), não desvia e volta ao início",
            a="AC", alu=ALU_PASSA_A, cond=COND_DESVIA_N, addr=0),
        _mi(22, "pc := band(ir, amask); goto 0;", "Desvio aceito: PC recebe os 12 bits de endereço (IR AND AMASK)",
            a="IR", b="AMASK", alu=ALU_AND, c="PC", enc=1, cond=COND_DESVIA_SEMPRE, addr=0),
        _mi(23, "alu := ac; if z then goto 22;", "JZER: se AC == 0 (Z=1), vai para linha 22 realizar o salto",
            a="AC", alu=ALU_PASSA_A, cond=COND_DESVIA_Z, addr=22),
        _mi(24, "goto 0;", "JZER: desvio não tomado (AC != 0), volta ao ciclo 0",
            cond=COND_DESVIA_SEMPRE, addr=0),
        _mi(25, "alu := tir; if n then goto 27;", "Testa bit 12 (0110=JUMP vs 0111=LOCO)",
            a="TIR", alu=ALU_PASSA_A, cond=COND_DESVIA_N, addr=27),
        _mi(26, "pc := band(ir, amask); goto 0;", "JUMP: salto incondicional para endereço x",
            a="IR", b="AMASK", alu=ALU_AND, c="PC", enc=1, cond=COND_DESVIA_SEMPRE, addr=0),
        _mi(27, "ac := band(ir, amask); goto 0;", "LOCO: carrega constante de 12 bits (0..4095) diretamente em AC",
            a="IR", b="AMASK", alu=ALU_AND, c="AC", enc=1, cond=COND_DESVIA_SEMPRE, addr=0),

        # --- 10xx: LODL, STOL, ADDL, SUBL ---
        _mi(28, "tir := lshift(ir + ir); if n then goto 40;", "Testa bit 14 (10xx vs 11xx)",
            a="IR", b="IR", alu=ALU_SOMA, sh=SH_ESQUERDA, c="TIR", enc=1, cond=COND_DESVIA_N, addr=40),
        _mi(29, "tir := lshift(tir); if n then goto 35;", "Testa bit 13 (100x vs 101x)",
            a="TIR", alu=ALU_PASSA_A, sh=SH_ESQUERDA, c="TIR", enc=1, cond=COND_DESVIA_N, addr=35),
        _mi(30, "alu := tir; if n then goto 33;", "Testa bit 12 (1000=LODL vs 1001=STOL)",
            a="TIR", alu=ALU_PASSA_A, cond=COND_DESVIA_N, addr=33),
        _mi(31, "a := ir + sp;", "LODL: calcula endereço efetivo SP + x",
            a="IR", b="SP", alu=ALU_SOMA, c="A", enc=1),
        _mi(32, "mar := a; rd; goto 7;", "LODL: inicia leitura em m[SP + x] e reutiliza linha 7",
            b="A", mar=1, rd=1, cond=COND_DESVIA_SEMPRE, addr=7),
        _mi(33, "a := ir + sp;", "STOL: calcula endereço efetivo SP + x",
            a="IR", b="SP", alu=ALU_SOMA, c="A", enc=1),
        _mi(34, "mar := a; mbr := ac; wr; goto 10;", "STOL: inicia escrita de AC em m[SP + x]",
            a="AC", b="A", alu=ALU_PASSA_A, mar=1, mbr=1, wr=1, cond=COND_DESVIA_SEMPRE, addr=10),
        _mi(35, "alu := tir; if n then goto 38;", "Testa bit 12 (1010=ADDL vs 1011=SUBL)",
            a="TIR", alu=ALU_PASSA_A, cond=COND_DESVIA_N, addr=38),
        _mi(36, "a := ir + sp;", "ADDL: calcula endereço efetivo SP + x",
            a="IR", b="SP", alu=ALU_SOMA, c="A", enc=1),
        _mi(37, "mar := a; rd; goto 13;", "ADDL: inicia leitura de m[SP + x] e reutiliza linha 13",
            b="A", mar=1, rd=1, cond=COND_DESVIA_SEMPRE, addr=13),
        _mi(38, "a := ir + sp;", "SUBL: calcula endereço efetivo SP + x",
            a="IR", b="SP", alu=ALU_SOMA, c="A", enc=1),
        _mi(39, "mar := a; rd; goto 16;", "SUBL: inicia leitura de m[SP + x] e reutiliza linha 16",
            b="A", mar=1, rd=1, cond=COND_DESVIA_SEMPRE, addr=16),

        # --- 11xx: JNEG, JNZE, CALL e grupo 1111 ---
        _mi(40, "tir := lshift(tir); if n then goto 46;", "Testa bit 13 (110x vs 111x)",
            a="TIR", alu=ALU_PASSA_A, sh=SH_ESQUERDA, c="TIR", enc=1, cond=COND_DESVIA_N, addr=46),
        _mi(41, "alu := tir; if n then goto 44;", "Testa bit 12 (1100=JNEG vs 1101=JNZE)",
            a="TIR", alu=ALU_PASSA_A, cond=COND_DESVIA_N, addr=44),
        _mi(42, "alu := ac; if n then goto 22;", "JNEG: se AC < 0 (N=1), desvia via linha 22",
            a="AC", alu=ALU_PASSA_A, cond=COND_DESVIA_N, addr=22),
        _mi(43, "goto 0;", "JNEG: desvio não tomado (AC >= 0)",
            cond=COND_DESVIA_SEMPRE, addr=0),
        _mi(44, "alu := ac; if z then goto 0;", "JNZE: se AC == 0 (Z=1), não desvia",
            a="AC", alu=ALU_PASSA_A, cond=COND_DESVIA_Z, addr=0),
        _mi(45, "pc := band(ir, amask); goto 0;", "JNZE: AC != 0, salta para endereço x",
            a="IR", b="AMASK", alu=ALU_AND, c="PC", enc=1, cond=COND_DESVIA_SEMPRE, addr=0),
        _mi(46, "tir := lshift(tir); if n then goto 50;", "Testa bit 12 (1110=CALL vs 1111=estendidas)",
            a="TIR", alu=ALU_PASSA_A, sh=SH_ESQUERDA, c="TIR", enc=1, cond=COND_DESVIA_N, addr=50),

        # --- 1110: CALL x (empilha PC e salta para x) ---
        _mi(47, "sp := sp + (-1);", "CALL: decrementa ponteiro de pilha SP",
            a="SP", b="-1", alu=ALU_SOMA, c="SP", enc=1),
        _mi(48, "mar := sp; mbr := pc; wr;", "CALL: prepara gravação do endereço de retorno (PC) na pilha",
            a="PC", b="SP", alu=ALU_PASSA_A, mar=1, mbr=1, wr=1),
        _mi(49, "pc := band(ir, amask); wr; goto 0;", "CALL: conclui escrita na pilha e salta para sub-rotina x",
            a="IR", b="AMASK", alu=ALU_AND, c="PC", enc=1, wr=1, cond=COND_DESVIA_SEMPRE, addr=0),

        # --- 1111: PSHI, POPI, PUSH, POP, RETN, SWAP, INSP, DESP ---
        _mi(50, "tir := lshift(tir); if n then goto 65;", "1111: testa bit 11 (11110xx vs 11111xx)",
            a="TIR", alu=ALU_PASSA_A, sh=SH_ESQUERDA, c="TIR", enc=1, cond=COND_DESVIA_N, addr=65),
        _mi(51, "tir := lshift(tir); if n then goto 59;", "11110: testa bit 10 (PSHI/POPI vs PUSH/POP)",
            a="TIR", alu=ALU_PASSA_A, sh=SH_ESQUERDA, c="TIR", enc=1, cond=COND_DESVIA_N, addr=59),
        _mi(52, "alu := tir; if n then goto 56;", "111100: testa bit 9 (PSHI vs POPI)",
            a="TIR", alu=ALU_PASSA_A, cond=COND_DESVIA_N, addr=56),

        # --- 1111000: PSHI (sp:=sp-1; m[sp]:=m[ac]) ---
        _mi(53, "mar := ac; rd;", "PSHI: inicia leitura indireta em m[AC]",
            b="AC", mar=1, rd=1),
        _mi(54, "sp := sp + (-1); rd;", "PSHI: decrementa SP enquanto conclui leitura de m[AC]",
            a="SP", b="-1", alu=ALU_SOMA, c="SP", enc=1, rd=1),
        _mi(55, "mar := sp; wr; goto 10;", "PSHI: grava MBR (m[AC]) no topo da pilha m[SP]",
            b="SP", mar=1, wr=1, cond=COND_DESVIA_SEMPRE, addr=10),

        # --- 1111001: POPI (m[ac]:=m[sp]; sp:=sp+1) ---
        _mi(56, "mar := sp; sp := sp + 1; rd;", "POPI: lê topo da pilha (m[SP antigo]) e incrementa SP",
            a="SP", b="+1", alu=ALU_SOMA, c="SP", enc=1, mar=1, rd=1),
        # Atenção: no MIC-1 real, MAR lê Barramento B. Para `mar := sp; sp := sp + 1`,
        # colocamos SP no Barramento B e +1 no Barramento A! (A+B = +1 + SP).
        _mi(57, "rd;", "POPI: conclui leitura do topo da pilha para MBR",
            rd=1),
        _mi(58, "mar := ac; wr; goto 10;", "POPI: escreve MBR no endereço apontado por AC (m[AC])",
            b="AC", mar=1, wr=1, cond=COND_DESVIA_SEMPRE, addr=10),

        # --- 1111010: PUSH / 1111011: POP ---
        _mi(59, "alu := tir; if n then goto 62;", "111101: testa bit 9 (PUSH vs POP)",
            a="TIR", alu=ALU_PASSA_A, cond=COND_DESVIA_N, addr=62),
        _mi(60, "sp := sp + (-1);", "PUSH: decrementa SP",
            a="SP", b="-1", alu=ALU_SOMA, c="SP", enc=1),
        _mi(61, "mar := sp; mbr := ac; wr; goto 10;", "PUSH: empilha AC em m[SP]",
            a="AC", b="SP", alu=ALU_PASSA_A, mar=1, mbr=1, wr=1, cond=COND_DESVIA_SEMPRE, addr=10),
        _mi(62, "mar := sp; sp := sp + 1; rd;", "POP: inicia leitura de m[SP] e incrementa SP",
            a="+1", b="SP", alu=ALU_SOMA, c="SP", enc=1, mar=1, rd=1),
        _mi(63, "rd;", "POP: conclui leitura do topo da pilha",
            rd=1),
        _mi(64, "ac := mbr; goto 0;", "POP: transfere valor desempilhado para AC",
            amux=AMUX_MBR, alu=ALU_PASSA_A, c="AC", enc=1, cond=COND_DESVIA_SEMPRE, addr=0),

        # --- 1111100: RETN / 1111101: SWAP ---
        _mi(65, "tir := lshift(tir); if n then goto 73;", "11111: testa bit 10 (RETN/SWAP vs INSP/DESP)",
            a="TIR", alu=ALU_PASSA_A, sh=SH_ESQUERDA, c="TIR", enc=1, cond=COND_DESVIA_N, addr=73),
        _mi(66, "alu := tir; if n then goto 70;", "111110: testa bit 9 (RETN vs SWAP)",
            a="TIR", alu=ALU_PASSA_A, cond=COND_DESVIA_N, addr=70),
        _mi(67, "mar := sp; sp := sp + 1; rd;", "RETN: inicia leitura do endereço de retorno na pilha e incrementa SP",
            a="+1", b="SP", alu=ALU_SOMA, c="SP", enc=1, mar=1, rd=1),
        _mi(68, "rd;", "RETN: conclui leitura do endereço de retorno",
            rd=1),
        _mi(69, "pc := mbr; goto 0;", "RETN: restaura PC com endereço de retorno da pilha",
            amux=AMUX_MBR, alu=ALU_PASSA_A, c="PC", enc=1, cond=COND_DESVIA_SEMPRE, addr=0),
        _mi(70, "a := ac;", "SWAP: salva AC temporariamente no registrador A",
            a="AC", alu=ALU_PASSA_A, c="A", enc=1),
        _mi(71, "ac := sp;", "SWAP: copia SP para AC",
            a="SP", alu=ALU_PASSA_A, c="AC", enc=1),
        _mi(72, "sp := a; goto 0;", "SWAP: copia antigo AC (em A) para SP",
            a="A", alu=ALU_PASSA_A, c="SP", enc=1, cond=COND_DESVIA_SEMPRE, addr=0),

        # --- 1111110: INSP y / 1111111: DESP y ---
        _mi(73, "alu := tir; if n then goto 76;", "111111: testa bit 9 (INSP vs DESP)",
            a="TIR", alu=ALU_PASSA_A, cond=COND_DESVIA_N, addr=76),
        _mi(74, "a := band(ir, smask);", "INSP: extrai constante y de 8 bits (IR AND SMASK)",
            a="IR", b="SMASK", alu=ALU_AND, c="A", enc=1),
        _mi(75, "sp := sp + a; goto 0;", "INSP/DESP: atualiza SP somando deslocamento A",
            a="SP", b="A", alu=ALU_SOMA, c="SP", enc=1, cond=COND_DESVIA_SEMPRE, addr=0),
        _mi(76, "a := band(ir, smask);", "DESP: extrai constante y de 8 bits (IR AND SMASK)",
            a="IR", b="SMASK", alu=ALU_AND, c="A", enc=1),
        _mi(77, "a := inv(a);", "DESP: inverte bits de y (passo 1 do complemento de 2)",
            a="A", alu=ALU_NOT_A, c="A", enc=1),
        _mi(78, "a := a + 1; goto 75;", "DESP: soma +1 para obter -y e salta para linha 75",
            a="A", b="+1", alu=ALU_SOMA, c="A", enc=1, cond=COND_DESVIA_SEMPRE, addr=75),
    ]

    # Correção importante na linha 56 (POPI): B precisa ser SP para ir ao MAR, e A ser +1
    for m in definicoes:
        if m.endereco == 56:
            m.a = REG_INDICE["+1"]
            m.b = REG_INDICE["SP"]
        rom[m.endereco] = m

    return rom
