from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from google import genai
from google.genai import types

class Tarefa(BaseModel):
    titulo: str
    prazo: Optional[str] = None
    prioridade: int
    descricao: str

class AnaliseRequest(BaseModel):
    tarefas: List[Tarefa]
    compromissos_fixos: List[str]

class AnaliseResponse(BaseModel):
    lista_ordenada: List[dict]
    motivo_ordem: str
    recomendacoes: str
    primeira_tarefa: str
    sugestoes: str

app = FastAPI()

origins = [
    "http://127.0.0.1:5500",
    "http://localhost:8000",
    "https://productivityassistant.vercel.app/", 
    "https://produtividade-assistant.onrender.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY não encontrada. O cliente Gemini não será inicializado.")
        app.state.client = None
    else:
        app.state.client = genai.Client(api_key=api_key)

@app.get("/agenda")
async def carregar_agenda():
    compromissos_fixos = [
        "Reunião de Alinhamento do Projeto X - 23:41 às 00:41 - Zoom Call",
        "Compromisso Médico Anual - 10:00 às 11:30 - Clínica Central",
        "Treino de Tênis - 18:00 às 19:30 - Clube",
    ]
    return {"compromissos": compromissos_fixos}

@app.post("/analisar")
async def analisar_tarefas(request: AnaliseRequest):
    if not app.state.client:
        return {
            "analise": {
                "error": "Cliente Gemini não inicializado. Verifique a chave de API.",
                "detalhe": "GEMINI_API_KEY não encontrado ou inválido."
            },
            "relatorio": "A IA não conseguiu gerar relatório."
        }

    tarefas_str = "\n".join([
        f"- Título: {t.titulo}, Prazo: {t.prazo if t.prazo else 'N/A'}, Prioridade: {t.prioridade}, Descrição: {t.descricao}"
        for t in request.tarefas
    ])
    
    compromissos_str = "\n".join(request.compromissos_fixos)

    prompt = f"""
    Você é um Assistente de Produtividade focado em otimizar o dia.
    Analise a lista de Tarefas e os Compromissos Fixos a seguir.

    Tarefas a analisar (Prioridade 1 = Mais Importante, 5 = Menos Importante):
    {tarefas_str}

    Compromissos Fixos do Dia (não podem ser alterados):
    {compromissos_str if compromissos_str else 'Nenhum compromisso fixo.'}

    Com base nisso, gere uma análise detalhada em formato JSON (string) com as seguintes chaves:
    1. lista_ordenada: Uma lista de objetos. Ordene as tarefas primeiro pela PRIORIDADE (menor número = maior prioridade), depois pelo PRAZO (mais próximo).
       Cada objeto deve ter: 'titulo', 'prioridade', e 'motivo'.
    2. motivo_ordem: Motivação geral da ordem e das prioridades (máx 3 frases).
    3. recomendacoes: Recomendações de gerenciamento de tempo ou consistência (máx 3 frases).
    4. primeira_tarefa: A tarefa com a maior prioridade e prazo mais próximo.
    5. sugestoes: Sugestões de produtividade, como 'dividir tarefas grandes em subtarefas menores' ou 'usar alarmes' (máx 3 frases).

    A saída DEVE ser estritamente o objeto JSON.
    """

    try:
        response = app.state.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )

        ia_response_json_str = response.text.strip()
        
        if ia_response_json_str.startswith("```json"):
            ia_response_json_str = ia_response_json_str.strip("```json\n").strip()
        elif ia_response_json_str.startswith("{"):
            ia_response_json_str = ia_response_json_str.strip()

        return {"analise": ia_response_json_str, "relatorio": "Relatório gerado com sucesso."}
    
    except Exception as e:
        error_msg = f"Falha ao conectar ou erro HTTP com a API Gemini: {e}"
        return {
            "analise": {
                "error": error_msg, 
                "detalhe": str(e)
            }, 
            "relatorio": "A IA não conseguiu gerar relatório."
        }

@app.get("/")
def read_root():
    return {"status": "Servidor rodando"}