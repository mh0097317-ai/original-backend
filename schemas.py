# schemas.py
from __future__ import annotations
from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, field_validator
from models import TipoMovimento, TipoConta, StatusMovimento, CategoriaMovimento


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
    filial_id: str
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


# ── Genérico ───────────────────────────────────────────────
class Mensagem(BaseModel):
    mensagem: str
