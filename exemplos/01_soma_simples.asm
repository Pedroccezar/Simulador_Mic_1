; Exemplo 1: Soma e Subtração Direta
; Demonstra: LODD, ADDD, SUBD, STOD, HALT
; Calcula: RESULT = (NUM1 + NUM2) - NUM3 = (15 + 27) - 10 = 32

INICIO: LODD NUM1      ; AC := m[NUM1] (15)
        ADDD NUM2      ; AC := AC + m[NUM2] (42)
        SUBD NUM3      ; AC := AC - m[NUM3] (32)
        STOD RESULT    ; m[RESULT] := AC (32)
        HALT           ; Encerra execução (JUMP para o próprio endereço)

NUM1:   DATA 15
NUM2:   DATA 27
NUM3:   DATA 10
RESULT: DATA 0
