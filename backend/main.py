from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import io
import os
from dotenv import load_dotenv

# Importações do LangChain
from langchain_openai import ChatOpenAI
from langchain_experimental.agents import create_pandas_dataframe_agent

# Carrega variáveis de ambiente (crie um arquivo .env na pasta backend com sua OPENAI_API_KEY)
load_dotenv()

app = FastAPI(title="Adobe Analytics AI Chat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Memória temporária para o MVP
global_df = None
agent_executor = None

class ChatRequest(BaseModel):
    message: str
    history: list = []

def limpar_csv_adobe(conteudo_csv: str) -> pd.DataFrame:
    """
    Função simplificada para limpar o CSV bruto do Adobe Analytics
    antes de entregar para o LLM, baseada na estrutura dos seus relatórios.
    """
    # Lê pulando as linhas de metadados iniciais (que começam com #)
    linhas = conteudo_csv.split('\n')
    linhas_limpas = [linha for linha in linhas if not linha.startswith('#') and linha.strip()]
    
    # Reconstrói um CSV limpo em memória
    csv_limpo = '\n'.join(linhas_limpas)
    df = pd.read_csv(io.StringIO(csv_limpo), header=1) # Assume que a linha 1 é o cabeçalho real
    
    # Remove a primeira linha de dados se for o "Total" geral do painel
    if len(df) > 0 and pd.isna(df.iloc[0, 0]) or df.iloc[0, 0] == 'Nome Da Feature (v141)':
        df = df.iloc[1:].reset_index(drop=True)

    # Renomeia as colunas para facilitar a vida do LLM
    df.columns = ['Feature', 'Impressoes', 'Aceites', 'Taxa_Conversao']
    
    # Limpeza de tipos (transformando em números para o LLM poder somar e calcular)
    df['Impressoes'] = pd.to_numeric(df['Impressoes'], errors='coerce').fillna(0)
    df['Aceites'] = pd.to_numeric(df['Aceites'], errors='coerce').fillna(0)
    df['Taxa_Conversao'] = pd.to_numeric(df['Taxa_Conversao'], errors='coerce').fillna(0)
    
    # Ignora valores inúteis
    df = df[~df['Feature'].str.lower().isin(['unspecified', 'nao especificado', 'none'])]
    
    return df

@app.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    global global_df, agent_executor
    try:
        contents = await file.read()
        conteudo_str = contents.decode('utf-8-sig')
        
        # 1. Prepara o DataFrame limpo
        global_df = limpar_csv_adobe(conteudo_str)
        
        # 2. Inicializa o LLM (GPT-4o mini é excelente para o MVP pelo custo-benefício)
        llm = ChatOpenAI(temperature=0, model="gpt-4o-mini")
        
        # 3. Cria o Agente Especialista no Pandas
        # allow_dangerous_code=True é necessário no LangChain atual pois o agente executa eval() de Python internamente
        agent_executor = create_pandas_dataframe_agent(
            llm,
            global_df,
            verbose=True, # Mostra o raciocínio da IA no terminal do backend
            agent_type="openai-tools",
            allow_dangerous_code=True,
            prefix=(
                "Você é um especialista em Adobe Analytics ajudando a equipe de dados. "
                "Você está analisando um DataFrame com métricas de engajamento diárias. "
                "A 'Taxa_Conversao' atual está em formato decimal (ex: 0.01 = 1%). Sempre formate respostas de conversão em porcentagem. "
                "Se houver muitos resultados, liste apenas os Top 5 a menos que solicitado de outra forma."
            )
        )
        
        return {"status": "success", "message": f"Arquivo carregado e agente IA ativado! {len(global_df)} features limpas prontas para análise."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/chat")
async def chat(request: ChatRequest):
    global agent_executor
    
    if agent_executor is None:
        return {"reply": "⚠️ Por favor, faça o upload de um arquivo CSV de campanha primeiro."}

    try:
        # Passamos a pergunta do usuário para o agente
        # O histórico é formatado para dar contexto caso a pergunta dependa de algo anterior
        historico_texto = "\n".join([f"{msg['role']}: {msg['content']}" for msg in request.history[-4:]]) # Pega as últimas mensagens
        
        prompt_final = f"Histórico recente da conversa:\n{historico_texto}\n\nNova Pergunta do Usuário: {request.message}"
        
        # O agente executa o código pandas internamente e retorna a string amigável
        resposta = agent_executor.invoke({"input": prompt_final})
        
        return {"reply": resposta["output"]}
        
    except Exception as e:
        return {"reply": f"❌ Desculpe, encontrei um erro ao analisar os dados: {str(e)}"}