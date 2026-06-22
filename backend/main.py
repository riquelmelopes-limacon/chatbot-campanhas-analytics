from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import io
import os
import glob
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from langchain_openai import ChatOpenAI
from langchain_experimental.agents import create_pandas_dataframe_agent

load_dotenv()

# Variáveis globais para armazenar os dados e o agente
dataframes_lake = []
agent_executor = None

def simular_ingestao_data_lake():
    """
    FUTURO: Aqui entrará o código que conecta no Data Lake (ex: Google BigQuery, AWS S3)
    ou puxa direto da API do Adobe Analytics via script agendado.
    ATUAL: Lê todos os CSVs da pasta 'dados/'.
    """
    global dataframes_lake, agent_executor
    
    pasta_dados = "dados"
    if not os.path.exists(pasta_dados):
        os.makedirs(pasta_dados)
        print(f"⚠️ Pasta '{pasta_dados}' criada. Por favor, adicione os CSVs do Adobe lá e reinicie o servidor.")
        return

    arquivos_csv = glob.glob(os.path.join(pasta_dados, "*.csv"))
    
    if not arquivos_csv:
        print("⚠️ Nenhum arquivo CSV encontrado na pasta 'dados'.")
        return

    print(f"🔄 Iniciando ingestão de {len(arquivos_csv)} arquivos do Data Lake (Mock)...")
    
    dataframes_lake = []
    
    for arquivo in arquivos_csv:
        try:
            # Lógica de limpeza adaptável (lê ignorando metadados do Adobe)
            with open(arquivo, 'r', encoding='utf-8-sig') as f:
                linhas = f.readlines()
                
            linhas_limpas = [linha for linha in linhas if not linha.startswith('#') and linha.strip()]
            csv_limpo = '\n'.join(linhas_limpas)
            
            df = pd.read_csv(io.StringIO(csv_limpo), header=1)
            
            # Remove a linha de "Total" se existir
            if len(df) > 0 and (pd.isna(df.iloc[0, 0]) or "v141" in str(df.iloc[0, 0])):
                df = df.iloc[1:].reset_index(drop=True)
                
            dataframes_lake.append(df)
            print(f"✅ {os.path.basename(arquivo)} carregado com sucesso. ({len(df)} linhas)")
            
        except Exception as e:
            print(f"❌ Erro ao ler {arquivo}: {e}")

    # Inicializa o Agente de IA com a lista de DataFrames
    # O LangChain é inteligente o suficiente para analisar múltiplos DataFrames ao mesmo tempo (df1, df2, etc)
    if dataframes_lake:
        llm = ChatOpenAI(temperature=0, model="gpt-4o-mini")
        
        agent_executor = create_pandas_dataframe_agent(
            llm,
            dataframes_lake, # Passamos a lista de todos os CSVs da pasta
            verbose=True,
            agent_type="openai-tools",
            allow_dangerous_code=True,
            prefix=(
                "Você é um especialista em Adobe Analytics. "
                "Você tem acesso a uma lista de DataFrames que vieram do Data Lake da empresa. "
                "Cruze os dados quando necessário e sempre formate respostas financeiras e taxas de conversão de forma amigável."
            )
        )
        print("🤖 Agente de IA ativado e pronto para analisar os dados!")

# O lifespan gerencia o que acontece quando o servidor liga e desliga
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Liga o servidor: Carrega os dados
    simular_ingestao_data_lake()
    yield
    # Desliga o servidor: Limpeza (se necessário)

app = FastAPI(title="Analytics AI Copilot API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Para testes locais
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    history: list = []

@app.get("/")
async def root():
    status = "Ativo" if agent_executor else "Sem dados"
    return {"message": "API Online", "agent_status": status, "tabelas_carregadas": len(dataframes_lake)}

@app.post("/chat")
async def chat(request: ChatRequest):
    global agent_executor
    
    if agent_executor is None:
        return {"reply": "⚠️ O agente não iniciou corretamente porque a pasta 'dados/' está vazia."}

    try:
        historico_texto = "\n".join([f"{msg['role']}: {msg['content']}" for msg in request.history[-4:]])
        prompt_final = f"Histórico:\n{historico_texto}\n\nNova Pergunta: {request.message}"
        
        resposta = agent_executor.invoke({"input": prompt_final})
        return {"reply": resposta["output"]}
        
    except Exception as e:
        return {"reply": f"❌ Erro na análise: {str(e)}"}