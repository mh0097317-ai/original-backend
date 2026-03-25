# models.py
import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime,
    ForeignKey, Text, Enum as SAEnum, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base


def gen_uuid():
    return str(uuid.uuid4())


# ── Enums ──────────────────────────────────────────────────
class CategoriaEnum(str, enum.Enum):
    economy  = "economy"
    suv      = "suv"
    luxo     = "luxo"
    sport    = "sport"
    eletrico = "eletrico"


class StatusVeiculoEnum(str, enum.Enum):
    disponivel  = "disponivel"
    alugado     = "alugado"
    manutencao  = "manutencao"


class StatusReservaEnum(str, enum.Enum):
    pendente   = "pendente"
    confirmada = "confirmada"
    ativa      = "ativa"
    concluida  = "concluida"
    cancelada  = "cancelada"


class PlanoEnum(str, enum.Enum):
    basico  = "basico"
    plus    = "plus"
    premium = "premium"


class TipoNotifEnum(str, enum.Enum):
    reserva    = "reserva"
    promocao   = "promocao"
    devolucao  = "devolucao"
    pagamento  = "pagamento"
    sistema    = "sistema"
    avaliacao  = "avaliacao"
    gps        = "gps"


# ── Tabelas ────────────────────────────────────────────────
class Usuario(Base):
    __tablename__ = "usuarios"

    id              = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    nome            = Column(String(150), nullable=False)
    email           = Column(String(200), unique=True, nullable=False, index=True)
    senha_hash      = Column(String(200), nullable=False)
    telefone        = Column(String(20))
    cnh             = Column(String(20), unique=True)
    foto_url        = Column(String(500))
    plano           = Column(SAEnum(PlanoEnum), default=PlanoEnum.basico)
    idioma          = Column(String(5), default="pt")
    total_alugueis  = Column(Integer, default=0)
    total_gasto     = Column(Float, default=0.0)
    ativo           = Column(Boolean, default=True)
    criado_em       = Column(DateTime, default=datetime.utcnow)
    atualizado_em   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    reservas        = relationship("Reserva", back_populates="usuario")
    avaliacoes      = relationship("Avaliacao", back_populates="usuario")
    notificacoes    = relationship("Notificacao", back_populates="usuario")


class Categoria(Base):
    __tablename__ = "categorias"

    id          = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    slug        = Column(SAEnum(CategoriaEnum), unique=True, nullable=False)
    nome        = Column(String(50), nullable=False)
    nome_en     = Column(String(50), nullable=False)
    icone       = Column(String(10), nullable=False)
    descricao   = Column(Text)
    criado_em   = Column(DateTime, default=datetime.utcnow)

    veiculos    = relationship("Veiculo", back_populates="categoria_rel")


class Veiculo(Base):
    __tablename__ = "veiculos"

    id               = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    nome             = Column(String(100), nullable=False)
    marca            = Column(String(50), nullable=False)
    modelo           = Column(String(80), nullable=False)
    ano              = Column(Integer, nullable=False)
    placa            = Column(String(10), unique=True, nullable=False)
    categoria        = Column(SAEnum(CategoriaEnum), nullable=False)
    status           = Column(SAEnum(StatusVeiculoEnum), default=StatusVeiculoEnum.disponivel)
    preco_dia        = Column(Float, nullable=False)
    preco_semana     = Column(Float)
    preco_mes        = Column(Float)
    potencia_cv      = Column(Integer)
    combustivel      = Column(String(20), default="flex")
    portas           = Column(Integer, default=4)
    lugares          = Column(Integer, default=5)
    cambio           = Column(String(20), default="automatico")
    ar_cond          = Column(Boolean, default=True)
    gps_integrado    = Column(Boolean, default=True)
    foto_url         = Column(String(500))
    nota_media       = Column(Float, default=0.0)
    total_avaliacoes = Column(Integer, default=0)
    criado_em        = Column(DateTime, default=datetime.utcnow)
    atualizado_em    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    categoria_rel    = relationship("Categoria", back_populates="veiculos")
    reservas         = relationship("Reserva", back_populates="veiculo")
    avaliacoes       = relationship("Avaliacao", back_populates="veiculo")
    gps_tracks       = relationship("RastreamentoGPS", back_populates="veiculo")


class Promocao(Base):
    __tablename__ = "promocoes"

    id            = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    codigo        = Column(String(30), unique=True, nullable=False)
    descricao     = Column(Text, nullable=False)
    descricao_en  = Column(Text)
    desconto_pct  = Column(Integer, nullable=False)
    categoria     = Column(SAEnum(CategoriaEnum))
    min_dias      = Column(Integer, default=1)
    valido_ate    = Column(DateTime, nullable=False)
    ativo         = Column(Boolean, default=True)
    usos_maximos  = Column(Integer)
    usos_atuais   = Column(Integer, default=0)
    criado_em     = Column(DateTime, default=datetime.utcnow)

    reservas      = relationship("Reserva", back_populates="promocao_rel")


class Reserva(Base):
    __tablename__ = "reservas"

    id              = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    usuario_id      = Column(UUID(as_uuid=False), ForeignKey("usuarios.id"), nullable=False)
    veiculo_id      = Column(UUID(as_uuid=False), ForeignKey("veiculos.id"), nullable=False)
    status          = Column(SAEnum(StatusReservaEnum), default=StatusReservaEnum.confirmada)
    data_retirada   = Column(DateTime, nullable=False)
    data_devolucao  = Column(DateTime, nullable=False)
    local_retirada  = Column(Text, nullable=False)
    local_devolucao = Column(Text)
    preco_dia       = Column(Float, nullable=False)
    total_dias      = Column(Integer, nullable=False)
    subtotal        = Column(Float, nullable=False)
    desconto_pct    = Column(Integer, default=0)
    desconto_valor  = Column(Float, default=0.0)
    total           = Column(Float, nullable=False)
    codigo_promo    = Column(String(30), ForeignKey("promocoes.codigo"))
    seguro          = Column(Boolean, default=False)
    observacoes     = Column(Text)
    criado_em       = Column(DateTime, default=datetime.utcnow)
    atualizado_em   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    usuario         = relationship("Usuario", back_populates="reservas")
    veiculo         = relationship("Veiculo", back_populates="reservas")
    promocao_rel    = relationship("Promocao", back_populates="reservas")
    avaliacao       = relationship("Avaliacao", back_populates="reserva", uselist=False)
    gps_tracks      = relationship("RastreamentoGPS", back_populates="reserva")


class RastreamentoGPS(Base):
    __tablename__ = "rastreamento_gps"

    id              = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    veiculo_id      = Column(UUID(as_uuid=False), ForeignKey("veiculos.id"), nullable=False)
    reserva_id      = Column(UUID(as_uuid=False), ForeignKey("reservas.id"))
    latitude        = Column(Float, nullable=False)
    longitude       = Column(Float, nullable=False)
    velocidade_kmh  = Column(Integer, default=0)
    combustivel_pct = Column(Integer, default=100)
    ignicao_ligada  = Column(Boolean, default=False)
    endereco        = Column(Text)
    registrado_em   = Column(DateTime, default=datetime.utcnow)

    veiculo         = relationship("Veiculo", back_populates="gps_tracks")
    reserva         = relationship("Reserva", back_populates="gps_tracks")


class Avaliacao(Base):
    __tablename__ = "avaliacoes"
    __table_args__ = (UniqueConstraint("reserva_id"),)

    id          = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    reserva_id  = Column(UUID(as_uuid=False), ForeignKey("reservas.id"), nullable=False)
    usuario_id  = Column(UUID(as_uuid=False), ForeignKey("usuarios.id"), nullable=False)
    veiculo_id  = Column(UUID(as_uuid=False), ForeignKey("veiculos.id"), nullable=False)
    nota        = Column(Integer, nullable=False)
    comentario  = Column(Text)
    criado_em   = Column(DateTime, default=datetime.utcnow)

    reserva     = relationship("Reserva", back_populates="avaliacao")
    usuario     = relationship("Usuario", back_populates="avaliacoes")
    veiculo     = relationship("Veiculo", back_populates="avaliacoes")


class Notificacao(Base):
    __tablename__ = "notificacoes"

    id          = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    usuario_id  = Column(UUID(as_uuid=False), ForeignKey("usuarios.id"), nullable=False)
    tipo        = Column(SAEnum(TipoNotifEnum), nullable=False)
    titulo      = Column(String(200), nullable=False)
    mensagem    = Column(Text, nullable=False)
    lida        = Column(Boolean, default=False)
    dados       = Column(Text)  # JSON string
    criado_em   = Column(DateTime, default=datetime.utcnow)

    usuario     = relationship("Usuario", back_populates="notificacoes")
