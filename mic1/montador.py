from .constantes import para_u16, para_bin16, para_hex16

# Instruções com operando de 12 bits (endereço x ou constante 0..4095)
OPCODES_12BITS = {
    "LODD": 0x0000,
    "STOD": 0x1000,
    "ADDD": 0x2000,
    "SUBD": 0x3000,
    "JPOS": 0x4000,
    "JZER": 0x5000,
    "JUMP": 0x6000,
    "LOCO": 0x7000,
    "LODL": 0x8000,
    "STOL": 0x9000,
    "ADDL": 0xA000,
    "SUBL": 0xB000,
    "JNEG": 0xC000,
    "JNZE": 0xD000,
    "CALL": 0xE000,
}

# Instruções sem operando (16 bits fixos)
OPCODES_SEM_OPERANDO = {
    "PSHI": 0xF000,
    "POPI": 0xF200,
    "PUSH": 0xF400,
    "POP":  0xF600,
    "RETN": 0xF800,
    "SWAP": 0xFA00,
}

# Instruções com operando de 8 bits (constante y: 0..255)
OPCODES_8BITS = {
    "INSP": 0xFC00,
    "DESP": 0xFE00,
}


class ErroDeMontagem(Exception):
    """Exceção lançada quando há erro de sintaxe ou valor inválido no Assembly MAC-1."""
    pass


def _parse_numero(token: str, linha_num: int) -> int:
    try:
        return int(token, 0)
    except ValueError:
        raise ErroDeMontagem(f"Linha {linha_num}: valor ou rótulo '{token}' não reconhecido.")


def montar(codigo_fonte: str) -> dict:
    """
    Monta um programa em Assembly MAC-1 em duas passagens:
      1ª passagem: registra rótulos e calcula o endereço de cada instrução/dado.
      2ª passagem: traduz cada mnemônico e operando para palavra de 16 bits.
    """
    linhas_cruas = codigo_fonte.splitlines()
    tabela_simbolos = {}
    itens = []
    endereco_atual = 0

    # 1ª PASSAGEM: limpeza, extração de rótulos e mapeamento de endereços
    for num_linha, linha_original in enumerate(linhas_cruas, start=1):
        # Remove comentários
        limpa = linha_original
        for marcador in (";", "//", "#"):
            if marcador in limpa:
                limpa = limpa.split(marcador, 1)[0]
        limpa = limpa.strip()
        if not limpa:
            continue

        # Verifica rótulo ("ROTULO: ...")
        rotulo = None
        if ":" in limpa:
            parte_rotulo, resto = limpa.split(":", 1)
            rotulo = parte_rotulo.strip().upper()
            if not rotulo or " " in rotulo:
                raise ErroDeMontagem(f"Linha {num_linha}: rótulo inválido '{parte_rotulo}'.")
            if rotulo in tabela_simbolos:
                raise ErroDeMontagem(f"Linha {num_linha}: rótulo duplicado '{rotulo}'.")
            tabela_simbolos[rotulo] = endereco_atual
            limpa = resto.strip()
            if not limpa:
                continue

        partes = limpa.split()
        mnemonico = partes[0].upper()
        operando_str = partes[1] if len(partes) > 1 else None

        if len(partes) > 2:
            raise ErroDeMontagem(f"Linha {num_linha}: argumentos em excesso em '{limpa}'.")

        # Diretiva opcional ORG para definir endereço explicitamente
        if mnemonico == "ORG":
            if operando_str is None:
                raise ErroDeMontagem(f"Linha {num_linha}: ORG exige um endereço.")
            novo_end = _parse_numero(operando_str, num_linha)
            if not (0 <= novo_end <= 4095):
                raise ErroDeMontagem(f"Linha {num_linha}: endereço ORG fora do limite (0..4095).")
            endereco_atual = novo_end
            if rotulo:
                tabela_simbolos[rotulo] = endereco_atual
            continue

        if endereco_atual > 4095:
            raise ErroDeMontagem(f"Linha {num_linha}: programa excedeu o limite de 4096 palavras.")

        itens.append({
            "linha": num_linha,
            "endereco": endereco_atual,
            "rotulo": rotulo,
            "mnemonico": mnemonico,
            "operando": operando_str,
            "fonte": limpa,
        })
        endereco_atual += 1

    if not itens:
        raise ErroDeMontagem("O código-fonte está vazio. Escreva pelo menos uma instrução MAC-1.")

    # 2ª PASSAGEM: geração das palavras de 16 bits
    memoria = {}
    listagem = []

    for item in itens:
        num_linha = item["linha"]
        end = item["endereco"]
        mnem = item["mnemonico"]
        op = item["operando"]

        if mnem in ("DATA", ".WORD", "WORD"):
            if op is None:
                raise ErroDeMontagem(f"Linha {num_linha}: {mnem} exige um valor inicial.")
            if op.upper() in tabela_simbolos:
                valor = tabela_simbolos[op.upper()]
            else:
                valor = _parse_numero(op, num_linha)
            palavra = para_u16(valor)

        elif mnem == "HALT":
            if op is not None:
                raise ErroDeMontagem(f"Linha {num_linha}: HALT não aceita operandos.")
            # Pseudo-instrução: JUMP para o próprio endereço (detectado como parada pelo simulador)
            palavra = OPCODES_12BITS["JUMP"] | (end & 0x0FFF)

        elif mnem in OPCODES_12BITS:
            if op is None:
                raise ErroDeMontagem(f"Linha {num_linha}: instrução {mnem} exige um operando (0..4095 ou rótulo).")
            if op.upper() in tabela_simbolos:
                val = tabela_simbolos[op.upper()]
            else:
                val = _parse_numero(op, num_linha)
            if not (0 <= val <= 4095):
                raise ErroDeMontagem(f"Linha {num_linha}: operando de {mnem} deve estar entre 0 e 4095 (recebido: {val}).")
            palavra = OPCODES_12BITS[mnem] | (val & 0x0FFF)

        elif mnem in OPCODES_SEM_OPERANDO:
            if op is not None:
                raise ErroDeMontagem(f"Linha {num_linha}: instrução {mnem} não aceita operandos.")
            palavra = OPCODES_SEM_OPERANDO[mnem]

        elif mnem in OPCODES_8BITS:
            if op is None:
                raise ErroDeMontagem(f"Linha {num_linha}: instrução {mnem} exige uma constante de 0 a 255.")
            val = _parse_numero(op, num_linha)
            if not (0 <= val <= 255):
                raise ErroDeMontagem(f"Linha {num_linha}: operando de {mnem} deve estar entre 0 e 255 (recebido: {val}).")
            palavra = OPCODES_8BITS[mnem] | (val & 0x00FF)

        else:
            raise ErroDeMontagem(f"Linha {num_linha}: mnemônico desconhecido '{mnem}'.")

        memoria[end] = palavra
        listagem.append({
            "linha": num_linha,
            "endereco": end,
            "endereco_hex": f"0x{end:03X}",
            "rotulo": item["rotulo"] or "",
            "fonte": item["fonte"],
            "palavra": palavra,
            "hex": para_hex16(palavra),
            "binario": para_bin16(palavra),
            "eh_dado": mnem in ("DATA", ".WORD", "WORD"),
        })

    return {
        "memoria": memoria,
        "listagem": listagem,
        "simbolos": tabela_simbolos,
    }


def desmontar_palavra(palavra: int) -> str:
    """Converte uma palavra de 16 bits de volta para mnemônico legível (didático)."""
    w = para_u16(palavra)
    op4 = w & 0xF000
    x = w & 0x0FFF

    mapa_12 = {v: k for k, v in OPCODES_12BITS.items()}
    if op4 in mapa_12:
        return f"{mapa_12[op4]} {x}"

    # Grupo 1111
    op7 = w & 0xFE00
    if op7 == 0xFC00:
        return f"INSP {w & 0x00FF}"
    if op7 == 0xFE00:
        return f"DESP {w & 0x00FF}"

    mapa_0 = {v: k for k, v in OPCODES_SEM_OPERANDO.items()}
    if op7 in mapa_0:
        return mapa_0[op7]

    return f"DATA {w}"
