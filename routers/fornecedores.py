# routers/fornecedores.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Fornecedor, Usuario, AcaoAudit
from schemas import FornecedorCriar, FornecedorOut, Pagina
from security import get_usuario_atual, requer_gestor, registrar_audit

router = APIRouter(prefix="/api/fornecedores", tags=["Fornecedores"])


@router.post("", response_model=FornecedorOut, status_code=status.HTTP_201_CREATED)
async def criar_fornecedor(
    fornecedor: FornecedorCriar,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(requer_gestor),
):
    existe = await db.execute(select(Fornecedor).where(Fornecedor.cnpj == fornecedor.cnpj))
    if existe.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="CNPJ já registrado")

    novo = Fornecedor(**fornecedor.model_dump())
    db.add(novo)
    await db.flush()
    await registrar_audit(db, usuario, AcaoAudit.criar, "fornecedor", novo.id, {"nome": novo.nome})
    return novo


@router.get("", response_model=Pagina[FornecedorOut])
async def listar_fornecedores(
    ativo: bool = True,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    limit = min(limit, 200)
    cond = [Fornecedor.ativo == ativo] if ativo is not None else []
    total = await db.execute(select(func.count(Fornecedor.id)).where(*cond))
    result = await db.execute(select(Fornecedor).where(*cond).offset(skip).limit(limit))
    return Pagina(total=total.scalar() or 0, skip=skip, limit=limit,
                  items=list(result.scalars().all()))


@router.get("/{fornecedor_id}", response_model=FornecedorOut)
async def obter_fornecedor(
    fornecedor_id: str,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    fornecedor = await db.execute(select(Fornecedor).where(Fornecedor.id == fornecedor_id))
    db_fornecedor = fornecedor.scalar_one_or_none()
    if not db_fornecedor:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")
    return db_fornecedor


@router.put("/{fornecedor_id}", response_model=FornecedorOut)
async def atualizar_fornecedor(
    fornecedor_id: str,
    fornecedor: FornecedorCriar,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(requer_gestor),
):
    resultado = await db.execute(select(Fornecedor).where(Fornecedor.id == fornecedor_id))
    db_fornecedor = resultado.scalar_one_or_none()
    if not db_fornecedor:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")

    for campo, valor in fornecedor.model_dump(exclude_unset=True).items():
        setattr(db_fornecedor, campo, valor)
    db.add(db_fornecedor)
    await db.flush()
    await registrar_audit(db, usuario, AcaoAudit.atualizar, "fornecedor", db_fornecedor.id)
    return db_fornecedor


@router.delete("/{fornecedor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_fornecedor(
    fornecedor_id: str,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(requer_gestor),
):
    resultado = await db.execute(select(Fornecedor).where(Fornecedor.id == fornecedor_id))
    db_fornecedor = resultado.scalar_one_or_none()
    if not db_fornecedor:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")

    db_fornecedor.ativo = False
    db.add(db_fornecedor)
    await registrar_audit(db, usuario, AcaoAudit.deletar, "fornecedor", db_fornecedor.id)
