# Imagem mínima e autocontida. A ferramenta usa só a biblioteca padrão;
# instalamos pytest para permitir rodar os testes dentro do contêiner.
FROM python:3.12-slim

WORKDIR /app

# Instala as dependências primeiro (camada em cache).
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do artefato.
COPY . .

# `src/` no path para `python -m contextguard` funcionar sem instalação.
ENV PYTHONPATH=/app/src

# Sem rede, sem privilégios, sem estado externo: o contêiner só computa.
ENTRYPOINT ["python", "-m", "contextguard"]
CMD ["demo"]
