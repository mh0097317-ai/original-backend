# routers/contas_pagar.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from database import get_db
from models import ContaPagar, Fornecedor, Usuario, AcaoAudit
from schemas import ContaPagarCriar, ContaPagarOut, Pagina
from security import get_usuario_atual, requer_gestor, registrar_audit

router = APIRouter(prefix="/api/contas-pagar", tags=["Contas a Pagar"])


@router.post("", response_model=ContaPagarOut, status_code=status.HTTP_201_CREATED)
async def criar_conta_pagar(
    conta: ContaPagarCriar,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(requer_gestor),
):
    fornecedor = await db.execute(select(Fornecedor).where(Fornecedor.id == conta.fornecedor_id))
    if not fornecedor.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")

    nova = ContaPagar(**conta.model_dump(), criado_por=usuario.id)
    db.add(nova)
    await db.flush()
    await registrar_audit(db, usuario, AcaoAudit.criar, "conta_pagar", nova.id,
                          {"valor": nova.valor, "documento": nova.numero_documento})
    return nova


@router.get("", response_model=Pagina[ContaPagarOut])
async def listar_contas_pagar(
    fornecedor_id: str | None = None,
    pago: bool | None = None,
    vencidas: bool = False,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    limit = min(limit, 200)
    cond = []
    if fornecedor_id:
        cond.append(ContaPagar.fornecedor_id == fornecedor_id)
    if pago is not None:
        cond.append(ContaPagar.pago == pago)
    if vencidas:
        cond.append(ContaPagar.data_vencimento < datetime.utcnow())
        cond.append(ContaPagar.pago == False)  # noqa: E712

    total = await db.execute(select(func.count(ContaPagar.id)).where(*cond))
    result = await db.execute(
        select(ContaPagar).where(*cond)
        .order_by(ContaPagar.data_vencimento).offset(skip).limit(limit)
    )
    return Pagina(total=total.scalar() or 0, skip=skip, limit=limit,
                  items=list(result.scalars().all()))


@router.get("/{conta_id}", response_model=ContaPagarOut)
async def obter_conta_pagar(
    conta_id: str,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    conta = await db.execute(select(ContaPagar).where(ContaPagar.id == conta_id))
    db_conta = conta.scalar_one_or_none()
    if not db_conta:
        raise HTTPException(status_code=404, detail="Conta a pagar não encontrada")
    return db_conta


@router.post("/{conta_id}/pagar", response_model=ContaPagarOut)
async def pagar_conta(
    conta_id: str,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(requer_gestor),
):
    resultado = await db.execute(select(ContaPagar).where(ContaPagar.id == conta_id))
    db_conta = resultado.scalar_one_or_none()
    if not db_conta:
        raise HTTPException(status_code=404, detail="Conta a pagar não encontrada")
    if db_conta.pago:
        raise HTTPException(status_code=400, detail="Conta já foi paga")

    db_conta.pago = True
    db_conta.data_pagamento = datetime.utcnow()
    db.add(db_conta)
    await db.flush()
    await registrar_audit(db, usuario, AcaoAudit.pagar, "conta_pagar", db_conta.id,
                          {"valor": db_conta.valor})
    return db_conta


@router.put("/{conta_id}", response_model=ContaPagarOut)
async def atualizar_conta_pagar(
    conta_id: str,
    conta: ContaPagarCriar,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(requer_gestor),
):
    resultado = await db.execute(select(ContaPagar).where(ContaPagar.id == conta_id))
    db_conta = resultado.scalar_one_or_none()
    if not db_conta:
        raise HTTPException(status_code=404, detail="Conta a pagar não encontrada")
    if db_conta.pago:
        raise HTTPException(status_code=400, detail="Não é possível atualizar conta já paga")

    for campo, valor in conta.model_dump(exclude_unset=True).items():
        setattr(db_conta, campo, valor)
    db.add(db_conta)
    await db.flush()
    await registrar_audit(db, usuario, AcaoAudit.atualizar, "conta_pagar", db_conta.id)
    return db_conta


@router.delete("/{conta_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_conta_pagar(
    conta_id: str,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(requer_gestor),
):
    resultado = await db.execute(select(ContaPagar).where(ContaPagar.id == conta_id))
    db_conta = resultado.scalar_one_or_none()
    if not db_conta:
        raise HTTPException(status_code=404, detail="Conta a pagar não encontrada")
    if db_conta.pago:
        raise HTTPException(status_code=400, detail="Não é possível deletar conta já paga")

    await registrar_audit(db, usuario, AcaoAudit.deletar, "conta_pagar", db_conta.id)
    await db.delete(db_conta)
