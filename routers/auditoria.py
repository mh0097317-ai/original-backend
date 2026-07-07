# routers/auditoria.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import AuditLog, Usuario, AcaoAudit
from schemas import AuditLogOut, Pagina
from security import requer_admin

router = APIRouter(prefix="/api/auditoria", tags=["Auditoria"])


@router.get("", response_model=Pagina[AuditLogOut])
async def listar_auditoria(
    entidade: str | None = None,
    entidade_id: str | None = None,
    usuario_id: str | None = None,
    acao: AcaoAudit | None = None,
    skip: int = 0,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    admin: Usuario = Depends(requer_admin),
):
    cond = []
    if entidade:
        cond.append(AuditLog.entidade == entidade)
    if entidade_id:
        cond.append(AuditLog.entidade_id == entidade_id)
    if usuario_id:
        cond.append(AuditLog.usuario_id == usuario_id)
    if acao:
        cond.append(AuditLog.acao == acao)

    total = await db.execute(select(func.count(AuditLog.id)).where(*cond))
    result = await db.execute(
        select(AuditLog).where(*cond)
        .order_by(AuditLog.criado_em.desc()).offset(skip).limit(limit)
    )
    return Pagina(total=total.scalar() or 0, skip=skip, limit=limit,
                  items=list(result.scalars().all()))
