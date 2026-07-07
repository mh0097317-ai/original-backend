# routers/contas.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Conta, Filial, Usuario, AcaoAudit
from schemas import ContaCriar, ContaAtualizar, ContaOut, Pagina
from security import get_usuario_atual, requer_gestor, registrar_audit, filial_permitida

router = APIRouter(prefix="/api/contas", tags=["Contas"])


@router.post("", response_model=ContaOut, status_code=status.HTTP_201_CREATED)
async def criar_conta(
    conta: ContaCriar,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(requer_gestor),
):
    filial = await db.execute(select(Filial).where(Filial.id == conta.filial_id))
    if not filial.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Filial não encontrada")
    if not filial_permitida(usuario, conta.filial_id):
        raise HTTPException(status_code=403, detail="Sem acesso a esta filial")

    nova = Conta(**conta.model_dump())
    nova.saldo_atual = nova.saldo_inicial
    db.add(nova)
    await db.flush()
    await registrar_audit(db, usuario, AcaoAudit.criar, "conta", nova.id,
                          {"nome": nova.nome, "saldo_inicial": nova.saldo_inicial})
    return nova


@router.get("", response_model=Pagina[ContaOut])
async def listar_contas(
    filial_id: str | None = None,
    ativa: bool = True,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    limit = min(limit, 200)
    cond = []
    if ativa is not None:
        cond.append(Conta.ativa == ativa)
    # visualizador/gestor só enxergam a própria filial
    if usuario.filial_id and usuario.role.value != "admin":
        cond.append(Conta.filial_id == usuario.filial_id)
    elif filial_id:
        cond.append(Conta.filial_id == filial_id)

    total = await db.execute(select(func.count(Conta.id)).where(*cond))
    result = await db.execute(select(Conta).where(*cond).offset(skip).limit(limit))
    return Pagina(total=total.scalar() or 0, skip=skip, limit=limit,
                  items=list(result.scalars().all()))


@router.get("/{conta_id}", response_model=ContaOut)
async def obter_conta(
    conta_id: str,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    conta = await db.execute(select(Conta).where(Conta.id == conta_id))
    db_conta = conta.scalar_one_or_none()
    if not db_conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    if not filial_permitida(usuario, db_conta.filial_id):
        raise HTTPException(status_code=403, detail="Sem acesso a esta conta")
    return db_conta


@router.put("/{conta_id}", response_model=ContaOut)
async def atualizar_conta(
    conta_id: str,
    conta: ContaAtualizar,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(requer_gestor),
):
    resultado = await db.execute(select(Conta).where(Conta.id == conta_id))
    db_conta = resultado.scalar_one_or_none()
    if not db_conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    if not filial_permitida(usuario, db_conta.filial_id):
        raise HTTPException(status_code=403, detail="Sem acesso a esta conta")

    for campo, valor in conta.model_dump(exclude_unset=True).items():
        setattr(db_conta, campo, valor)
    db.add(db_conta)
    await db.flush()
    await registrar_audit(db, usuario, AcaoAudit.atualizar, "conta", db_conta.id)
    return db_conta


@router.delete("/{conta_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_conta(
    conta_id: str,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(requer_gestor),
):
    resultado = await db.execute(select(Conta).where(Conta.id == conta_id))
    db_conta = resultado.scalar_one_or_none()
    if not db_conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    if not filial_permitida(usuario, db_conta.filial_id):
        raise HTTPException(status_code=403, detail="Sem acesso a esta conta")

    db_conta.ativa = False
    db.add(db_conta)
    await registrar_audit(db, usuario, AcaoAudit.deletar, "conta", db_conta.id)
