import uvicorn
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from validate_docbr import CPF
from dateutil.parser import parse, ParserError

# --- Modelos de Dados ---

class HorarioDisponivel(BaseModel):
    data: str
    horarios: Dict[str, Any]

class DadosHorarios(BaseModel):
    horarios_disponiveis: List[HorarioDisponivel]

class PacientePayload(BaseModel):
    nome_paciente: Optional[str] = ""
    telefone_paciente: Optional[str] = ""
    data_nascimento_paciente: Optional[str] = ""
    cpf_paciente: Optional[str] = ""
    id_agenda_escolhido: Optional[str] = ""
    dados_horarios: Optional[Any] = ""

    @field_validator('dados_horarios', mode='before')
    @classmethod
    def parse_json_string(cls, value):
        if isinstance(value, str) and value.strip():
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
    title="API de Processamento de Agendamentos Flexível",
    description="Formata apenas os campos enviados com valor válido.",
    version="3.1.0"
)

# --- Funções utilitárias ---

def formatar_e_validar_nome(nome: str) -> str:
    nome_limpo = " ".join(nome.strip().split())
    return nome_limpo.title()

def identificar_genero(nome: str) -> str:
    male_names = ["Lucas", "João", "Pedro", "Carlos", "Gabriel", "Rafael", "Matheus", "Bruno"]
    female_names = ["Ana", "Maria", "Juliana", "Larissa", "Camila", "Fernanda", "Beatriz"]
    primeiro_nome = nome.split(" ")[0].lower()
    if primeiro_nome in [n.lower() for n in male_names]: return "M"
    if primeiro_nome in [n.lower() for n in female_names]: return "F"
    if primeiro_nome.endswith(("a", "e")): return "F"
    return "M"

def formatar_e_validar_telefone(phone: str) -> str:
    phone_digits = re.sub(r'\D', '', phone)
    if phone_digits.startswith('55'):
        phone_digits = phone_digits[2:]
    if not (10 <= len(phone_digits) <= 11):
        raise HTTPException(status_code=400, detail=f"Número '{phone}' inválido.")
    return phone_digits

def formatar_e_validar_data_nascimento(date_str: str) -> str:
    try:
        data_nasc = parse(date_str, dayfirst=True)
        if data_nasc > datetime.now():
            raise HTTPException(status_code=400, detail="Data de nascimento no futuro.")
        if (datetime.now().year - data_nasc.year) > 120:
            raise HTTPException(status_code=400, detail="Idade acima de 120 anos.")
        return data_nasc.strftime('%Y-%m-%d')
    except (ParserError, ValueError):
        raise HTTPException(status_code=400, detail=f"Data '{date_str}' inválida.")

def formatar_e_validar_cpf(cpf_str: str) -> str:
    cpf_validator = CPF()
    cpf_digits = re.sub(r'\D', '', cpf_str)
    if not cpf_validator.validate(cpf_digits):
        raise HTTPException(status_code=400, detail="CPF inválido.")
    return cpf_digits

def identificar_id_agenda(id_agenda_escolhido: str, dados_horarios: DadosHorarios) -> str:
    if not dados_horarios or not dados_horarios.horarios_disponiveis:
        raise HTTPException(status_code=404, detail="Lista de horários vazia.")
    try:
        primeira_data_str = dados_horarios.horarios_disponiveis[0].data
        ano_base = datetime.strptime(primeira_data_str, "%Y-%m-%d").year
        dt_alvo = parse(id_agenda_escolhido, dayfirst=True, default=datetime(ano_base, 1, 1))
    except Exception:
        raise HTTPException(status_code=400, detail="Formato de data inválido.")
    data_alvo_str = dt_alvo.strftime('%Y-%m-%d')
    hora_alvo_str = dt_alvo.strftime('%H:%M')
    for item_dia in dados_horarios.horarios_disponiveis:
        if item_dia.data == data_alvo_str:
            for id_completo in item_dia.horarios:
                if hora_alvo_str in id_completo:
                    return id_completo
    raise HTTPException(status_code=404, detail="Horário não encontrado.")

# --- Endpoint Principal ---
@app.post("/processar", response_model=RespostaFormatada)
def processar_agendamento(payload: PacientePayload):
    try:
        result = {}

        if payload.nome_paciente and payload.nome_paciente.strip():
            nome_formatado = formatar_e_validar_nome(payload.nome_paciente)
            result["nome_formatado"] = nome_formatado
            result["genero"] = identificar_genero(nome_formatado)

        if payload.telefone_paciente and payload.telefone_paciente.strip():
            result["telefone_formatado"] = formatar_e_validar_telefone(payload.telefone_paciente)

        if payload.data_nascimento_paciente and payload.data_nascimento_paciente.strip():
            result["data_nascimento_formatada"] = formatar_e_validar_data_nascimento(payload.data_nascimento_paciente)

        if payload.cpf_paciente and payload.cpf_paciente.strip():
            result["cpf_formatado"] = formatar_e_validar_cpf(payload.cpf_paciente)

        if payload.id_agenda_escolhido and payload.dados_horarios:
            result["id_agenda"] = identificar_id_agenda(payload.id_agenda_escolhido, payload.dados_horarios)

        if not result:
            raise HTTPException(status_code=400, detail="Nenhum campo válido foi enviado.")

        return result

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Erro inesperado: {e}")
        raise HTTPException(status_code=500, detail="Erro interno no servidor.")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


