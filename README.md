# Simulador MIC-1

Trabalho da disciplina de Arquitetura de Computadores.

Simulador da microarquitetura MIC-1 (Tanenbaum) feito em Python, com montador para MAC-1, interface gráfica no navegador e cache L1 separada para instruções e dados.

## Requisitos

- Docker / Docker Compose, ou
- Python 3 (não usa bibliotecas externas)

## Como rodar

### Com Docker

bash
docker compose up --build


Sem o compose:

bash
docker build -t simulador-mic1 .
docker run -p 8000:8000 simulador-mic1


Depois basta abrir http://localhost:8000 no navegador.

### Direto com Python

bash
python3 servidor.py


## Estrutura do projeto

- servidor.py - servidor HTTP que conecta a interface ao simulador.
- testes.py - testes unitários das 23 instruções e das caches.
- mic1/constantes.py - registradores de 16 bits, constantes de hardware e sinais de controle.
- mic1/memoria.py - memória principal de 4096 palavras (16 bits).
- mic1/montador.py - montador MAC-1 em duas passagens.
- mic1/microprograma.py - memória de controle (256 x 32 bits) com as microinstruções de 0 a 78.
- mic1/processador.py - ciclo de execução (4 subciclos), ULA, deslocador, latches, MAR/MBR e MPC/MIR.
- mic1/cache.py - I-Cache e D-Cache com mapeamento direto ou associativo 2-vias (LRU) e política write-through.
- exemplos/ - programas .asm prontos para teste.
- web/ - arquivos da interface (HTML, CSS, JS e diagrama SVG).

## Sintaxe do montador

- Aceita as 23 macroinstruções padrão do MAC-1 (LODD, STOD, ADDD, SUBD, JPOS, JZER, JUMP, LOCO, LODL, STOL, ADDL, SUBL, JNEG, JNZE, CALL, PSHI, POPI, PUSH, POP, RETN, SWAP, INSP, DESP).
- Rótulos terminam com : (ex: LOOP:).
- HALT funciona como pseudo-instrução de parada (monta como JUMP para o próprio endereço).

## Integrantes

- Pedro Henrique Cezar Castilho
- Manuel Pedro Christianes de Almeida Magalhães
- Nicolas Damasceno de Souza
- Rodrigo Silva Moreno
