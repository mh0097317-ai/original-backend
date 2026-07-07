# routers/movimentos.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from database import get_db
from models import (
    Movimento, Conta, Usuario, AcaoAudit,
    StatusMovimento, TipoMovimento, CategoriaMovimento,
)
from schemas import MovimentoCriar, MovimentoOut, Pagina
from security import get_usuario_atual, requer_gestor, registrar_audit, filial_permitida

router = APIRouter(prefix="/api/movimentos", tags=["Movimentos"])


def _aplicar_no_saldo(conta: Conta, mov: Movimento, reverter: bool = False):
    """Aplica (ou reverte) o impacto do movimento no saldo da conta."""
    sinal = -1 if reverter else 1
    if mov.tipo == TipoMovimento.entrada:
        conta.saldo_atual = conta.saldo_atual + sinal * mov.valor
    else:
        conta.saldo_atual = conta.saldo_atual - sinal * mov.valor


@router.post("", response_model=MovimentoOut, status_code=status.HTTP_201_CREATED)
async def criar_movimento(
    movimento: MovimentoCriar,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(requer_gestor),
):
    conta = await db.execute(select(Conta).where(Conta.id == movimento.conta_id))
    db_conta = conta.scalar_one_or_none()
    if not db_conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    if not db_conta.ativa:
        raise HTTPException(status_code=400, detail="Conta inativa")
    if not filial_permitida(usuario, db_conta.filial_id):
        raise HTTPException(status_code=403, detail="Sem acesso a esta conta")

    novo = Movimento(
        **movimento.model_dump(),
        filial_id=db_conta.filial_id,
        status=StatusMovimento.confirmado,
        criado_por=usuario.id,
    )

    if novo.tipo == TipoMovimento.saida and db_conta.saldo_atual < novo.valor:
        raise HTTPException(status_code=400, detail="Saldo insuficiente na conta")

    db.add(novo)
    _aplicar_no_saldo(db_conta, novo)
    db.add(db_conta)
    await db.flush()
    await registrar_audit(db, usuario, AcaoAudit.criar, "movimento", novo.id,
                          {"tipo": novo.tipo.value, "valor": novo.valor,
                           "conta_id": novo.conta_id})
    return novo


@router.get("", response_model=Pagina[MovimentoOut])
async def listar_movimentos(
    filial_id: str | None = None,
    conta_id: str | None = None,
    categoria: CategoriaMovimento | None = None,
    tipo: TipoMovimento | None = None,
    movstatus: StatusMovimento | None = None,
    data_inicio: datetime | None = None,
    data_fim: datetime | None = None,
    skip: int = 0,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    cond = []
    # escopo de filial para não-admin
    if usuario.filial_id and usuario.role.value != "admin":
        cond.append(Movimento.filial_id == usuario.filial_id)
    elif filial_id:
        cond.append(Movimento.filial_id == filial_id)
    if conta_id:
        cond.append(Movimento.conta_id == conta_id)
    if categoria:
        cond.append(Movimento.categoria == categoria)
    if tipo:
        cond.append(Movimento.tipo == tipo)
    if movstatus:
        cond.append(Movimento.status == movstatus)
    if data_inicio:
        cond.append(Movimento.data_movimento >= data_inicio)
    if data_fim:
        cond.append(Movimento.data_movimento <= data_fim)

    total = await db.execute(select(func.count(Movimento.id)).where(*cond))
    result = await db.execute(
        select(Movimento).where(*cond)
        .order_by(Movimento.data_movimento.desc())
        .offset(skip).limit(limit)
    )
    return Pagina(total=total.scalar() or 0, skip=skip, limit=limit,
                  items=list(result.scalars().all()))


@router.get("/{movimento_id}", response_model=MovimentoOut)
async def obter_movimento(
    movimento_id: str,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    movimento = await db.execute(select(Movimento).where(Movimento.id == movimento_id))
    db_mov = movimento.scalar_one_or_none()
    if not db_mov:
        raise HTTPException(status_code=404, detail="Movimento não encontrado")
    if not filial_permitida(usuario, db_mov.filial_id):
        raise HTTPException(status_code=403, detail="Sem acesso a este movimento")
    return db_mov


@router.delete("/{movimento_id}", status_code=status.HTTP_200_OK, response_model=MovimentoOut)
async def cancelar_movimento(
    movimento_id: str,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(requer_gestor),
):
    """Cancela um movimento e reverte seu impacto no saldo da conta (atômico)."""
    resultado = await db.execute(select(Movimento).where(Movimento.id == movimento_id))
    db_mov = resultado.scalar_one_or_none()
    if not db_mov:
        raise HTTPException(status_code=404, detail="Movimento não encontrado")
    if not filial_permitida(usuario, db_mov.filial_id):
        raise HTTPException(status_code=403, detail="Sem acesso a este movimento")
    if db_mov.status == StatusMovimento.cancelado:
        raise HTTPException(status_code=400, detail="Movimento já cancelado")

    conta = await db.execute(select(Conta).where(Conta.id == db_mov.conta_id))
    db_conta = conta.scalar_one_or_none()

    _aplicar_no_saldo(db_conta, db_mov, reverter=True)
    db_mov.status = StatusMovimento.cancelado
    db.add_all([db_mov, db_conta])
    await db.flush()
    await registrar_audit(db, usuario, AcaoAudit.cancelar, "movimento", db_mov.id,
                          {"valor": db_mov.valor})
    return db_mov
