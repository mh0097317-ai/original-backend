# routers/movimentos.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from database import AsyncSessionLocal
from models import Movimento, Conta, StatusMovimento, TipoMovimento
from schemas import MovimentoCriar, MovimentoOut

router = APIRouter(prefix="/api/movimentos", tags=["Movimentos"])


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.post("", response_model=MovimentoOut, status_code=status.HTTP_201_CREATED)
async def criar_movimento(movimento: MovimentoCriar, db: AsyncSession = Depends(get_db)):
    conta = await db.execute(select(Conta).where(Conta.id == movimento.conta_id))
    db_conta = conta.scalars().first()
    if not db_conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    novo_movimento = Movimento(**movimento.model_dump())
    db.add(novo_movimento)

    if novo_movimento.tipo == TipoMovimento.entrada:
        db_conta.saldo_atual += novo_movimento.valor
    else:
        if db_conta.saldo_atual < novo_movimento.valor:
            raise HTTPException(status_code=400, detail="Saldo insuficiente")
        db_conta.saldo_atual -= novo_movimento.valor

    await db.commit()
    await db.refresh(novo_movimento)
    return novo_movimento


@router.get("", response_model=list[MovimentoOut])
async def listar_movimentos(
    filial_id: str = None,
    conta_id: str = None,
    categoria: str = None,
    status: str = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(Movimento)
    if filial_id:
        query = query.where(Movimento.filial_id == filial_id)
    if conta_id:
        query = query.where(Movimento.conta_id == conta_id)
    if categoria:
        query = query.where(Movimento.categoria == categoria)
    if status:
        query = query.where(Movimento.status == status)
    query = query.order_by(Movimento.data_movimento.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{movimento_id}", response_model=MovimentoOut)
async def obter_movimento(movimento_id: str, db: AsyncSession = Depends(get_db)):
    movimento = await db.execute(select(Movimento).where(Movimento.id == movimento_id))
    db_movimento = movimento.scalars().first()
    if not db_movimento:
        raise HTTPException(status_code=404, detail="Movimento não encontrado")
    return db_movimento


@router.put("/{movimento_id}/confirmar", response_model=MovimentoOut)
async def confirmar_movimento(movimento_id: str, db: AsyncSession = Depends(get_db)):
    resultado = await db.execute(select(Movimento).where(Movimento.id == movimento_id))
    db_movimento = resultado.scalars().first()
    if not db_movimento:
        raise HTTPException(status_code=404, detail="Movimento não encontrado")

    if db_movimento.status != StatusMovimento.pendente:
        raise HTTPException(status_code=400, detail="Movimento já foi processado")

    db_movimento.status = StatusMovimento.confirmado
    await db.commit()
    await db.refresh(db_movimento)
    return db_movimento


@router.delete("/{movimento_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancelar_movimento(movimento_id: str, db: AsyncSession = Depends(get_db)):
    resultado = await db.execute(select(Movimento).where(Movimento.id == movimento_id))
    db_movimento = resultado.scalars().first()
    if not db_movimento:
        raise HTTPException(status_code=404, detail="Movimento não encontrado")

    if db_movimento.status == StatusMovimento.cancelado:
        raise HTTPException(status_code=400, detail="Movimento já foi cancelado")

    conta = await db.execute(select(Conta).where(Conta.id == db_movimento.conta_id))
    db_conta = conta.scalars().first()

    if db_movimento.tipo == TipoMovimento.entrada:
        db_conta.saldo_atual -= db_movimento.valor
    else:
        db_conta.saldo_atual += db_movimento.valor

    db_movimento.status = StatusMovimento.cancelado
    await db.commit()
