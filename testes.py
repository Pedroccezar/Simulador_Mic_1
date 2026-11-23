"""
Suite de testes automatizados do Simulador MIC-1.
Valida todas as 23 macroinstruções MAC-1, o montador e ambas as políticas de Cache.
Execute com: python testes.py
"""

import unittest
from mic1.processador import SimuladorMIC1
from mic1.constantes import para_s16


class TestSimuladorMIC1(unittest.TestCase):
    def rodar(self, codigo: str, limite: int = 300) -> SimuladorMIC1:
        sim = SimuladorMIC1()
        sim.carregar_assembly(codigo)
        sim.executar_tudo(limite_macros=limite)
        self.assertTrue(sim.finalizado, "Programa não chegou ao HALT dentro do limite.")
        return sim

    def test_aritmetica_direta_e_loco(self):
        # Testa LOCO, STOD, LODD, ADDD, SUBD
        sim = self.rodar("""
            LOCO 100
            STOD A
            LOCO 35
            ADDD A
            SUBD B
            STOD RES
            HALT
            A: DATA 0
            B: DATA 50
            RES: DATA 0
        """)
        self.assertEqual(para_s16(sim.registradores[1]), 85)
        self.assertEqual(para_s16(sim.memoria.ler(sim.simbolos["RES"])), 85)

    def test_saltos_condicionais_e_incondicional(self):
        # Testa JPOS, JZER, JUMP, JNEG, JNZE
        sim = self.rodar("""
            LOCO 0
            JZER PASSOU_Z
            JUMP ERRO
        PASSOU_Z:
            LOCO 5
            JNZE PASSOU_NZ
            JUMP ERRO
        PASSOU_NZ:
            JPOS PASSOU_POS
            JUMP ERRO
        PASSOU_POS:
            SUBD DEZ      ; AC = 5 - 10 = -5
            JNEG OK
            JUMP ERRO
        ERRO:
            LOCO 999
            HALT
        OK:
            LOCO 123
            HALT
        DEZ: DATA 10
        """)
        self.assertEqual(para_s16(sim.registradores[1]), 123)

    def test_pilha_e_locais_e_subrotina(self):
        # Testa PUSH, POP, CALL, RETN, LODL, STOL, ADDL, SUBL, INSP, DESP
        sim = self.rodar("""
            LOCO 20
            PUSH
            LOCO 50
            PUSH
            CALL FUNC
            INSP 2
            STOD FINAL
            HALT

        FUNC:
            DESP 1        ; espaço para variável local em SP+0
            LODL 2        ; 50 (SP+1 = retorno, SP+2 = 50, SP+3 = 20)
            ADDL 3        ; 50 + 20 = 70
            STOL 0        ; local = 70
            LODL 0        ; 70
            SUBL 3        ; 70 - 20 = 50
            PUSH
            POP           ; testa PUSH + POP preservando 50
            INSP 1        ; remove local
            RETN

        FINAL: DATA 0
        """)
        self.assertEqual(para_s16(sim.registradores[1]), 50)
        self.assertEqual(para_s16(sim.memoria.ler(sim.simbolos["FINAL"])), 50)
        self.assertEqual(sim.registradores[2], 4096)  # SP restaurado perfeitamente

    def test_indiretos_e_swap(self):
        # Testa PSHI, POPI, SWAP
        sim = self.rodar("""
            LODD PTR_X
            PSHI          ; empilha m[X] = 321
            LODD PTR_Y
            POPI          ; m[Y] = 321
            LOCO 77
            SWAP          ; AC := 4096, SP := 77
            SWAP          ; AC := 77, SP := 4096
            HALT
            PTR_X: DATA X
            PTR_Y: DATA Y
            X: DATA 321
            Y: DATA 0
        """)
        self.assertEqual(sim.memoria.ler(sim.simbolos["Y"]), 321)
        self.assertEqual(sim.registradores[1], 77)
        self.assertEqual(sim.registradores[2], 4096)

    def test_caches_direto_e_associativo(self):
        codigo_laco = """
            LOCO 0
            STOD SOMA
            LOCO 5
            STOD CONT
        LOOP:
            LODD CONT
            JZER FIM
            ADDD SOMA
            STOD SOMA
            LODD CONT
            SUBD UM
            STOD CONT
            JUMP LOOP
        FIM:
            LODD SOMA
            HALT
        UM:   DATA 1
        CONT: DATA 0
        SOMA: DATA 0
        """
        for vias in (1, 2):
            sim = SimuladorMIC1()
            sim.configurar_caches(num_conjuntos=4, vias=vias, palavras_por_bloco=4)
            sim.carregar_assembly(codigo_laco)
            sim.executar_tudo()
            self.assertTrue(sim.finalizado)
            self.assertEqual(sim.registradores[1], 15)
            # Garante que I-Cache e D-Cache realmente tiveram hits no laço!
            self.assertGreater(sim.cache_instrucoes.hits, 10)
            self.assertGreater(sim.cache_dados.hits, 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
