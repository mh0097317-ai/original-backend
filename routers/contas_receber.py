# routers/contas_receber.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from database import get_db
from models import ContaReceber, Usuario, AcaoAudit
from schemas import ContaReceberCriar, ContaReceberOut, Pagina
from security import get_usuario_atual, requer_gestor, registrar_audit

router = APIRouter(prefix="/api/contas-receber", tags=["Contas a Receber"])


@router.post("", response_model=ContaReceberOut, status_code=status.HTTP_201_CREATED)
async def criar_conta_receber(
    conta: ContaReceberCriar,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(requer_gestor),
):
    nova = ContaReceber(**conta.model_dump(), criado_por=usuario.id)
    db.add(nova)
    await db.flush()
    await registrar_audit(db, usuario, AcaoAudit.criar, "conta_receber", nova.id,
                          {"valor": nova.valor, "cliente": nova.cliente_nome})
    return nova


@router.get("", response_model=Pagina[ContaReceberOut])
async def listar_contas_receber(
    cliente_nome: str | None = None,
    recebido: bool | None = None,
    vencidas: bool = False,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    limit = min(limit, 200)
    cond = []
    if cliente_nome:
        cond.append(ContaReceber.cliente_nome.ilike(f"%{cliente_nome}%"))
    if recebido is not None:
        cond.append(ContaReceber.recebido == recebido)
    if vencidas:
        cond.append(ContaReceber.data_vencimento < datetime.utcnow())
        cond.append(ContaReceber.recebido == False)  # noqa: E712

    total = await db.execute(select(func.count(ContaReceber.id)).where(*cond))
    result = await db.execute(
        select(ContaReceber).where(*cond)
        .order_by(ContaReceber.data_vencimento).offset(skip).limit(limit)
    )
    return Pagina(total=total.scalar() or 0, skip=skip, limit=limit,
                  items=list(result.scalars().all()))


@router.get("/{conta_id}", response_model=ContaReceberOut)
async def obter_conta_receber(
    conta_id: str,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    conta = await db.execute(select(ContaReceber).where(ContaReceber.id == conta_id))
    db_conta = conta.scalar_one_or_none()
    if not db_conta:
        raise HTTPException(status_code=404, detail="Conta a receber não encontrada")
    return db_conta


@router.post("/{conta_id}/receber", response_model=ContaReceberOut)
async def receber_conta(
    conta_id: str,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(requer_gestor),
):
    resultado = await db.execute(select(ContaReceber).where(ContaReceber.id == conta_id))
    db_conta = resultado.scalar_one_or_none()
    if not db_conta:
        raise HTTPException(status_code=404, detail="Conta a receber não encontrada")
    if db_conta.recebido:
        raise HTTPException(status_code=400, detail="Conta já foi recebida")

    db_conta.recebido = True
    db_conta.data_recebimento = datetime.utcnow()
    db.add(db_conta)
    await db.flush()
    await registrar_audit(db, usuario, AcaoAudit.receber, "conta_receber", db_conta.id,
                          {"valor": db_conta.valor})
    return db_conta


@router.put("/{conta_id}", response_model=ContaReceberOut)
async def atualizar_conta_receber(
    conta_id: str,
    conta: ContaReceberCriar,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(requer_gestor),
):
    resultado = await db.execute(select(ContaReceber).where(ContaReceber.id == conta_id))
    db_conta = resultado.scalar_one_or_none()
    if not db_conta:
        raise HTTPException(status_code=404, detail="Conta a receber não encontrada")
    if db_conta.recebido:
        raise HTTPException(status_code=400, detail="Não é possível atualizar conta já recebida")

    for campo, valor in conta.model_dump(exclude_unset=True).items():
        setattr(db_conta, campo, valor)
    db.add(db_conta)
    await db.flush()
    await registrar_audit(db, usuario, AcaoAudit.atualizar, "conta_receber", db_conta.id)
    return db_conta


@router.delete("/{conta_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_conta_receber(
    conta_id: str,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(requer_gestor),
):
    resultado = await db.execute(select(ContaReceber).where(ContaReceber.id == conta_id))
    db_conta = resultado.scalar_one_or_none()
    if not db_conta:
        raise HTTPException(status_code=404, detail="Conta a receber não encontrada")
    if db_conta.recebido:
        raise HTTPException(status_code=400, detail="Não é possível deletar conta já recebida")

    await registrar_audit(db, usuario, AcaoAudit.deletar, "conta_receber", db_conta.id)
    await db.delete(db_conta)
