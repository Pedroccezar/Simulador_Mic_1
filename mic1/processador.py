"""
Núcleo de Simulação da Microarquitetura MIC-1 (Tanenbaum).

Executa fielmente os 4 subciclos do relógio para cada microinstrução:
  Subciclo 1: Busca da microinstrução na Memória de Controle (MPC -> MIR)
  Subciclo 2: Leitura dos registradores A e B para Latch A e Latch B
  Subciclo 3: AMUX -> ULA (calcula N e Z) -> Deslocador; MAR recebe Latch B se MAR=1
  Subciclo 4: Escrita pelo Barramento C no registrador C (se ENC=1),
              escrita no MBR (se MBR=1), operação de memória/cache (RD/WR),
              e cálculo do próximo MPC via Mmux + Lógica de Microssequenciamento.
"""

from .constantes import (
    REG_NOMES,
    REGS_SOMENTE_LEITURA,
    CONSTANTES_HARDWARE,
    SP_INICIAL,
    AMUX_MBR,
    COND_NAO_DESVIA,
    COND_DESVIA_N,
    COND_DESVIA_Z,
    COND_DESVIA_SEMPRE,
    ALU_SOMA,
    ALU_AND,
    ALU_PASSA_A,
    ALU_NOT_A,
    SH_ESQUERDA,
    SH_DIREITA,
    para_u16,
    para_s16,
    para_hex16,
    para_bin16,
)
from .memoria import MemoriaPrincipal
from .cache import Cache
from .microprograma import criar_memoria_de_controle
from .montador import montar, desmontar_palavra


class SimuladorMIC1:
    def __init__(self):
        self.memoria = MemoriaPrincipal()
        self.rom_controle = criar_memoria_de_controle()

        # Caches separadas (Arquitetura Harvard no nível L1): Instruções e Dados
        self.cache_instrucoes = Cache("Cache de Instruções (I-Cache)", self.memoria, num_conjuntos=4, vias=1, palavras_por_bloco=4)
        self.cache_dados = Cache("Cache de Dados (D-Cache)", self.memoria, num_conjuntos=4, vias=1, palavras_por_bloco=4)

        self.listagem_programa = []
        self.simbolos = {}
        self.ultimo_codigo = ""

        self.resetar_cpu()

    def resetar_cpu(self) -> None:
        """Reinicia todos os registradores, latches, caches e contadores (mantendo o programa carregado na RAM)."""
        self.registradores = [0] * 16
        for idx, val in CONSTANTES_HARDWARE.items():
            self.registradores[idx] = val
        self.registradores[2] = SP_INICIAL  # SP = 4096

        self.mar = 0
        self.mbr = 0
        self.mpc = 0
        self.mir = self.rom_controle[0]

        # Latches e sinais internos do último ciclo (usados para animar o diagrama SVG)
        self.latch_a = 0
        self.latch_b = 0
        self.entrada_amux = 0
        self.saida_ula = 0
        self.saida_deslocador = 0
        self.flag_n = 0
        self.flag_z = 0
        self.mmux_desviou = False

        # Controle dos 2 ciclos de leitura/escrita da memória no MIC-1
        self.ciclos_rd = 0
        self.ciclos_wr = 0
        self.leitura_eh_instrucao = False

        # Contadores e estado didático
        self.ciclos_micro = 0
        self.macro_executadas = 0
        self.finalizado = False
        self.pc_macro_atual = 0
        self.ultimo_rastro = self._rastro_inicial()
        self.historico = []

        self.cache_instrucoes.resetar()
        self.cache_dados.resetar()

    def _rastro_inicial(self) -> dict:
        return {
            "mpc_executado": None,
            "proximo_mpc": 0,
            "micro_texto": "Pronto para iniciar (MPC = 0)",
            "descricao": "Carregue um programa ou clique em 'Passo Micro' para iniciar o ciclo de busca.",
            "subciclos": [],
            "ativos": [],
            "evento_cache": None,
            "cache_usada": None,
        }

    def carregar_assembly(self, codigo_fonte: str) -> dict:
        """Monta o código Assembly MAC-1, grava na RAM e reinicia a CPU."""
        resultado = montar(codigo_fonte)
        self.ultimo_codigo = codigo_fonte
        self.listagem_programa = resultado["listagem"]
        self.simbolos = resultado["simbolos"]
        self.memoria.carregar_programa(resultado["memoria"])
        self.resetar_cpu()
        return resultado

    def configurar_caches(self, num_conjuntos: int, vias: int, palavras_por_bloco: int) -> None:
        """Atualiza a organização das caches (Direto vs Associativo por Conjunto)."""
        self.cache_instrucoes.configurar(num_conjuntos, vias, palavras_por_bloco)
        self.cache_dados.configurar(num_conjuntos, vias, palavras_por_bloco)

    def executar_microinstrucao(self) -> dict:
        """
        Executa exatamente 1 ciclo de clock da MIC-1 (os 4 subciclos do relógio).
        Retorna o dicionário de rastro didático do que ocorreu neste ciclo.
        """
        if self.finalizado:
            return self.ultimo_rastro

        ativos = set()
        subciclos = []

        # =====================================================================
        # SUBCICLO 1: Busca da microinstrução na Memória de Controle (MPC -> MIR)
        # =====================================================================
        mpc_atual = self.mpc
        if mpc_atual == 0:
            self.pc_macro_atual = self.registradores[0]

        mi = self.rom_controle[mpc_atual]
        self.mir = mi
        ativos.update(["MPC", "ROM_CONTROLE", "MIR"])
        subciclos.append(f"Subciclo 1 (Busca Controle): MPC={mpc_atual} → MIR carrega '{mi.texto}'")

        # =====================================================================
        # SUBCICLO 2: Leitura dos Registradores para Latch A e Latch B
        # =====================================================================
        self.latch_a = self.registradores[mi.a]
        self.latch_b = self.registradores[mi.b]
        ativos.add("BANCO_REGS")

        usa_a = (mi.amux == 0) and (mi.enc == 1 or mi.mbr == 1 or mi.cond in (COND_DESVIA_N, COND_DESVIA_Z))
        usa_b = (mi.mar == 1) or (mi.alu in (ALU_SOMA, ALU_AND) and (mi.enc == 1 or mi.mbr == 1 or mi.cond in (COND_DESVIA_N, COND_DESVIA_Z)))
        if usa_a:
            ativos.update(["BUS_A", "LATCH_A"])
        if usa_b:
            ativos.update(["BUS_B", "LATCH_B"])

        subciclos.append(
            f"Subciclo 2 (Leitura Regs): Latch A ← {REG_NOMES[mi.a]} ({para_s16(self.latch_a)}), "
            f"Latch B ← {REG_NOMES[mi.b]} ({para_s16(self.latch_b)})"
        )

        # =====================================================================
        # SUBCICLO 3: AMUX, ULA, Deslocador e carregamento de MAR
        # =====================================================================
        if mi.amux == AMUX_MBR:
            self.entrada_amux = self.mbr
            ativos.update(["MBR", "AMUX"])
            origem_amux = f"MBR ({para_s16(self.mbr)})"
        else:
            self.entrada_amux = self.latch_a
            if usa_a:
                ativos.add("AMUX")
            origem_amux = f"Latch A ({para_s16(self.latch_a)})"

        # Operação da ULA
        if mi.alu == ALU_SOMA:
            res_ula = para_u16(self.entrada_amux + self.latch_b)
            op_ula_nome = "A + B"
        elif mi.alu == ALU_AND:
            res_ula = para_u16(self.entrada_amux & self.latch_b)
            op_ula_nome = "A AND B"
        elif mi.alu == ALU_PASSA_A:
            res_ula = para_u16(self.entrada_amux)
            op_ula_nome = "A"
        else:  # ALU_NOT_A
            res_ula = para_u16(~self.entrada_amux)
            op_ula_nome = "NOT A"

        self.saida_ula = res_ula
        # Flags N e Z são geradas na saída da ULA (ANTES do deslocador!)
        self.flag_n = 1 if (res_ula & 0x8000) else 0
        self.flag_z = 1 if (res_ula == 0) else 0

        if usa_a or mi.amux == AMUX_MBR or usa_b:
            ativos.update(["ULA", "DESLOCADOR"])

        # Deslocador (SH)
        if mi.sh == SH_ESQUERDA:
            self.saida_deslocador = para_u16(res_ula << 1)
            sh_nome = "lshift(1)"
        elif mi.sh == SH_DIREITA:
            # Deslocamento aritmético à direita (preserva bit de sinal)
            sinal = res_ula & 0x8000
            self.saida_deslocador = para_u16((res_ula >> 1) | sinal)
            sh_nome = "rshift(1)"
        else:
            self.saida_deslocador = res_ula
            sh_nome = "sem desloc."

        # MAR carrega os 12 bits menos significativos do Latch B
        mar_msg = ""
        if mi.mar == 1:
            self.mar = self.latch_b & 0x0FFF
            ativos.update(["BUS_B", "LATCH_B", "MAR"])
            mar_msg = f" | MAR ← {self.mar} (0x{self.mar:03X})"

        subciclos.append(
            f"Subciclo 3 (ULA/SH): AMUX={origem_amux}, ULA({op_ula_nome})={para_hex16(res_ula)} "
            f"[N={self.flag_n}, Z={self.flag_z}], SH({sh_nome})={para_hex16(self.saida_deslocador)}{mar_msg}"
        )

        # =====================================================================
        # SUBCICLO 4: Escrita no Barramento C, MBR, Memória/Cache e próximo MPC
        # =====================================================================
        acoes_s4 = []

        # Escrita no registrador destino via Barramento C
        if mi.enc == 1:
            if mi.c not in REGS_SOMENTE_LEITURA:
                self.registradores[mi.c] = self.saida_deslocador
            ativos.update(["BUS_C", "BANCO_REGS"])
            acoes_s4.append(f"{REG_NOMES[mi.c]} ← {para_s16(self.saida_deslocador)} ({para_hex16(self.saida_deslocador)})")

        # Escrita no MBR
        if mi.mbr == 1:
            self.mbr = self.saida_deslocador
            ativos.update(["BUS_C", "MBR"])
            acoes_s4.append(f"MBR ← {para_hex16(self.mbr)}")

        # Acesso à Hierarquia de Memória (I-Cache / D-Cache + RAM) - 2 ciclos por RD/WR
        evento_cache = None
        cache_usada = None

        if mi.rd == 1:
            self.ciclos_wr = 0
            self.ciclos_rd += 1
            if self.ciclos_rd == 1:
                # MPC == 0 é sempre o Fetch de Instrução (I-Cache); os demais são Dados (D-Cache)
                self.leitura_eh_instrucao = (mpc_atual == 0)
                cache_usada = "ICACHE" if self.leitura_eh_instrucao else "DCACHE"
                ativos.update(["MAR", cache_usada])
                acoes_s4.append(f"RD ciclo 1/2 ({'I-Cache' if self.leitura_eh_instrucao else 'D-Cache'} em 0x{self.mar:03X})")
            elif self.ciclos_rd >= 2:
                cache_alvo = self.cache_instrucoes if self.leitura_eh_instrucao else self.cache_dados
                cache_usada = "ICACHE" if self.leitura_eh_instrucao else "DCACHE"
                valor_lido, hit = cache_alvo.ler(self.mar)
                self.mbr = valor_lido
                self.ciclos_rd = 0
                evento_cache = cache_alvo.ultimo_evento
                ativos.update(["MAR", "MBR", cache_usada])
                if not hit:
                    ativos.add("RAM")
                acoes_s4.append(
                    f"RD ciclo 2/2 ({'I-Cache' if self.leitura_eh_instrucao else 'D-Cache'} "
                    f"{'HIT' if hit else 'MISS → RAM'}): MBR ← {para_hex16(valor_lido)}"
                )
        else:
            self.ciclos_rd = 0

        if mi.wr == 1:
            self.ciclos_rd = 0
            self.ciclos_wr += 1
            cache_usada = "DCACHE"
            if self.ciclos_wr == 1:
                ativos.update(["MAR", "MBR", "DCACHE"])
                acoes_s4.append(f"WR ciclo 1/2 (D-Cache em 0x{self.mar:03X})")
            elif self.ciclos_wr >= 2:
                hit = self.cache_dados.escrever(self.mar, self.mbr)
                self.ciclos_wr = 0
                evento_cache = self.cache_dados.ultimo_evento
                ativos.update(["MAR", "MBR", "DCACHE", "RAM"])
                acoes_s4.append(
                    f"WR ciclo 2/2 (D-Cache {'HIT' if hit else 'MISS'} + Write-Through RAM): "
                    f"m[0x{self.mar:03X}] ← {para_hex16(self.mbr)}"
                )
        else:
            self.ciclos_wr = 0

        # Lógica de Microssequenciamento + Mmux -> Próximo MPC
        desviar = (
            (mi.cond == COND_DESVIA_SEMPRE)
            or (mi.cond == COND_DESVIA_N and self.flag_n == 1)
            or (mi.cond == COND_DESVIA_Z and self.flag_z == 1)
        )
        self.mmux_desviou = desviar
        ativos.update(["LOGICA_SEQ", "MMUX"])

        if desviar:
            proximo_mpc = mi.addr
            ativos.add("ADDR")
        else:
            proximo_mpc = (mpc_atual + 1) & 0xFF
            ativos.add("INCREMENTADOR")

        self.mpc = proximo_mpc
        self.ciclos_micro += 1

        # Ao voltar para MPC == 0, concluímos uma macroinstrução MAC-1!
        macro_concluida = (proximo_mpc == 0 and mpc_atual != 0)
        if macro_concluida:
            self.macro_executadas += 1
            # Detecta HALT (instrução JUMP apontando para o próprio endereço)
            ir_atual = self.registradores[3]
            pc_novo = self.registradores[0]
            if (ir_atual & 0xF000) == 0x6000 and pc_novo == self.pc_macro_atual:
                self.finalizado = True
                acoes_s4.append("HALT detectado (JUMP para o próprio endereço)")

        acoes_s4.append(f"Próximo MPC ← {proximo_mpc}" + (" (desvio)" if desviar else " (MPC+1)"))
        subciclos.append("Subciclo 4 (Escrita/Próx. MPC): " + " | ".join(acoes_s4))

        self.ultimo_rastro = {
            "ciclo": self.ciclos_micro,
            "mpc_executado": mpc_atual,
            "proximo_mpc": proximo_mpc,
            "micro_texto": mi.texto,
            "descricao": mi.comentario,
            "subciclos": subciclos,
            "ativos": sorted(ativos),
            "evento_cache": evento_cache,
            "cache_usada": cache_usada,
            "macro_concluida": macro_concluida,
        }

        self.historico.append({
            "ciclo": self.ciclos_micro,
            "mpc": mpc_atual,
            "texto": mi.texto,
            "comentario": mi.comentario,
            "cache": (
                f"{'I-Cache' if cache_usada == 'ICACHE' else 'D-Cache'} {evento_cache['resultado']}"
                if evento_cache else ""
            ),
        })
        if len(self.historico) > 80:
            self.historico = self.historico[-80:]

        return self.ultimo_rastro

    def executar_macroinstrucao(self, limite_micros: int = 40) -> list:
        """Executa microinstruções até concluir a macroinstrução atual (retornar a MPC = 0)."""
        passos = []
        for _ in range(limite_micros):
            if self.finalizado:
                break
            r = self.executar_microinstrucao()
            passos.append(r)
            if self.mpc == 0:
                break
        return passos

    def executar_tudo(self, limite_macros: int = 500) -> int:
        """Executa até detectar HALT ou atingir o limite de segurança de macroinstruções."""
        executadas = 0
        while not self.finalizado and executadas < limite_macros:
            self.executar_macroinstrucao()
            executadas += 1
        return executadas

    def exportar_estado(self) -> dict:
        """Exporta todo o estado interno da máquina para JSON (interface gráfica)."""
        regs_info = []
        for idx, nome in enumerate(REG_NOMES):
            val = self.registradores[idx]
            regs_info.append({
                "indice": idx,
                "nome": nome,
                "valor_u16": val,
                "valor_s16": para_s16(val),
                "hex": para_hex16(val),
                "binario": para_bin16(val),
                "constante": idx in REGS_SOMENTE_LEITURA,
            })

        # Monta uma visão enxuta e útil da Memória Principal:
        # endereços do programa + regiões não-zero + topo da pilha próximo a SP
        enderecos_interessantes = set(range(0, min(64, max(32, len(self.listagem_programa) + 12))))
        sp = self.registradores[2] & 0x0FFF
        for e in range(max(0, sp - 4), min(4096, sp + 12)):
            enderecos_interessantes.add(e)
        for e in range(4088, 4096):
            enderecos_interessantes.add(e)
        for e, w in enumerate(self.memoria.palavras):
            if w != 0:
                enderecos_interessantes.add(e)

        simbolos_por_end = {end: nome for nome, end in self.simbolos.items()}
        memoria_visivel = []
        for end in sorted(enderecos_interessantes):
            w = self.memoria.palavras[end]
            memoria_visivel.append({
                "endereco": end,
                "endereco_hex": f"0x{end:03X}",
                "rotulo": simbolos_por_end.get(end, ""),
                "valor_u16": w,
                "valor_s16": para_s16(w),
                "hex": para_hex16(w),
                "binario": para_bin16(w),
                "desmontado": desmontar_palavra(w),
            })

        return {
            "ciclos_micro": self.ciclos_micro,
            "macro_executadas": self.macro_executadas,
            "finalizado": self.finalizado,
            "mpc": self.mpc,
            "mar": self.mar,
            "mar_hex": f"0x{self.mar:03X}",
            "mbr": self.mbr,
            "mbr_s16": para_s16(self.mbr),
            "mbr_hex": para_hex16(self.mbr),
            "latch_a": self.latch_a,
            "latch_a_s16": para_s16(self.latch_a),
            "latch_b": self.latch_b,
            "latch_b_s16": para_s16(self.latch_b),
            "entrada_amux": self.entrada_amux,
            "saida_ula": self.saida_ula,
            "saida_ula_s16": para_s16(self.saida_ula),
            "saida_deslocador": self.saida_deslocador,
            "saida_deslocador_s16": para_s16(self.saida_deslocador),
            "flag_n": self.flag_n,
            "flag_z": self.flag_z,
            "mmux_desviou": self.mmux_desviou,
            "mir": self.mir.para_dict(),
            "mir_proximo": self.rom_controle[self.mpc].para_dict(),
            "registradores": regs_info,
            "cache_instrucoes": self.cache_instrucoes.exportar_estado(),
            "cache_dados": self.cache_dados.exportar_estado(),
            "memoria": memoria_visivel,
            "listagem": self.listagem_programa,
            "rastro": self.ultimo_rastro,
            "historico": list(reversed(self.historico[-25:])),
        }
