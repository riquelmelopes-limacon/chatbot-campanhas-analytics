# Usa uma imagem oficial do Node.js baseada no Alpine (super leve)
FROM node:18-alpine

# Define a pasta de trabalho
WORKDIR /app

# Copia os arquivos de dependência
COPY package*.json ./

# Instala as dependências do Node
RUN npm install

# Copia o resto do código
COPY . .

# Comando para rodar o Vite. 
# O "--host 0.0.0.0" é obrigatório no Docker para que a porta 5173 seja acessível fora do contêiner.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]