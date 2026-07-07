# routers/fornecedores.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from models import Fornecedor
from schemas import FornecedorCriar, FornecedorOut

router = APIRouter(prefix="/api/fornecedores", tags=["Fornecedores"])


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.post("", response_model=FornecedorOut, status_code=status.HTTP_201_CREATED)
async def criar_fornecedor(fornecedor: FornecedorCriar, db: AsyncSession = Depends(get_db)):
    db_fornecedor = await db.execute(select(Fornecedor).where(Fornecedor.cnpj == fornecedor.cnpj))
    if db_fornecedor.scalars().first():
        raise HTTPException(status_code=400, detail="CNPJ já registrado")

    novo_fornecedor = Fornecedor(**fornecedor.model_dump())
    db.add(novo_fornecedor)
    await db.commit()
    await db.refresh(novo_fornecedor)
    return novo_fornecedor


@router.get("", response_model=list[FornecedorOut])
async def listar_fornecedores(ativo: bool = True, db: AsyncSession = Depends(get_db)):
    query = select(Fornecedor)
    if ativo is not None:
        query = query.where(Fornecedor.ativo == ativo)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{fornecedor_id}", response_model=FornecedorOut)
async def obter_fornecedor(fornecedor_id: str, db: AsyncSession = Depends(get_db)):
    fornecedor = await db.execute(select(Fornecedor).where(Fornecedor.id == fornecedor_id))
    db_fornecedor = fornecedor.scalars().first()
    if not db_fornecedor:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")
    return db_fornecedor


@router.put("/{fornecedor_id}", response_model=FornecedorOut)
async def atualizar_fornecedor(fornecedor_id: str, fornecedor: FornecedorCriar, db: AsyncSession = Depends(get_db)):
    resultado = await db.execute(select(Fornecedor).where(Fornecedor.id == fornecedor_id))
    db_fornecedor = resultado.scalars().first()
    if not db_fornecedor:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")

    for campo, valor in fornecedor.model_dump(exclude_unset=True).items():
        setattr(db_fornecedor, campo, valor)

    await db.commit()
    await db.refresh(db_fornecedor)
    return db_fornecedor


@router.delete("/{fornecedor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_fornecedor(fornecedor_id: str, db: AsyncSession = Depends(get_db)):
    resultado = await db.execute(select(Fornecedor).where(Fornecedor.id == fornecedor_id))
    db_fornecedor = resultado.scalars().first()
    if not db_fornecedor:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")

    db_fornecedor.ativo = False
    await db.commit()
