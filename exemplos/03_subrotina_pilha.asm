; Exemplo 3: Sub-rotina e Pilha (CALL, PUSH, LODL, ADDL, RETN, INSP)
; Chama a função SOMA_DOIS(12, 30) passando parâmetros pela pilha.
; Resultado esperado em AC e RESULT: 42.

        LOCO 12        ; 1º argumento = 12
        PUSH           ; Empilha 12
        LOCO 30        ; 2º argumento = 30
        PUSH           ; Empilha 30
        CALL SOMA_DOIS ; Empilha PC de retorno e salta para sub-rotina
        INSP 2         ; Limpa os 2 argumentos da pilha (SP := SP + 2)
        STOD RESULT    ; Salva retorno (42) em RESULT
        HALT

; Na entrada da função, a pilha está assim:
;   m[SP + 0] = endereço de retorno (salvo pelo CALL)
;   m[SP + 1] = 2º argumento (30)
;   m[SP + 2] = 1º argumento (12)
SOMA_DOIS:
        LODL 1         ; AC := m[SP + 1] (30)
        ADDL 2         ; AC := AC + m[SP + 2] (30 + 12 = 42)
        RETN           ; Desempilha PC de retorno e volta

RESULT: DATA 0
