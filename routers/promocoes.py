# routers/promocoes.py
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import Promocao, Usuario
from schemas import PromocaoOut, ValidarCupomOut
from routers.auth import get_usuario_atual

router = APIRouter(prefix="/promocoes", tags=["Promoções"])


@router.get("/", response_model=List[PromocaoOut])
async def listar(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Promocao)
        .where(Promocao.ativo == True, Promocao.valido_ate >= datetime.utcnow())
        .order_by(Promocao.desconto_pct.desc())
    )
    return [PromocaoOut.model_validate(p) for p in result.scalars().all()]


@router.get("/validar/{codigo}", response_model=ValidarCupomOut)
async def validar_cupom(
    codigo: str,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_usuario_atual),
):
    result = await db.execute(
        select(Promocao).where(
            Promocao.codigo == codigo.upper(),
            Promocao.ativo == True,
            Promocao.valido_ate >= datetime.utcnow(),
        )
    )
    promo = result.scalar_one_or_none()

    if not promo:
        return ValidarCupomOut(valido=False, mensagem="Cupom inválido ou expirado")

    if promo.usos_maximos and promo.usos_atuais >= promo.usos_maximos:
        return ValidarCupomOut(valido=False, mensagem="Cupom esgotado")

    return ValidarCupomOut(
        valido=True,
        desconto_pct=promo.desconto_pct,
        descricao=promo.descricao,
        mensagem=f"Cupom válido! {promo.desconto_pct}% de desconto aplicado.",
    )
