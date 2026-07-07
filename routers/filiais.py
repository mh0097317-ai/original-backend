# routers/filiais.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from models import Filial
from schemas import FilialCriar, FilialOut

router = APIRouter(prefix="/api/filiais", tags=["Filiais"])


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.post("", response_model=FilialOut, status_code=status.HTTP_201_CREATED)
async def criar_filial(filial: FilialCriar, db: AsyncSession = Depends(get_db)):
    db_filial = await db.execute(select(Filial).where(Filial.cnpj == filial.cnpj))
    if db_filial.scalars().first():
        raise HTTPException(status_code=400, detail="CNPJ já registrado")

    nova_filial = Filial(**filial.model_dump())
    db.add(nova_filial)
    await db.commit()
    await db.refresh(nova_filial)
    return nova_filial


@router.get("", response_model=list[FilialOut])
async def listar_filiais(ativa: bool = True, db: AsyncSession = Depends(get_db)):
    query = select(Filial)
    if ativa is not None:
        query = query.where(Filial.ativa == ativa)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{filial_id}", response_model=FilialOut)
async def obter_filial(filial_id: str, db: AsyncSession = Depends(get_db)):
    filial = await db.execute(select(Filial).where(Filial.id == filial_id))
    db_filial = filial.scalars().first()
    if not db_filial:
        raise HTTPException(status_code=404, detail="Filial não encontrada")
    return db_filial


@router.put("/{filial_id}", response_model=FilialOut)
async def atualizar_filial(filial_id: str, filial: FilialCriar, db: AsyncSession = Depends(get_db)):
    resultado = await db.execute(select(Filial).where(Filial.id == filial_id))
    db_filial = resultado.scalars().first()
    if not db_filial:
        raise HTTPException(status_code=404, detail="Filial não encontrada")

    for campo, valor in filial.model_dump(exclude_unset=True).items():
        setattr(db_filial, campo, valor)

    await db.commit()
    await db.refresh(db_filial)
    return db_filial


@router.delete("/{filial_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_filial(filial_id: str, db: AsyncSession = Depends(get_db)):
    resultado = await db.execute(select(Filial).where(Filial.id == filial_id))
    db_filial = resultado.scalars().first()
    if not db_filial:
        raise HTTPException(status_code=404, detail="Filial não encontrada")

    db_filial.ativa = False
    await db.commit()
