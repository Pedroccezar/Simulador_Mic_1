"""
Servidor Web do Simulador MIC-1 (Tanenbaum).
Usa apenas a biblioteca padrão do Python (sem necessidade de pip install).

Como executar localmente:
    python servidor.py
Depois abra no navegador: http://localhost:8000

Como executar via Docker:
    docker compose up --build
"""

import json
import os
import threading
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

from mic1.processador import SimuladorMIC1
from mic1.montador import ErroDeMontagem

DIRETORIO_BASE = os.path.dirname(os.path.abspath(__file__))
DIRETORIO_WEB = os.path.join(DIRETORIO_BASE, "web")
DIRETORIO_EXEMPLOS = os.path.join(DIRETORIO_BASE, "exemplos")

# Instância global do processador MIC-1 simulado
simulador = SimuladorMIC1()


def carregar_exemplos() -> list:
    exemplos = []
    if os.path.isdir(DIRETORIO_EXEMPLOS):
        for nome in sorted(os.listdir(DIRETORIO_EXEMPLOS)):
            if nome.endswith(".asm"):
                caminho = os.path.join(DIRETORIO_EXEMPLOS, nome)
                with open(caminho, "r", encoding="utf-8") as f:
                    exemplos.append({
                        "arquivo": nome,
                        "titulo": nome.replace(".asm", "").replace("_", " ").title(),
                        "codigo": f.read(),
                    })
    return exemplos


# Carrega automaticamente o 1º exemplo ao iniciar o simulador
_exemplos_iniciais = carregar_exemplos()
if _exemplos_iniciais:
    simulador.carregar_assembly(_exemplos_iniciais[0]["codigo"])


class HandlerMIC1(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRETORIO_WEB, **kwargs)

    def log_message(self, format, *args):
        # Mantém o terminal limpo durante a apresentação
        pass

    def _enviar_json(self, dados: dict, status: int = 200) -> None:
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def _ler_corpo_json(self) -> dict:
        tamanho = int(self.headers.get("Content-Length", 0))
        if tamanho == 0:
            return {}
        bruto = self.rfile.read(tamanho).decode("utf-8")
        return json.loads(bruto)

    def do_GET(self):
        rota = urlparse(self.path).path

        if rota == "/api/estado":
            self._enviar_json(simulador.exportar_estado())
            return

        if rota == "/api/microprograma":
            rom = [mi.para_dict() for mi in simulador.rom_controle[:79]]
            self._enviar_json({"microprograma": rom})
            return

        if rota == "/api/exemplos":
            self._enviar_json({"exemplos": carregar_exemplos()})
            return

        if rota == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        rota = urlparse(self.path).path
        try:
            payload = self._ler_corpo_json()

            if rota == "/api/montar":
                codigo = payload.get("codigo", "")
                simulador.carregar_assembly(codigo)
                self._enviar_json({"ok": True, "estado": simulador.exportar_estado()})
                return

            if rota == "/api/passo_micro":
                simulador.executar_microinstrucao()
                self._enviar_json({"ok": True, "estado": simulador.exportar_estado()})
                return

            if rota == "/api/passo_macro":
                simulador.executar_macroinstrucao()
                self._enviar_json({"ok": True, "estado": simulador.exportar_estado()})
                return

            if rota == "/api/executar":
                limite = int(payload.get("limite", 500))
                simulador.executar_tudo(limite_macros=limite)
                self._enviar_json({"ok": True, "estado": simulador.exportar_estado()})
                return

            if rota == "/api/reset":
                if simulador.ultimo_codigo:
                    simulador.carregar_assembly(simulador.ultimo_codigo)
                else:
                    simulador.resetar_cpu()
                self._enviar_json({"ok": True, "estado": simulador.exportar_estado()})
                return

            if rota == "/api/config_cache":
                num_conjuntos = int(payload.get("num_conjuntos", 4))
                vias = int(payload.get("vias", 1))
                palavras_por_bloco = int(payload.get("palavras_por_bloco", 4))
                simulador.configurar_caches(num_conjuntos, vias, palavras_por_bloco)
                if simulador.ultimo_codigo:
                    simulador.carregar_assembly(simulador.ultimo_codigo)
                self._enviar_json({"ok": True, "estado": simulador.exportar_estado()})
                return

            self._enviar_json({"ok": False, "erro": "Rota não encontrada."}, status=404)

        except ErroDeMontagem as e:
            self._enviar_json({"ok": False, "erro": str(e)}, status=400)
        except Exception as e:
            self._enviar_json({"ok": False, "erro": f"Erro interno: {e}"}, status=500)


def main():
    host = os.environ.get("MIC1_HOST", "0.0.0.0")
    porta = int(os.environ.get("MIC1_PORT", "8000"))
    em_docker = os.environ.get("EM_DOCKER", "0") == "1"

    servidor = HTTPServer((host, porta), HandlerMIC1)
    url = f"http://localhost:{porta}"
    print("=" * 60)
    print("  Simulador MIC-1 (Tanenbaum) iniciado com sucesso!")
    print(f"  Acesse no navegador: {url}")
    print("  Pressione Ctrl+C para encerrar.")
    print("=" * 60)

    if not em_docker:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nSimulador encerrado.")
        servidor.server_close()


if __name__ == "__main__":
    main()
