# routers/chat.py
"""Chat interno da equipe — texto e mensagens de voz.

Sala única da empresa: todos os usuários autenticados (qualquer papel)
leem e enviam. Áudio trafega em base64 (m4a gravado no app).
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import MensagemChat, Usuario
from schemas import MensagemChatCriar, MensagemChatOut, Pagina
from security import get_usuario_atual

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("/mensagens", response_model=MensagemChatOut, status_code=status.HTTP_201_CREATED)
async def enviar_mensagem(
    dados: MensagemChatCriar,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    msg = MensagemChat(
        usuario_id=usuario.id,
        usuario_nome=usuario.nome,
        tipo=dados.tipo,
        conteudo=dados.conteudo,
        duracao_seg=dados.duracao_seg,
    )
    db.add(msg)
    await db.flush()
    return msg


@router.get("/mensagens", response_model=Pagina[MensagemChatOut])
async def listar_mensagens(
    skip: int = 0,
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Mensagens mais recentes primeiro (o app exibe em lista invertida)."""
    total = await db.execute(select(func.count(MensagemChat.id)))
    result = await db.execute(
        select(MensagemChat).order_by(MensagemChat.criado_em.desc())
        .offset(skip).limit(limit)
    )
    return Pagina(total=total.scalar() or 0, skip=skip, limit=limit,
                  items=list(result.scalars().all()))


@router.delete("/mensagens/{mensagem_id}", status_code=status.HTTP_204_NO_CONTENT)
async def apagar_mensagem(
    mensagem_id: str,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Autor apaga a própria mensagem; admin apaga qualquer uma."""
    msg = (await db.execute(
        select(MensagemChat).where(MensagemChat.id == mensagem_id)
    )).scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Mensagem não encontrada")
    if msg.usuario_id != usuario.id and usuario.role.value != "admin":
        raise HTTPException(status_code=403, detail="Só o autor ou admin pode apagar")
    await db.delete(msg)
