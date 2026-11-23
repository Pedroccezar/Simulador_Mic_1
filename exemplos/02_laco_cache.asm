; Exemplo 2: Laço de Repetição (Ideal para demonstrar Cache Hits!)
; Soma os inteiros de 5 até 1: 5 + 4 + 3 + 2 + 1 = 15
; Observe na aba Caches: após a 1ª iteração, a I-Cache acerta quase 100% (localidade temporal)!

        LOCO 0         ; AC := 0
        STOD SOMA      ; SOMA := 0
        LOCO 5         ; AC := 5 (contador)
        STOD CONT      ; CONT := 5

LOOP:   LODD CONT      ; Carrega contador
        JZER FIM       ; Se CONT == 0, sai do laço
        ADDD SOMA      ; AC := CONT + SOMA
        STOD SOMA      ; Atualiza SOMA
        LODD CONT      ; Recarrega CONT
        SUBD UM        ; CONT := CONT - 1
        STOD CONT      ; Salva CONT
        JUMP LOOP      ; Volta ao início do laço

FIM:    LODD SOMA      ; Deixa resultado final (15) no AC
        HALT

UM:     DATA 1
CONT:   DATA 0
SOMA:   DATA 0
