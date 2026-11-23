FROM python:3.11-slim

WORKDIR /app

# Copia os arquivos do simulador (não exige dependências externas)
COPY mic1/ ./mic1/
COPY exemplos/ ./exemplos/
COPY web/ ./web/
COPY servidor.py testes.py ./

ENV EM_DOCKER=1
ENV MIC1_HOST=0.0.0.0
ENV MIC1_PORT=8000

EXPOSE 8000

CMD ["python", "servidor.py"]
