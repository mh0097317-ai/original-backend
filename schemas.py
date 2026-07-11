# schemas.py
from __future__ import annotations
from datetime import datetime
from typing import Optional, Generic, TypeVar
from decimal import Decimal
from pydantic import BaseModel, EmailStr, field_validator
from models import (
    TipoMovimento, TipoConta, StatusMovimento, CategoriaMovimento,
    RoleEnum, AcaoAudit, StatusConciliacao,
)

T = TypeVar("T")


# ── Paginação genérica ────────────────────────────────────
class Pagina(BaseModel, Generic[T]):
    total: int
    skip: int
    limit: int
    items: list[T]


# ── Autenticação ──────────────────────────────────────────
class UsuarioCadastro(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    role: RoleEnum = RoleEnum.visualizador
    filial_id: Optional[str] = None

    @field_validator("senha")
    @classmethod
    def senha_forte(cls, v):
        if len(v) < 6:
            raise ValueError("Senha deve ter ao menos 6 caracteres")
        return v


class UsuarioLogin(BaseModel):
    email: EmailStr
    senha: str


class UsuarioOut(BaseModel):
    id: str
    nome: str
    email: str
    role: RoleEnum
    filial_id: Optional[str]
    ativo: bool
    criado_em: datetime
    model_config = {"from_attributes": True}


class TrocarSenha(BaseModel):
    senha_atual: str
    nova_senha: str

    @field_validator("nova_senha")
    @classmethod
    def senha_forte(cls, v):
        if len(v) < 6:
            raise ValueError("Nova senha deve ter ao menos 6 caracteres")
        return v


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut


# ── Filiais ────────────────────────────────────────────────
class FilialCriar(BaseModel):
    nome: str
    cnpj: str
    endereco: str
    cidade: str
    estado: str
    telefone: Optional[str] = None
    email: Optional[str] = None


class FilialOut(BaseModel):
    id: str
    nome: str
    cnpj: str
    endereco: str
    cidade: str
    estado: str
    telefone: Optional[str]
    email: Optional[str]
    ativa: bool
    criado_em: datetime
    model_config = {"from_attributes": True}


# ── Contas ────────────────────────────────────────────────
class ContaCriar(BaseModel):
    filial_id: str
    nome: str
    tipo: TipoConta
    numero_conta: Optional[str] = None
    banco: Optional[str] = None
    saldo_inicial: Decimal = Decimal("0.00")


class ContaAtualizar(BaseModel):
    nome: Optional[str] = None
    tipo: Optional[TipoConta] = None
    numero_conta: Optional[str] = None
    banco: Optional[str] = None


class ContaOut(BaseModel):
    id: str
    filial_id: str
    nome: str
    tipo: TipoConta
    numero_conta: Optional[str]
    banco: Optional[str]
    saldo_inicial: Decimal
    saldo_atual: Decimal
    ativa: bool
    criado_em: datetime
    model_config = {"from_attributes": True}


# ── Movimentos ────────────────────────────────────────────
class MovimentoCriar(BaseModel):
    conta_id: str
    tipo: TipoMovimento
    categoria: CategoriaMovimento
    descricao: str
    valor: Decimal
    data_movimento: datetime
    data_competencia: datetime
    documento: Optional[str] = None
    observacoes: Optional[str] = None

    @field_validator("valor")
    @classmethod
    def valor_positivo(cls, v):
        if v <= 0:
            raise ValueError("Valor deve ser maior que zero")
        return v


class MovimentoOut(BaseModel):
    id: str
    filial_id: str
    conta_id: str
    tipo: TipoMovimento
    categoria: CategoriaMovimento
    descricao: str
    valor: Decimal
    data_movimento: datetime
    data_competencia: datetime
    status: StatusMovimento
    documento: Optional[str]
    observacoes: Optional[str]
    criado_por: Optional[str]
    criado_em: datetime
    model_config = {"from_attributes": True}


# ── Fornecedores ──────────────────────────────────────────
class FornecedorCriar(BaseModel):
    nome: str
    cnpj: str
    contato: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None


class FornecedorOut(BaseModel):
    id: str
    nome: str
    cnpj: str
    contato: Optional[str]
    email: Optional[str]
    telefone: Optional[str]
    ativo: bool
    criado_em: datetime
    model_config = {"from_attributes": True}


# ── Contas a Pagar ────────────────────────────────────────
class ContaPagarCriar(BaseModel):
    fornecedor_id: str
    numero_documento: str
    descricao: str
    valor: Decimal
    data_vencimento: datetime
    observacoes: Optional[str] = None

    @field_validator("valor")
    @classmethod
    def valor_positivo(cls, v):
        if v <= 0:
            raise ValueError("Valor deve ser maior que zero")
        return v


class ContaPagarOut(BaseModel):
    id: str
    fornecedor_id: str
    numero_documento: str
    descricao: str
    valor: Decimal
    data_vencimento: datetime
    data_pagamento: Optional[datetime]
    pago: bool
    observacoes: Optional[str]
    criado_em: datetime
    model_config = {"from_attributes": True}


# ── Contas a Receber ──────────────────────────────────────
class ContaReceberCriar(BaseModel):
    cliente_nome: str
    cliente_cnpj: Optional[str] = None
    numero_documento: str
    descricao: str
    valor: Decimal
    data_vencimento: datetime
    observacoes: Optional[str] = None

    @field_validator("valor")
    @classmethod
    def valor_positivo(cls, v):
        if v <= 0:
            raise ValueError("Valor deve ser maior que zero")
        return v


class ContaReceberOut(BaseModel):
    id: str
    cliente_nome: str
    cliente_cnpj: Optional[str]
    numero_documento: str
    descricao: str
    valor: Decimal
    data_vencimento: datetime
    data_recebimento: Optional[datetime]
    recebido: bool
    observacoes: Optional[str]
    criado_em: datetime
    model_config = {"from_attributes": True}


# ── Auditoria ─────────────────────────────────────────────
class AuditLogOut(BaseModel):
    id: str
    usuario_id: Optional[str]
    usuario_nome: Optional[str]
    acao: AcaoAudit
    entidade: str
    entidade_id: Optional[str]
    detalhes: Optional[str]
    criado_em: datetime
    model_config = {"from_attributes": True}


# ── Relatórios ────────────────────────────────────────────
class FluxoDeCaixaOut(BaseModel):
    data: datetime
    saldo_inicial: Decimal
    entradas: Decimal
    saidas: Decimal
    saldo_final: Decimal


class DREOut(BaseModel):
    periodo: str
    receitas_vendas: Decimal
    despesas_operacionais: Decimal
    folha_pagamento: Decimal
    impostos: Decimal
    resultado_liquido: Decimal


class ResumoContasOut(BaseModel):
    total_contas_pagar: Decimal
    total_contas_receber: Decimal
    saldo_geral: Decimal
    contas_pagar_vencidas: int
    contas_receber_vencidas: int


# ── Conciliação bancária (Pluggy) ─────────────────────────
class ConexaoBancariaCriar(BaseModel):
    conta_id: str
    pluggy_item_id: str
    pluggy_account_id: str
    banco_nome: Optional[str] = None


class ConexaoBancariaOut(BaseModel):
    id: str
    filial_id: str
    conta_id: str
    pluggy_item_id: str
    pluggy_account_id: str
    banco_nome: Optional[str]
    ativa: bool
    ultima_importacao: Optional[datetime]
    criado_em: datetime
    model_config = {"from_attributes": True}


class TransacaoBancariaOut(BaseModel):
    id: str
    conexao_id: str
    conta_id: str
    pluggy_transaction_id: str
    descricao: str
    tipo: TipoMovimento
    valor: Decimal
    data: datetime
    status_conciliacao: StatusConciliacao
    movimento_id: Optional[str]
    criado_em: datetime
    model_config = {"from_attributes": True}


class ImportarExtratoIn(BaseModel):
    data_inicio: datetime
    data_fim: datetime


class ImportacaoOut(BaseModel):
    importadas: int
    ja_existentes: int


class ConciliacaoResultadoOut(BaseModel):
    conciliadas: int
    divergentes: int
    pendentes: int


class ConciliarManualIn(BaseModel):
    movimento_id: str


class LancarTransacaoIn(BaseModel):
    categoria: CategoriaMovimento = CategoriaMovimento.outro
    descricao: Optional[str] = None


class ConnectTokenOut(BaseModel):
    access_token: str


class ResumoConciliacaoOut(BaseModel):
    total: int
    conciliadas: int
    divergentes: int
    pendentes: int
    ignoradas: int


# ── Genérico ───────────────────────────────────────────────
class Mensagem(BaseModel):
    mensagem: str
