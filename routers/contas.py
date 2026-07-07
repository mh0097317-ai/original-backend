# routers/contas.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from models import Conta, Filial
from schemas import ContaCriar, ContaOut

router = APIRouter(prefix="/api/contas", tags=["Contas"])


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.post("", response_model=ContaOut, status_code=status.HTTP_201_CREATED)
async def criar_conta(conta: ContaCriar, db: AsyncSession = Depends(get_db)):
    filial = await db.execute(select(Filial).where(Filial.id == conta.filial_id))
    if not filial.scalars().first():
        raise HTTPException(status_code=404, detail="Filial não encontrada")

    nova_conta = Conta(**conta.model_dump())
    nova_conta.saldo_atual = nova_conta.saldo_inicial
    db.add(nova_conta)
    await db.commit()
    await db.refresh(nova_conta)
    return nova_conta


@router.get("", response_model=list[ContaOut])
async def listar_contas(filial_id: str = None, ativa: bool = True, db: AsyncSession = Depends(get_db)):
    query = select(Conta)
    if filial_id:
        query = query.where(Conta.filial_id == filial_id)
    if ativa is not None:
        query = query.where(Conta.ativa == ativa)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{conta_id}", response_model=ContaOut)
async def obter_conta(conta_id: str, db: AsyncSession = Depends(get_db)):
    conta = await db.execute(select(Conta).where(Conta.id == conta_id))
    db_conta = conta.scalars().first()
    if not db_conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    return db_conta


@router.put("/{conta_id}", response_model=ContaOut)
async def atualizar_conta(conta_id: str, conta: ContaCriar, db: AsyncSession = Depends(get_db)):
    resultado = await db.execute(select(Conta).where(Conta.id == conta_id))
    db_conta = resultado.scalars().first()
    if not db_conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    for campo, valor in conta.model_dump(exclude_unset=True).items():
        if campo != "saldo_inicial":
            setattr(db_conta, campo, valor)

    await db.commit()
    await db.refresh(db_conta)
    return db_conta


@router.delete("/{conta_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_conta(conta_id: str, db: AsyncSession = Depends(get_db)):
    resultado = await db.execute(select(Conta).where(Conta.id == conta_id))
    db_conta = resultado.scalars().first()
    if not db_conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    db_conta.ativa = False
    await db.commit()
