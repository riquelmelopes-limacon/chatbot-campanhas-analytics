# Usa uma imagem oficial do Python, versão enxuta (slim)
FROM python:3.11-slim

# Define a pasta de trabalho dentro do contêiner
WORKDIR /app

# Copia apenas o arquivo de dependências primeiro (otimiza o cache do Docker)
COPY requirements.txt .

# Instala as dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# O código em si será mapeado via volume no Docker Compose para o --reload funcionar,
# mas copiamos por garantia para quando formos gerar a imagem de produção.
COPY . .

# Comando para rodar a aplicação habilitando o acesso externo (0.0.0.0) e o reload
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]