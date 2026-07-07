# routers/filiais.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Filial, Usuario, AcaoAudit
from schemas import FilialCriar, FilialOut, Pagina
from security import get_usuario_atual, requer_admin, registrar_audit

router = APIRouter(prefix="/api/filiais", tags=["Filiais"])


@router.post("", response_model=FilialOut, status_code=status.HTTP_201_CREATED)
async def criar_filial(
    filial: FilialCriar,
    db: AsyncSession = Depends(get_db),
    admin: Usuario = Depends(requer_admin),
):
    existe = await db.execute(select(Filial).where(Filial.cnpj == filial.cnpj))
    if existe.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="CNPJ já registrado")

    nova = Filial(**filial.model_dump())
    db.add(nova)
    await db.flush()
    await registrar_audit(db, admin, AcaoAudit.criar, "filial", nova.id, {"nome": nova.nome})
    return nova


@router.get("", response_model=Pagina[FilialOut])
async def listar_filiais(
    ativa: bool = True,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    limit = min(limit, 200)
    cond = [Filial.ativa == ativa] if ativa is not None else []
    total = await db.execute(select(func.count(Filial.id)).where(*cond))
    result = await db.execute(select(Filial).where(*cond).offset(skip).limit(limit))
    return Pagina(total=total.scalar() or 0, skip=skip, limit=limit,
                  items=list(result.scalars().all()))


@router.get("/{filial_id}", response_model=FilialOut)
async def obter_filial(
    filial_id: str,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    filial = await db.execute(select(Filial).where(Filial.id == filial_id))
    db_filial = filial.scalar_one_or_none()
    if not db_filial:
        raise HTTPException(status_code=404, detail="Filial não encontrada")
    return db_filial


@router.put("/{filial_id}", response_model=FilialOut)
async def atualizar_filial(
    filial_id: str,
    filial: FilialCriar,
    db: AsyncSession = Depends(get_db),
    admin: Usuario = Depends(requer_admin),
):
    resultado = await db.execute(select(Filial).where(Filial.id == filial_id))
    db_filial = resultado.scalar_one_or_none()
    if not db_filial:
        raise HTTPException(status_code=404, detail="Filial não encontrada")

    for campo, valor in filial.model_dump(exclude_unset=True).items():
        setattr(db_filial, campo, valor)
    db.add(db_filial)
    await db.flush()
    await registrar_audit(db, admin, AcaoAudit.atualizar, "filial", db_filial.id)
    return db_filial


@router.delete("/{filial_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_filial(
    filial_id: str,
    db: AsyncSession = Depends(get_db),
    admin: Usuario = Depends(requer_admin),
):
    resultado = await db.execute(select(Filial).where(Filial.id == filial_id))
    db_filial = resultado.scalar_one_or_none()
    if not db_filial:
        raise HTTPException(status_code=404, detail="Filial não encontrada")

    db_filial.ativa = False
    db.add(db_filial)
    await registrar_audit(db, admin, AcaoAudit.deletar, "filial", db_filial.id)
