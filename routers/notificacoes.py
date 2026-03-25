# routers/notificacoes.py
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from database import get_db
from models import Notificacao, Usuario
from schemas import NotificacaoOut, Mensagem
from routers.auth import get_usuario_atual

router = APIRouter(prefix="/notificacoes", tags=["Notificações"])


@router.get("/", response_model=List[NotificacaoOut])
async def listar(
    apenas_nao_lidas: bool = False,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Notificacao)
        .where(Notificacao.usuario_id == usuario.id)
        .order_by(Notificacao.criado_em.desc())
        .limit(50)
    )
    if apenas_nao_lidas:
        query = query.where(Notificacao.lida == False)

    result = await db.execute(query)
    return [NotificacaoOut.model_validate(n) for n in result.scalars().all()]


@router.get("/nao-lidas/count")
async def contar_nao_lidas(
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notificacao).where(
            Notificacao.usuario_id == usuario.id,
            Notificacao.lida == False,
        )
    )
    return {"count": len(result.scalars().all())}


@router.patch("/{notif_id}/lida", response_model=Mensagem)
async def marcar_lida(
    notif_id: str,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(Notificacao)
        .where(Notificacao.id == notif_id, Notificacao.usuario_id == usuario.id)
        .values(lida=True)
    )
    return Mensagem(mensagem="Notificação marcada como lida")


@router.patch("/todas/lidas", response_model=Mensagem)
async def marcar_todas_lidas(
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(Notificacao)
        .where(Notificacao.usuario_id == usuario.id, Notificacao.lida == False)
        .values(lida=True)
    )
    return Mensagem(mensagem="Todas as notificações marcadas como lidas")
