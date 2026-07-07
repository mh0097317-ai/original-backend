# models.py
import enum
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime,
    ForeignKey, Text, Enum as SAEnum, Numeric
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base


def gen_uuid():
    return str(uuid.uuid4())


# ── Enums ──────────────────────────────────────────────────
class TipoMovimento(str, enum.Enum):
    entrada = "entrada"
    saida = "saida"


class TipoConta(str, enum.Enum):
    caixa = "caixa"
    banco = "banco"
    cartao_credito = "cartao_credito"
    contas_receber = "contas_receber"
    contas_pagar = "contas_pagar"


class StatusMovimento(str, enum.Enum):
    pendente = "pendente"
    confirmado = "confirmado"
    cancelado = "cancelado"


class CategoriaMovimento(str, enum.Enum):
    vendas = "vendas"
    recebimento = "recebimento"
    pagamento_fornecedor = "pagamento_fornecedor"
    despesa_operacional = "despesa_operacional"
    impostos = "impostos"
    folha_pagamento = "folha_pagamento"
    financeiro = "financeiro"
    estoque = "estoque"
    outro = "outro"


# ── Models ─────────────────────────────────────────────────
class Filial(Base):
    __tablename__ = "filiais"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    nome = Column(String(200), nullable=False)
    cnpj = Column(String(20), unique=True, nullable=False)
    endereco = Column(String(300), nullable=False)
    cidade = Column(String(100), nullable=False)
    estado = Column(String(2), nullable=False)
    telefone = Column(String(20))
    email = Column(String(150))
    ativa = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contas = relationship("Conta", back_populates="filial")
    movimentos = relationship("Movimento", back_populates="filial")


class Conta(Base):
    __tablename__ = "contas"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    filial_id = Column(UUID(as_uuid=False), ForeignKey("filiais.id"), nullable=False)
    nome = Column(String(150), nullable=False)
    tipo = Column(SAEnum(TipoConta), nullable=False)
    numero_conta = Column(String(50))
    banco = Column(String(100))
    saldo_inicial = Column(Numeric(12, 2), default=0)
    saldo_atual = Column(Numeric(12, 2), default=0)
    ativa = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    filial = relationship("Filial", back_populates="contas")
    movimentos = relationship("Movimento", back_populates="conta")


class Movimento(Base):
    __tablename__ = "movimentos"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    filial_id = Column(UUID(as_uuid=False), ForeignKey("filiais.id"), nullable=False)
    conta_id = Column(UUID(as_uuid=False), ForeignKey("contas.id"), nullable=False)

    tipo = Column(SAEnum(TipoMovimento), nullable=False)
    categoria = Column(SAEnum(CategoriaMovimento), nullable=False)
    descricao = Column(String(300), nullable=False)
    valor = Column(Numeric(12, 2), nullable=False)

    data_movimento = Column(DateTime, nullable=False)
    data_competencia = Column(DateTime, nullable=False)
    status = Column(SAEnum(StatusMovimento), default=StatusMovimento.pendente)

    documento = Column(String(50))
    observacoes = Column(Text)

    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    filial = relationship("Filial", back_populates="movimentos")
    conta = relationship("Conta", back_populates="movimentos")


class Fornecedor(Base):
    __tablename__ = "fornecedores"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    nome = Column(String(200), nullable=False)
    cnpj = Column(String(20), unique=True, nullable=False)
    contato = Column(String(100))
    email = Column(String(150))
    telefone = Column(String(20))
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contas_pagar = relationship("ContaPagar", back_populates="fornecedor")


class ContaPagar(Base):
    __tablename__ = "contas_pagar"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    fornecedor_id = Column(UUID(as_uuid=False), ForeignKey("fornecedores.id"), nullable=False)

    numero_documento = Column(String(50), nullable=False)
    descricao = Column(String(300), nullable=False)
    valor = Column(Numeric(12, 2), nullable=False)

    data_vencimento = Column(DateTime, nullable=False)
    data_pagamento = Column(DateTime, nullable=True)
    pago = Column(Boolean, default=False)

    observacoes = Column(Text)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    fornecedor = relationship("Fornecedor", back_populates="contas_pagar")


class ContaReceber(Base):
    __tablename__ = "contas_receber"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    cliente_nome = Column(String(200), nullable=False)
    cliente_cnpj = Column(String(20))

    numero_documento = Column(String(50), nullable=False)
    descricao = Column(String(300), nullable=False)
    valor = Column(Numeric(12, 2), nullable=False)

    data_vencimento = Column(DateTime, nullable=False)
    data_recebimento = Column(DateTime, nullable=True)
    recebido = Column(Boolean, default=False)

    observacoes = Column(Text)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
