# routers/reservas.py
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import get_db
from models import Reserva, Veiculo, Promocao, Usuario, StatusReservaEnum, StatusVeiculoEnum
from schemas import ReservaCriar, ReservaOut, PrecoReservaOut, Mensagem
from routers.auth import get_usuario_atual

router = APIRouter(prefix="/reservas", tags=["Reservas"])


def calcular_preco(preco_dia: float, total_dias: int, promocao: Optional[Promocao]) -> dict:
    subtotal = round(preco_dia * total_dias, 2)
    desconto_pct = 0
    desconto_valor = 0.0

    if promocao:
        desconto_pct = promocao.desconto_pct
        desconto_valor = round(subtotal * desconto_pct / 100, 2)

    total = round(subtotal - desconto_valor, 2)
    return dict(
        subtotal=subtotal,
        desconto_pct=desconto_pct,
        desconto_valor=desconto_valor,
        total=total,
    )


@router.post("/calcular-preco", response_model=PrecoReservaOut)
async def calcular(
    veiculo_id: str,
    data_retirada: datetime,
    data_devolucao: datetime,
    codigo_promo: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_usuario_atual),
):
    # Busca veículo
    r = await db.execute(select(Veiculo).where(Veiculo.id == veiculo_id))
    veiculo = r.scalar_one_or_none()
    if not veiculo:
        raise HTTPException(404, "Veículo não encontrado")

    total_dias = max(1, (data_devolucao - data_retirada).days)

    # Valida promoção
    promocao = None
    if codigo_promo:
        pr = await db.execute(
            select(Promocao).where(
                Promocao.codigo == codigo_promo.upper(),
                Promocao.ativo == True,
                Promocao.valido_ate >= datetime.utcnow(),
                Promocao.min_dias <= total_dias,
            )
        )
        promocao = pr.scalar_one_or_none()

    preco = calcular_preco(veiculo.preco_dia, total_dias, promocao)
    return PrecoReservaOut(
        total_dias=total_dias,
        preco_dia=veiculo.preco_dia,
        **preco,
    )


@router.post("/", response_model=ReservaOut, status_code=201)
async def criar_reserva(
    dados: ReservaCriar,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    # Busca veículo
    rv = await db.execute(select(Veiculo).where(Veiculo.id == dados.veiculo_id))
    veiculo = rv.scalar_one_or_none()
    if not veiculo:
        raise HTTPException(404, "Veículo não encontrado")
    if veiculo.status != StatusVeiculoEnum.disponivel:
        raise HTTPException(409, "Veículo não está disponível")

    total_dias = max(1, (dados.data_devolucao - dados.data_retirada).days)

    # Valida promoção
    promocao = None
    if dados.codigo_promo:
        rp = await db.execute(
            select(Promocao).where(
                Promocao.codigo == dados.codigo_promo.upper(),
                Promocao.ativo == True,
                Promocao.valido_ate >= datetime.utcnow(),
                Promocao.min_dias <= total_dias,
            )
        )
        promocao = rp.scalar_one_or_none()
        if not promocao:
            raise HTTPException(400, "Código promocional inválido ou expirado")
        if promocao.usos_maximos and promocao.usos_atuais >= promocao.usos_maximos:
            raise HTTPException(400, "Cupom esgotado")

    preco = calcular_preco(veiculo.preco_dia, total_dias, promocao)

    reserva = Reserva(
        usuario_id=usuario.id,
        veiculo_id=veiculo.id,
        data_retirada=dados.data_retirada,
        data_devolucao=dados.data_devolucao,
        local_retirada=dados.local_retirada,
        local_devolucao=dados.local_devolucao,
        codigo_promo=dados.codigo_promo.upper() if dados.codigo_promo else None,
        seguro=dados.seguro,
        observacoes=dados.observacoes,
        preco_dia=veiculo.preco_dia,
        total_dias=total_dias,
        **preco,
    )
    db.add(reserva)

    # Atualiza uso do cupom
    if promocao:
        promocao.usos_atuais += 1

    await db.flush()

    # Recarrega com veiculo
    result = await db.execute(
        select(Reserva)
        .options(selectinload(Reserva.veiculo))
        .where(Reserva.id == reserva.id)
    )
    return ReservaOut.model_validate(result.scalar_one())


@router.get("/", response_model=List[ReservaOut])
async def minhas_reservas(
    status: Optional[StatusReservaEnum] = None,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Reserva)
        .options(selectinload(Reserva.veiculo))
        .where(Reserva.usuario_id == usuario.id)
        .order_by(Reserva.criado_em.desc())
    )
    if status:
        query = query.where(Reserva.status == status)

    result = await db.execute(query)
    return [ReservaOut.model_validate(r) for r in result.scalars().all()]


@router.get("/ativa", response_model=Optional[ReservaOut])
async def reserva_ativa(
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Reserva)
        .options(selectinload(Reserva.veiculo))
        .where(Reserva.usuario_id == usuario.id, Reserva.status == StatusReservaEnum.ativa)
        .limit(1)
    )
    reserva = result.scalar_one_or_none()
    return ReservaOut.model_validate(reserva) if reserva else None


@router.patch("/{reserva_id}/cancelar", response_model=Mensagem)
async def cancelar_reserva(
    reserva_id: str,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Reserva).where(Reserva.id == reserva_id, Reserva.usuario_id == usuario.id)
    )
    reserva = result.scalar_one_or_none()
    if not reserva:
        raise HTTPException(404, "Reserva não encontrada")
    if reserva.status in (StatusReservaEnum.concluida, StatusReservaEnum.cancelada):
        raise HTTPException(400, f"Reserva já está {reserva.status.value}")

    reserva.status = StatusReservaEnum.cancelada
    reserva.atualizado_em = datetime.utcnow()

    # Libera veículo
    rv = await db.execute(select(Veiculo).where(Veiculo.id == reserva.veiculo_id))
    veiculo = rv.scalar_one_or_none()
    if veiculo:
        veiculo.status = StatusVeiculoEnum.disponivel

    await db.flush()
    return Mensagem(mensagem="Reserva cancelada com sucesso")
