; Exemplo 4: Acesso Indireto, SWAP e Controle de Pilha
; Demonstra: PSHI, POPI, SWAP, DESP, INSP, JNEG, JNZE
; Copia o valor apontado por PTR_ORIG para o endereço apontado por PTR_DEST.

        LODD PTR_ORIG  ; AC recebe o endereço de ORIGEM
        PSHI           ; Empilha m[AC] (ou seja, empilha 77)
        LODD PTR_DEST  ; AC recebe o endereço de DESTINO
        POPI           ; Desempilha 77 para m[AC] (ou seja, DESTINO := 77)

        ; Teste de alocação e desalocação de frame na pilha
        DESP 3         ; Reserva 3 palavras na pilha (SP := SP - 3)
        LOCO 99
        STOL 0         ; m[SP + 0] := 99
        LODL 0         ; AC := 99
        INSP 3         ; Libera as 3 palavras (SP := SP + 3)

        ; Carrega DESTINO em AC para conferência final (77)
        LODD DESTINO
        HALT

PTR_ORIG: DATA ORIGEM
PTR_DEST: DATA DESTINO
ORIGEM:   DATA 77
DESTINO:  DATA 0
