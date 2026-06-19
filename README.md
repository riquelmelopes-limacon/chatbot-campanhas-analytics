# 📊 Analytics AI Copilot

O **Analytics AI Copilot** é uma aplicação inteligente desenvolvida para democratizar a análise de dados de campanhas do Adobe Analytics. Utilizando IA Generativa através do **LangChain Pandas Dataframe Agent**, a ferramenta faz o *parsing* e a limpeza dos relatórios diários em formato CSV (Módulo de Engajamento, Features e Faixas de Preço/Ticket) e permite que qualquer utilizador consulte métricas de desempenho e obtenha insights ad-hoc usando linguagem natural, mantendo o histórico e o contexto da sessão de chat.

---

## 🏗️ Estrutura do Projeto

```text
analytics-ai-chat/
├── backend/
│   ├── main.py           # API desenvolvida em FastAPI com o Agente LLM
│   ├── .env              # Variáveis de ambiente protegidas (Chave da API)
│   └── requirements.txt  # Dependências do ecossistema Python e IA
└── frontend/
    ├── src/
    │   ├── App.jsx       # Interface do Chat e Upload em React
    │   └── App.css       # Estilização da interface de conversação
    ├── package.json      # Dependências e scripts do ecossistema Node.js
    └── index.html        # Arquivo base do Frontend

```

---

## ⚙️ Passo 1: Configuração e Execução do Backend

O backend foi construído em **Python** utilizando **FastAPI** para a infraestrutura de API e **LangChain** para orquestrar o agente que traduz as perguntas do utilizador em comandos do `pandas`.

### Pré-requisitos

* Ter o Python 3.10 ou superior instalado na máquina.

### Instalação

1. Navega até a pasta do backend:
```bash
cd backend

```


2. Cria um ambiente virtual (recomendado para isolar as dependências):
```bash
python -m venv venv

```


3. Ativa o ambiente virtual:
* **No Windows:**
```bash
venv\Scripts\activate

```


* **No macOS/Linux:**
```bash
source venv/bin/activate

```




4. Instala todas as dependências necessárias listadas no `requirements.txt`:
```bash
pip install -r requirements.txt

```



### Configuração da Inteligência Artificial

O agente utiliza modelos da OpenAI para processar a lógica conversacional e gerar as consultas de dados de forma dinâmica.

1. Dentro da pasta `backend/`, cria um arquivo chamado `.env`.
2. Adiciona a tua chave privada da OpenAI no arquivo:
```env
OPENAI_API_KEY=sk-proj-SUA_CHAVE_AQUI_...

```


*(Nota: Nunca envies o arquivo `.env` para o repositório Git).*

### Execução do Servidor

Com o ambiente ativado e a chave configurada, inicia o servidor Uvicorn:

```bash
uvicorn main:app --reload

```

O servidor backend estará ativo em `http://localhost:8000`. Podes verificar a documentação interativa automática da API em `http://localhost:8000/docs`.

---

## 💻 Passo 2: Configuração e Execução do Frontend

O frontend é uma SPA (Single Page Application) limpa construída em **React**, responsável por gerir o estado das mensagens, renderizar o histórico de conversação e enviar os arquivos CSV para o servidor.

### Pré-requisitos

* Ter o Node.js (versão 18 ou superior) e o npm (ou yarn) instalados.

### Instalação

1. Abre uma nova janela no teu terminal e navega até a pasta do frontend:
```bash
cd frontend

```


2. Instala os pacotes e dependências do Node:
```bash
npm install

```



### Execução da Interface

Inicia o servidor de desenvolvimento do frontend:

```bash
npm run dev

```

*(Se o teu projeto foi criado com o Create React App clássico, utiliza `npm start`)*.

O terminal indicará a porta onde a aplicação está a rodar (geralmente `http://localhost:5173` ou `http://localhost:3000`). Abre este endereço no teu navegador.

---

## 🚀 Como Utilizar a Aplicação

1. **Aceder à Interface:** Abre o navegador no endereço do Frontend.
2. **Carregar os Dados:** Clica no botão de upload no cabeçalho da página e seleciona um arquivo CSV exportado do Adobe Analytics (ex: `IAC - Nome Da Feature (v141) (2).csv`).
3. **Validação:** Aguarda que a mensagem de status mude para `✅ CSV Carregado!`. O chat receberá uma confirmação indicando quantas linhas de dados foram limpas e estruturadas na memória do backend.
4. **Interagir:** Escreve perguntas em linguagem natural no campo de texto inferior.

### Exemplos de Perguntas para Testar:

* *“Qual foi a feature que registou o maior volume de impressões no relatório de hoje?”*
* *“Qual é a taxa de conversão exata da feature RENDAMAIS?”*
* *“Mostra-me o Top 5 de features ordenadas por número de aceites.”*
* *“Existem campanhas com aceites superiores a zero mas que tiveram menos de 50 impressões?”*

---

## 🧠 Como Funciona por Trás dos Panos?

1. **Limpeza Inteligente de Dados:** Quando fazes o upload, o FastAPI remove automaticamente os metadados do Adobe (linhas iniciadas por `#`), ignora linhas de totais gerais e trata distorções matemáticas comuns nos relatórios (como taxas de conversão brutas ou valores não especificados como `Unspecified`).
2. **Geração Dinâmica de Código:** O agente do LangChain analisa a estrutura do DataFrame gerado. Quando fazes uma pergunta como *"Qual a conversão de X?"*, o LLM escreve internamente a sintaxe exata em Python (ex: `df[df['Feature'] == 'X']['Taxa_Conversao']`), executa-a no ambiente seguro do backend e recolhe o resultado.
3. **Resposta Contextualizada:** A IA traduz o retorno puramente numérico do DataFrame de volta para uma resposta amigável em português para o utilizador, aplicando a formatação correta de percentagens e tabelas.