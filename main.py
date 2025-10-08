# main.py
import uvicorn
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from validate_docbr import CPF
from dateutil.parser import parse, ParserError

# --- Modelos de Dados (Validação com Pydantic) ---

class HorarioDisponivel(BaseModel):
    data: Optional[str] = None
    horarios: Optional[Dict[str, Any]] = None

class DadosHorarios(BaseModel):
    horarios_disponiveis: Optional[List[HorarioDisponivel]] = None

class PacientePayload(BaseModel):
    nome_paciente: Optional[str] = None
    telefone_paciente: Optional[str] = None
    data_nascimento_paciente: Optional[str] = None
    cpf_paciente: Optional[str] = None
    id_agenda_escolhido: Optional[str] = None
    dados_horarios: Optional[Any] = Field(default=None, alias='dados_horarios')

    @field_validator('dados_horarios', mode='before')
    @classmethod
    def parse_json_string(cls, value):
        """Permite que dados_horarios seja string JSON ou dict."""
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValueError("O campo 'dados_horarios' contém um JSON malformado.")
        return value

class RespostaFormatada(BaseModel):
    genero: Optional[str] = None
    nome_formatado: Optional[str] = None
    telefone_formatado: Optional[str] = None
    data_nascimento_formatada: Optional[str] = None
    cpf_formatado: Optional[str] = None
    id_agenda: Optional[str] = None

# --- Inicialização do FastAPI ---
app = FastAPI(
    title="API de Processamento de Agendamentos",
    description="API que aceita dados_horarios como string JSON e valida CPF.",
    version="3.1.0"
)

# --- Funções utilitárias ---

def formatar_e_validar_nome(nome: Optional[str]) -> Optional[str]:
    if not nome:
        return None
    return " ".join(nome.strip().split()).title()

def identificar_genero(nome: Optional[str]) -> Optional[str]:
    if not nome:
        return None
    male_names = ["Abel", "Carlos", "Eduardo", "Fernando", "Gustavo", "Henrique", "João", "Lucas", "Miguel", "Pedro", "Ricardo", "Samuel", "Tiago", "Vitor", "Yuri", "Renê", "Noa", "Fabrízio", "Ícaro", "Denis", "Luis", "Marcos", "Rodrigo", "André", "Matheus", "Felipe", "Danilo", "Gabriel", "Leonardo", "Rafael", "Bruno"]
    female_names = ["Ana", "Beatriz", "Carla", "Daniela", "Elaine", "Fernanda", "Gabriela", "Helena", "Isabela", "Juliana", "Karla", "Larissa", "Mariana", "Natália", "Priscila", "Renata", "Tatiane", "Vanessa", "Dominique", "Evelyn", "Celeste", "Amarílis", "Laís", "Ísis", "Camila", "Patrícia", "Jéssica", "Lorena", "Sabrina", "Viviane", "Anny", "Emily", "Kelly", "Jenny", "Lilly", "Agnes", "Eloise", "Yasmin", "Yasmim", "Miriam", "Jasmim"]
    primeiro_nome = nome.split(" ")[0].lower()
    if primeiro_nome in [n.lower() for n in male_names]:
        return "M"
    if primeiro_nome in [n.lower() for n in female_names]:
        return "F"
    if primeiro_nome[-1] in ['a', 'e']:
        return "F"
    return "M"

def formatar_e_validar_telefone(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    phone_digits = re.sub(r'\D', '', phone)
    if phone_digits.startswith('55'):
        phone_digits = phone_digits[2:]
    if not (10 <= len(phone_digits) <= 11):
        raise HTTPException(status_code=400, detail=f"Número de telefone '{phone}' parece inválido. Deve conter DDD + número.")
    return phone_digits

def formatar_e_validar_data_nascimento(date_str: Optional[str]) -> Optional[str]:
    if not date_str:
        return None
    try:
        data_nasc = parse(date_str, dayfirst=True)
        if data_nasc > datetime.now():
            raise HTTPException(status_code=400, detail="Data de nascimento não pode ser futura.")
        if (datetime.now().year - data_nasc.year) > 120:
            raise HTTPException(status_code=400, detail="Idade informada é superior a 120 anos.")
        return data_nasc.strftime('%Y-%m-%d')
    except (ParserError, ValueError):
        raise HTTPException(status_code=400, detail=f"Formato de data '{date_str}' é inválido.")

def formatar_e_validar_cpf(cpf_str: Optional[str]) -> Optional[str]:
    if not cpf_str:
        return None
    cpf_validator = CPF()
    cpf_digits = re.sub(r'\D', '', cpf_str)
    if not cpf_validator.validate(cpf_digits):
        raise HTTPException(status_code=400, detail="O CPF informado é inválido.")
    return cpf_digits

def identificar_id_agenda(id_agenda_escolhido: Optional[str], dados_horarios: Optional[dict]) -> Optional[str]:
    if not id_agenda_escolhido or not dados_horarios:
        return None

    # Garante que estamos lidando com dict
    if isinstance(dados_horarios, DadosHorarios):
        dados_horarios = dados_horarios.dict()

    horarios_disponiveis = dados_horarios.get("horarios_disponiveis", [])
    if not horarios_disponiveis:
        raise HTTPException(status_code=404, detail="A lista de horários disponíveis está vazia.")

    try:
        primeira_data_str = horarios_disponiveis[0]["data"]
        ano_base = datetime.strptime(primeira_data_str, "%Y-%m-%d").year
        dt_alvo = parse(id_agenda_escolhido, dayfirst=True, default=datetime(ano_base, 1, 1))
    except Exception:
        raise HTTPException(status_code=400, detail=f"Formato de data e hora '{id_agenda_escolhido}' é inválido.")

    data_alvo_str = dt_alvo.strftime('%Y-%m-%d')
    hora_alvo_str = dt_alvo.strftime('%H:%M')

    for dia in horarios_disponiveis:
        if dia["data"] == data_alvo_str:
            for id_completo in dia["horarios"]:
                try:
                    _, _, _, _, hora_chave = id_completo.split('|')
                    if hora_chave == hora_alvo_str:
                        return id_completo
                except ValueError:
                    continue

    raise HTTPException(status_code=404, detail=f"O horário '{id_agenda_escolhido}' não foi encontrado.")

# --- Rota Principal ---
@app.post("/processar", response_model=RespostaFormatada)
def processar_agendamento(payload: PacientePayload):
    try:
        nome_formatado = formatar_e_validar_nome(payload.nome_paciente)
        telefone_formatado = formatar_e_validar_telefone(payload.telefone_paciente)
        data_nascimento_formatada = formatar_e_validar_data_nascimento(payload.data_nascimento_paciente)
        cpf_formatado = formatar_e_validar_cpf(payload.cpf_paciente)
        genero = identificar_genero(nome_formatado)
        id_agenda = identificar_id_agenda(payload.id_agenda_escolhido, payload.dados_horarios)

        return RespostaFormatada(
            genero=genero,
            nome_formatado=nome_formatado,
            telefone_formatado=telefone_formatado,
            data_nascimento_formatada=data_nascimento_formatada,
            cpf_formatado=cpf_formatado,
            id_agenda=id_agenda
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"[ERRO INTERNO] {e}")
        raise HTTPException(status_code=500, detail="Ocorreu um erro interno no servidor.")

