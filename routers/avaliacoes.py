# routers/avaliacoes.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import get_db
from models import Avaliacao, Veiculo, Usuario
from schemas import AvaliacaoCriar, AvaliacaoOut
from routers.auth import get_usuario_atual

router = APIRouter(prefix="/avaliacoes", tags=["Avaliações"])


@router.post("/", response_model=AvaliacaoOut, status_code=201)
async def criar_avaliacao(
    dados: AvaliacaoCriar,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    # Verifica se já avaliou
    r = await db.execute(
        select(Avaliacao).where(Avaliacao.reserva_id == dados.reserva_id)
    )
    if r.scalar_one_or_none():
        raise HTTPException(409, "Você já avaliou esta reserva")

    aval = Avaliacao(
        **dados.model_dump(),
        usuario_id=usuario.id,
    )
    db.add(aval)
    await db.flush()

    # Recalcula nota do veículo
    result = await db.execute(
        select(Avaliacao).where(Avaliacao.veiculo_id == dados.veiculo_id)
    )
    todas = result.scalars().all()
    media = sum(a.nota for a in todas) / len(todas) if todas else 0

    rv = await db.execute(select(Veiculo).where(Veiculo.id == dados.veiculo_id))
    veiculo = rv.scalar_one_or_none()
    if veiculo:
        veiculo.nota_media = round(media, 2)
        veiculo.total_avaliacoes = len(todas)

    await db.flush()

    out = AvaliacaoOut.model_validate(aval)
    out.usuario_nome = usuario.nome
    return out


@router.get("/veiculo/{veiculo_id}", response_model=List[AvaliacaoOut])
async def listar_por_veiculo(
    veiculo_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Avaliacao)
        .options(selectinload(Avaliacao.usuario))
        .where(Avaliacao.veiculo_id == veiculo_id)
        .order_by(Avaliacao.criado_em.desc())
        .limit(20)
    )
    avaliacoes = result.scalars().all()
    out = []
    for a in avaliacoes:
        item = AvaliacaoOut.model_validate(a)
        item.usuario_nome = a.usuario.nome if a.usuario else None
        out.append(item)
    return out
