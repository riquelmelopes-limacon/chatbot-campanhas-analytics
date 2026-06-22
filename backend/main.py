from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import io
import os
import glob
import re
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_experimental.agents import create_pandas_dataframe_agent

# 🟢 Importando os SEUS scripts que já limpam os dados do Adobe perfeitamente!
from csv_reader import read_csv
from ticket_reader import read_ticket_csv

load_dotenv()

dataframes_lake = []
agent_executor = None

def simular_ingestao_data_lake():
    global dataframes_lake, agent_executor
    
    pasta_dados = "dados"
    if not os.path.exists(pasta_dados):
        os.makedirs(pasta_dados)
        print(f"⚠️ Pasta '{pasta_dados}' criada. Adicione os CSVs lá e reinicie.")
        return

    arquivos_csv = glob.glob(os.path.join(pasta_dados, "*.csv"))
    
    if not arquivos_csv:
        print("⚠️ Nenhum arquivo CSV encontrado na pasta 'dados'.")
        return

    print(f"🔄 Iniciando ingestão de {len(arquivos_csv)} arquivos...")
    
    dataframes_lake = []
    
    for arquivo in arquivos_csv:
        nome_arquivo = arquivo.lower()
        try:
            # 🟢 Se o arquivo for o de Ticket/Faixa de Preço
            if "ticket" in nome_arquivo or "faixa" in nome_arquivo or "preço" in nome_arquivo or "preco" in nome_arquivo:
                ticket_dict = read_ticket_csv(arquivo)
                # O seu script retorna um dicionário. Pegamos a lista 'price_breakdown' e transformamos em DataFrame limpo
                df_ticket = pd.DataFrame(ticket_dict["price_breakdown"])
                # Adicionamos um prefixo na tabela para a IA saber o que é
                df_ticket.attrs["nome_tabela"] = "Ticket_Medio" 
                dataframes_lake.append(df_ticket)
                print(f"✅ Ticket Médio estruturado. ({len(df_ticket)} faixas de preço)")
            
            # 🟢 Se for o arquivo de Features de Engajamento
            else:
                features_list = read_csv(arquivo)
                # O seu script retorna uma lista de dicionários perfeitos para o Pandas
                df_features = pd.DataFrame(features_list)
                df_features.attrs["nome_tabela"] = "Features_Campanhas"
                dataframes_lake.append(df_features)
                print(f"✅ Features estruturadas. ({len(df_features)} campanhas)")
                
        except Exception as e:
            print(f"❌ Erro ao ler {arquivo}: {e}")

    if dataframes_lake:
        llm = ChatGoogleGenerativeAI(temperature=0, model="gemini-2.5-flash")
        
        agent_executor = create_pandas_dataframe_agent(
            llm,
            dataframes_lake,
            verbose=True,
            allow_dangerous_code=True,
            agent_type="tool-calling",
            handle_parsing_errors=True,
            prefix=(
                "Você é um especialista em Adobe Analytics. "
                "As tabelas fornecidas possuem colunas padronizadas em inglês: 'name' (nome da feature), 'impressions', 'accepts', 'conversion' (em decimal) e 'price' (quando aplicável). "
                "Nunca responda em branco. Se não encontrar o dado, diga."
            )
        )
        print("🤖 Agente Gemini ativado e pronto para analisar os dados limpos!")

@asynccontextmanager
async def lifespan(app: FastAPI):
    simular_ingestao_data_lake()
    yield

app = FastAPI(title="Analytics AI Copilot API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    history: list = []

@app.post("/chat")
async def chat(request: ChatRequest):
    global agent_executor
    
    if agent_executor is None:
        return {"reply": "⚠️ O agente não está ativo."}

    try:
        historico_texto = "\n".join([f"{msg['role']}: {msg['content']}" for msg in request.history[-4:]])
        prompt_final = f"Histórico:\n{historico_texto}\n\nNova Pergunta: {request.message}"
        
        resposta_raw = agent_executor.invoke({"input": prompt_final})
        resposta_texto = str(resposta_raw["output"])
        
        if "type': 'text'" in resposta_texto or "NameError" in resposta_texto:
            # Tenta resgatar a parte legível que o LLM escreveu antes do erro
            match = re.search(r"'text':\s*'([^']*)'", resposta_texto)
            if match:
                resposta_texto = match.group(1).replace('\\n', '\n')
            else:
                resposta_texto = "Desculpe, tive um erro técnico ao tentar cruzar as tabelas (NameError). Pode reformular a pergunta?"
                
        return {"reply": resposta_texto}
        
    except Exception as e:
        return {"reply": f"❌ Erro interno: {str(e)}"}