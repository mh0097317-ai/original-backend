# routers/contas_receber.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from database import AsyncSessionLocal
from models import ContaReceber
from schemas import ContaReceberCriar, ContaReceberOut

router = APIRouter(prefix="/api/contas-receber", tags=["Contas a Receber"])


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.post("", response_model=ContaReceberOut, status_code=status.HTTP_201_CREATED)
async def criar_conta_receber(conta: ContaReceberCriar, db: AsyncSession = Depends(get_db)):
    nova_conta = ContaReceber(**conta.model_dump())
    db.add(nova_conta)
    await db.commit()
    await db.refresh(nova_conta)
    return nova_conta


@router.get("", response_model=list[ContaReceberOut])
async def listar_contas_receber(
    cliente_nome: str = None,
    recebido: bool = False,
    vencidas: bool = False,
    db: AsyncSession = Depends(get_db)
):
    query = select(ContaReceber)
    if cliente_nome:
        query = query.where(ContaReceber.cliente_nome.ilike(f"%{cliente_nome}%"))
    if recebido is not None:
        query = query.where(ContaReceber.recebido == recebido)
    if vencidas:
        query = query.where(ContaReceber.data_vencimento < datetime.utcnow()).where(ContaReceber.recebido == False)
    query = query.order_by(ContaReceber.data_vencimento)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{conta_id}", response_model=ContaReceberOut)
async def obter_conta_receber(conta_id: str, db: AsyncSession = Depends(get_db)):
    conta = await db.execute(select(ContaReceber).where(ContaReceber.id == conta_id))
    db_conta = conta.scalars().first()
    if not db_conta:
        raise HTTPException(status_code=404, detail="Conta a receber não encontrada")
    return db_conta


@router.post("/{conta_id}/receber", response_model=ContaReceberOut)
async def receber_conta(conta_id: str, db: AsyncSession = Depends(get_db)):
    resultado = await db.execute(select(ContaReceber).where(ContaReceber.id == conta_id))
    db_conta = resultado.scalars().first()
    if not db_conta:
        raise HTTPException(status_code=404, detail="Conta a receber não encontrada")

    if db_conta.recebido:
        raise HTTPException(status_code=400, detail="Conta já foi recebida")

    db_conta.recebido = True
    db_conta.data_recebimento = datetime.utcnow()
    await db.commit()
    await db.refresh(db_conta)
    return db_conta


@router.put("/{conta_id}", response_model=ContaReceberOut)
async def atualizar_conta_receber(conta_id: str, conta: ContaReceberCriar, db: AsyncSession = Depends(get_db)):
    resultado = await db.execute(select(ContaReceber).where(ContaReceber.id == conta_id))
    db_conta = resultado.scalars().first()
    if not db_conta:
        raise HTTPException(status_code=404, detail="Conta a receber não encontrada")

    if db_conta.recebido:
        raise HTTPException(status_code=400, detail="Não é possível atualizar conta já recebida")

    for campo, valor in conta.model_dump(exclude_unset=True).items():
        setattr(db_conta, campo, valor)

    await db.commit()
    await db.refresh(db_conta)
    return db_conta


@router.delete("/{conta_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_conta_receber(conta_id: str, db: AsyncSession = Depends(get_db)):
    resultado = await db.execute(select(ContaReceber).where(ContaReceber.id == conta_id))
    db_conta = resultado.scalars().first()
    if not db_conta:
        raise HTTPException(status_code=404, detail="Conta a receber não encontrada")

    if db_conta.recebido:
        raise HTTPException(status_code=400, detail="Não é possível deletar conta já recebida")

    await db.delete(db_conta)
    await db.commit()
