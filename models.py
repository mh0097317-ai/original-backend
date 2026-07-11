# models.py
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime,
    ForeignKey, Text, Enum as SAEnum, Numeric, Index
)
from sqlalchemy.orm import relationship
from database import Base
from db_types import GUID, gen_uuid


# ── Enums ──────────────────────────────────────────────────
class RoleEnum(str, enum.Enum):
    admin = "admin"            # acesso total, todas as filiais
    gestor = "gestor"          # cria/edita movimentos da própria filial
    visualizador = "visualizador"  # apenas leitura


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


class AcaoAudit(str, enum.Enum):
    criar = "criar"
    atualizar = "atualizar"
    deletar = "deletar"
    confirmar = "confirmar"
    cancelar = "cancelar"
    pagar = "pagar"
    receber = "receber"
    login = "login"
    importar = "importar"
    conciliar = "conciliar"


class StatusConciliacao(str, enum.Enum):
    pendente = "pendente"        # importada, ainda não processada
    conciliado = "conciliado"    # casou com um movimento do caixa
    divergente = "divergente"    # sem movimento correspondente no caixa
    ignorado = "ignorado"        # marcada manualmente como não relevante


# ── Models ─────────────────────────────────────────────────
class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(GUID, primary_key=True, default=gen_uuid)
    nome = Column(String(150), nullable=False)
    email = Column(String(200), unique=True, nullable=False, index=True)
    senha_hash = Column(String(255), nullable=False)
    role = Column(SAEnum(RoleEnum), default=RoleEnum.visualizador, nullable=False)
    # admin pode ter filial_id nulo (vê todas); demais devem ter filial
    filial_id = Column(GUID, ForeignKey("filiais.id"), nullable=True)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    filial = relationship("Filial")


class Filial(Base):
    __tablename__ = "filiais"

    id = Column(GUID, primary_key=True, default=gen_uuid)
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

    id = Column(GUID, primary_key=True, default=gen_uuid)
    filial_id = Column(GUID, ForeignKey("filiais.id"), nullable=False)
    nome = Column(String(150), nullable=False)
    tipo = Column(SAEnum(TipoConta), nullable=False)
    numero_conta = Column(String(50))
    banco = Column(String(100))
    saldo_inicial = Column(Numeric(14, 2), default=0, nullable=False)
    saldo_atual = Column(Numeric(14, 2), default=0, nullable=False)
    ativa = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    filial = relationship("Filial", back_populates="contas")
    movimentos = relationship("Movimento", back_populates="conta")


class Movimento(Base):
    __tablename__ = "movimentos"
    __table_args__ = (
        Index("ix_mov_filial_data", "filial_id", "data_movimento"),
        Index("ix_mov_conta_status", "conta_id", "status"),
    )

    id = Column(GUID, primary_key=True, default=gen_uuid)
    filial_id = Column(GUID, ForeignKey("filiais.id"), nullable=False)
    conta_id = Column(GUID, ForeignKey("contas.id"), nullable=False)

    tipo = Column(SAEnum(TipoMovimento), nullable=False)
    categoria = Column(SAEnum(CategoriaMovimento), nullable=False)
    descricao = Column(String(300), nullable=False)
    valor = Column(Numeric(14, 2), nullable=False)

    data_movimento = Column(DateTime, nullable=False)
    data_competencia = Column(DateTime, nullable=False)
    status = Column(SAEnum(StatusMovimento), default=StatusMovimento.confirmado, nullable=False)

    documento = Column(String(50))
    observacoes = Column(Text)

    criado_por = Column(GUID, ForeignKey("usuarios.id"), nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    filial = relationship("Filial", back_populates="movimentos")
    conta = relationship("Conta", back_populates="movimentos")


class Fornecedor(Base):
    __tablename__ = "fornecedores"

    id = Column(GUID, primary_key=True, default=gen_uuid)
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

    id = Column(GUID, primary_key=True, default=gen_uuid)
    fornecedor_id = Column(GUID, ForeignKey("fornecedores.id"), nullable=False)

    numero_documento = Column(String(50), nullable=False)
    descricao = Column(String(300), nullable=False)
    valor = Column(Numeric(14, 2), nullable=False)

    data_vencimento = Column(DateTime, nullable=False)
    data_pagamento = Column(DateTime, nullable=True)
    pago = Column(Boolean, default=False)

    observacoes = Column(Text)
    criado_por = Column(GUID, ForeignKey("usuarios.id"), nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    fornecedor = relationship("Fornecedor", back_populates="contas_pagar")


class ContaReceber(Base):
    __tablename__ = "contas_receber"

    id = Column(GUID, primary_key=True, default=gen_uuid)
    cliente_nome = Column(String(200), nullable=False)
    cliente_cnpj = Column(String(20))

    numero_documento = Column(String(50), nullable=False)
    descricao = Column(String(300), nullable=False)
    valor = Column(Numeric(14, 2), nullable=False)

    data_vencimento = Column(DateTime, nullable=False)
    data_recebimento = Column(DateTime, nullable=True)
    recebido = Column(Boolean, default=False)

    observacoes = Column(Text)
    criado_por = Column(GUID, ForeignKey("usuarios.id"), nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConexaoBancaria(Base):
    """Vincula uma conta do sistema a uma conta bancária real via Pluggy (Open Finance)."""
    __tablename__ = "conexoes_bancarias"

    id = Column(GUID, primary_key=True, default=gen_uuid)
    filial_id = Column(GUID, ForeignKey("filiais.id"), nullable=False)
    conta_id = Column(GUID, ForeignKey("contas.id"), nullable=False)

    pluggy_item_id = Column(String(64), nullable=False)      # conexão no Pluggy
    pluggy_account_id = Column(String(64), nullable=False)   # conta bancária dentro do item
    banco_nome = Column(String(150))

    ativa = Column(Boolean, default=True)
    ultima_importacao = Column(DateTime, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    conta = relationship("Conta")


class TransacaoBancaria(Base):
    """Transação importada do extrato bancário (via Pluggy) para conciliação."""
    __tablename__ = "transacoes_bancarias"
    __table_args__ = (
        Index("ix_transb_conta_status", "conta_id", "status_conciliacao"),
    )

    id = Column(GUID, primary_key=True, default=gen_uuid)
    conexao_id = Column(GUID, ForeignKey("conexoes_bancarias.id"), nullable=False)
    conta_id = Column(GUID, ForeignKey("contas.id"), nullable=False)

    pluggy_transaction_id = Column(String(64), unique=True, nullable=False)
    descricao = Column(String(300), nullable=False)
    tipo = Column(SAEnum(TipoMovimento), nullable=False)     # entrada (crédito) / saida (débito)
    valor = Column(Numeric(14, 2), nullable=False)           # sempre positivo
    data = Column(DateTime, nullable=False)

    status_conciliacao = Column(SAEnum(StatusConciliacao),
                                default=StatusConciliacao.pendente, nullable=False)
    movimento_id = Column(GUID, ForeignKey("movimentos.id"), nullable=True)

    criado_em = Column(DateTime, default=datetime.utcnow)

    conexao = relationship("ConexaoBancaria")
    movimento = relationship("Movimento")


class AuditLog(Base):
    """Registro imutável de ações dos usuários sobre entidades financeiras."""
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_entidade", "entidade", "entidade_id"),
    )

    id = Column(GUID, primary_key=True, default=gen_uuid)
    usuario_id = Column(GUID, ForeignKey("usuarios.id"), nullable=True)
    usuario_nome = Column(String(150))
    acao = Column(SAEnum(AcaoAudit), nullable=False)
    entidade = Column(String(50), nullable=False)
    entidade_id = Column(GUID, nullable=True)
    detalhes = Column(Text)  # JSON serializado
    criado_em = Column(DateTime, default=datetime.utcnow)
