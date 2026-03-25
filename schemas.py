# schemas.py
from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, field_validator
from models import CategoriaEnum, StatusVeiculoEnum, StatusReservaEnum, PlanoEnum, TipoNotifEnum


# ── Auth ───────────────────────────────────────────────────
class UsuarioCadastro(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    telefone: Optional[str] = None
    cnh: Optional[str] = None
    plano: PlanoEnum = PlanoEnum.basico

class UsuarioLogin(BaseModel):
    email: EmailStr
    senha: str

class UsuarioOut(BaseModel):
    id: str
    nome: str
    email: str
    telefone: Optional[str]
    cnh: Optional[str]
    foto_url: Optional[str]
    plano: PlanoEnum
    idioma: str
    total_alugueis: int
    total_gasto: float
    criado_em: datetime
    model_config = {"from_attributes": True}

class UsuarioAtualizar(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    cnh: Optional[str] = None
    plano: Optional[PlanoEnum] = None
    idioma: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut


# ── Veículos ───────────────────────────────────────────────
class VeiculoOut(BaseModel):
    id: str
    nome: str
    marca: str
    modelo: str
    ano: int
    placa: str
    categoria: CategoriaEnum
    status: StatusVeiculoEnum
    preco_dia: float
    preco_semana: Optional[float]
    preco_mes: Optional[float]
    potencia_cv: Optional[int]
    combustivel: str
    portas: int
    lugares: int
    cambio: str
    ar_cond: bool
    gps_integrado: bool
    foto_url: Optional[str]
    nota_media: float
    total_avaliacoes: int
    model_config = {"from_attributes": True}

class CategoriaOut(BaseModel):
    id: str
    slug: CategoriaEnum
    nome: str
    nome_en: str
    icone: str
    descricao: Optional[str]
    model_config = {"from_attributes": True}


# ── Promoções ──────────────────────────────────────────────
class PromocaoOut(BaseModel):
    id: str
    codigo: str
    descricao: str
    descricao_en: Optional[str]
    desconto_pct: int
    categoria: Optional[CategoriaEnum]
    min_dias: int
    valido_ate: datetime
    model_config = {"from_attributes": True}

class ValidarCupomOut(BaseModel):
    valido: bool
    desconto_pct: int = 0
    descricao: str = ""
    mensagem: str = ""


# ── Reservas ───────────────────────────────────────────────
class ReservaCriar(BaseModel):
    veiculo_id: str
    data_retirada: datetime
    data_devolucao: datetime
    local_retirada: str
    local_devolucao: Optional[str] = None
    codigo_promo: Optional[str] = None
    seguro: bool = False
    observacoes: Optional[str] = None

    @field_validator("data_devolucao")
    @classmethod
    def devolucao_maior_retirada(cls, v, info):
        if "data_retirada" in info.data and v <= info.data["data_retirada"]:
            raise ValueError("Data de devolução deve ser posterior à retirada")
        return v

class ReservaOut(BaseModel):
    id: str
    usuario_id: str
    veiculo_id: str
    veiculo: Optional[VeiculoOut]
    status: StatusReservaEnum
    data_retirada: datetime
    data_devolucao: datetime
    local_retirada: str
    local_devolucao: Optional[str]
    preco_dia: float
    total_dias: int
    subtotal: float
    desconto_pct: int
    desconto_valor: float
    total: float
    codigo_promo: Optional[str]
    seguro: bool
    criado_em: datetime
    model_config = {"from_attributes": True}

class PrecoReservaOut(BaseModel):
    total_dias: int
    preco_dia: float
    subtotal: float
    desconto_pct: int
    desconto_valor: float
    total: float


# ── GPS ────────────────────────────────────────────────────
class GPSEnviar(BaseModel):
    veiculo_id: str
    reserva_id: str
    latitude: float
    longitude: float
    velocidade_kmh: int = 0
    combustivel_pct: int = 100
    ignicao_ligada: bool = False
    endereco: Optional[str] = None

class GPSOut(BaseModel):
    id: str
    veiculo_id: str
    reserva_id: Optional[str]
    latitude: float
    longitude: float
    velocidade_kmh: int
    combustivel_pct: int
    ignicao_ligada: bool
    endereco: Optional[str]
    registrado_em: datetime
    model_config = {"from_attributes": True}


# ── Avaliações ─────────────────────────────────────────────
class AvaliacaoCriar(BaseModel):
    reserva_id: str
    veiculo_id: str
    nota: int
    comentario: Optional[str] = None

    @field_validator("nota")
    @classmethod
    def nota_valida(cls, v):
        if not 1 <= v <= 5:
            raise ValueError("Nota deve ser entre 1 e 5")
        return v

class AvaliacaoOut(BaseModel):
    id: str
    reserva_id: str
    usuario_id: str
    veiculo_id: str
    nota: int
    comentario: Optional[str]
    criado_em: datetime
    usuario_nome: Optional[str] = None
    model_config = {"from_attributes": True}


# ── Notificações ───────────────────────────────────────────
class NotificacaoOut(BaseModel):
    id: str
    tipo: TipoNotifEnum
    titulo: str
    mensagem: str
    lida: bool
    dados: Optional[str]
    criado_em: datetime
    model_config = {"from_attributes": True}


# ── Genérico ───────────────────────────────────────────────
class Mensagem(BaseModel):
    mensagem: str
