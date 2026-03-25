# routers/gps.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import RastreamentoGPS, Reserva, StatusReservaEnum, Usuario
from schemas import GPSEnviar, GPSOut
from routers.auth import get_usuario_atual

router = APIRouter(prefix="/gps", tags=["GPS"])


@router.post("/", response_model=GPSOut, status_code=201)
async def enviar_posicao(
    dados: GPSEnviar,
    _: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    track = RastreamentoGPS(**dados.model_dump())
    db.add(track)
    await db.flush()
    return GPSOut.model_validate(track)


@router.get("/veiculo/{veiculo_id}/ultima", response_model=GPSOut)
async def ultima_posicao(
    veiculo_id: str,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RastreamentoGPS)
        .where(RastreamentoGPS.veiculo_id == veiculo_id)
        .order_by(RastreamentoGPS.registrado_em.desc())
        .limit(1)
    )
    track = result.scalar_one_or_none()
    if not track:
        raise HTTPException(404, "Sem dados GPS para este veículo")
    return GPSOut.model_validate(track)


@router.get("/veiculo/{veiculo_id}/historico", response_model=List[GPSOut])
async def historico_gps(
    veiculo_id: str,
    limite: int = 50,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RastreamentoGPS)
        .where(RastreamentoGPS.veiculo_id == veiculo_id)
        .order_by(RastreamentoGPS.registrado_em.desc())
        .limit(limite)
    )
    return [GPSOut.model_validate(t) for t in result.scalars().all()]
