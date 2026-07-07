# routers/contas_pagar.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from database import AsyncSessionLocal
from models import ContaPagar, Fornecedor
from schemas import ContaPagarCriar, ContaPagarOut

router = APIRouter(prefix="/api/contas-pagar", tags=["Contas a Pagar"])


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.post("", response_model=ContaPagarOut, status_code=status.HTTP_201_CREATED)
async def criar_conta_pagar(conta: ContaPagarCriar, db: AsyncSession = Depends(get_db)):
    fornecedor = await db.execute(select(Fornecedor).where(Fornecedor.id == conta.fornecedor_id))
    if not fornecedor.scalars().first():
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")

    nova_conta = ContaPagar(**conta.model_dump())
    db.add(nova_conta)
    await db.commit()
    await db.refresh(nova_conta)
    return nova_conta


@router.get("", response_model=list[ContaPagarOut])
async def listar_contas_pagar(
    fornecedor_id: str = None,
    pago: bool = False,
    vencidas: bool = False,
    db: AsyncSession = Depends(get_db)
):
    query = select(ContaPagar)
    if fornecedor_id:
        query = query.where(ContaPagar.fornecedor_id == fornecedor_id)
    if pago is not None:
        query = query.where(ContaPagar.pago == pago)
    if vencidas:
        query = query.where(ContaPagar.data_vencimento < datetime.utcnow()).where(ContaPagar.pago == False)
    query = query.order_by(ContaPagar.data_vencimento)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{conta_id}", response_model=ContaPagarOut)
async def obter_conta_pagar(conta_id: str, db: AsyncSession = Depends(get_db)):
    conta = await db.execute(select(ContaPagar).where(ContaPagar.id == conta_id))
    db_conta = conta.scalars().first()
    if not db_conta:
        raise HTTPException(status_code=404, detail="Conta a pagar não encontrada")
    return db_conta


@router.post("/{conta_id}/pagar", response_model=ContaPagarOut)
async def pagar_conta(conta_id: str, db: AsyncSession = Depends(get_db)):
    resultado = await db.execute(select(ContaPagar).where(ContaPagar.id == conta_id))
    db_conta = resultado.scalars().first()
    if not db_conta:
        raise HTTPException(status_code=404, detail="Conta a pagar não encontrada")

    if db_conta.pago:
        raise HTTPException(status_code=400, detail="Conta já foi paga")

    db_conta.pago = True
    db_conta.data_pagamento = datetime.utcnow()
    await db.commit()
    await db.refresh(db_conta)
    return db_conta


@router.put("/{conta_id}", response_model=ContaPagarOut)
async def atualizar_conta_pagar(conta_id: str, conta: ContaPagarCriar, db: AsyncSession = Depends(get_db)):
    resultado = await db.execute(select(ContaPagar).where(ContaPagar.id == conta_id))
    db_conta = resultado.scalars().first()
    if not db_conta:
        raise HTTPException(status_code=404, detail="Conta a pagar não encontrada")

    if db_conta.pago:
        raise HTTPException(status_code=400, detail="Não é possível atualizar conta já paga")

    for campo, valor in conta.model_dump(exclude_unset=True).items():
        setattr(db_conta, campo, valor)

    await db.commit()
    await db.refresh(db_conta)
    return db_conta


@router.delete("/{conta_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_conta_pagar(conta_id: str, db: AsyncSession = Depends(get_db)):
    resultado = await db.execute(select(ContaPagar).where(ContaPagar.id == conta_id))
    db_conta = resultado.scalars().first()
    if not db_conta:
        raise HTTPException(status_code=404, detail="Conta a pagar não encontrada")

    if db_conta.pago:
        raise HTTPException(status_code=400, detail="Não é possível deletar conta já paga")

    await db.delete(db_conta)
    await db.commit()
