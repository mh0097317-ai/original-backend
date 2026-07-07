# security.py
"""Autenticação JWT, hashing de senha e controle de acesso por papel (RBAC)."""
import json
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, settings
from models import Usuario, RoleEnum, AuditLog, AcaoAudit

# pbkdf2_sha256 como padrão (puro Python, sem dependências nativas frágeis);
# bcrypt permanece suportado para verificar hashes legados.
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def hash_senha(senha: str) -> str:
    return pwd_context.hash(senha)


def verificar_senha(senha: str, hash_: str) -> bool:
    return pwd_context.verify(senha, hash_)


def criar_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    payload = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload.update({"exp": expire})
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_usuario_atual(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(Usuario).where(Usuario.id == user_id))
    usuario = result.scalar_one_or_none()
    if usuario is None or not usuario.ativo:
        raise credentials_exception
    return usuario


def requer_roles(*roles: RoleEnum):
    """Dependência que exige que o usuário tenha um dos papéis informados."""
    async def _verificar(usuario: Usuario = Depends(get_usuario_atual)) -> Usuario:
        if usuario.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão insuficiente para esta operação",
            )
        return usuario
    return _verificar


# Atalhos de papel comuns
requer_gestor = requer_roles(RoleEnum.admin, RoleEnum.gestor)
requer_admin = requer_roles(RoleEnum.admin)


def filial_permitida(usuario: Usuario, filial_id: Optional[str]) -> bool:
    """Admin acessa qualquer filial; demais só a própria."""
    if usuario.role == RoleEnum.admin:
        return True
    return usuario.filial_id is not None and usuario.filial_id == filial_id


async def registrar_audit(
    db: AsyncSession,
    usuario: Optional[Usuario],
    acao: AcaoAudit,
    entidade: str,
    entidade_id: Optional[str] = None,
    detalhes: Optional[dict] = None,
) -> None:
    """Cria um registro de auditoria na mesma transação da operação."""
    log = AuditLog(
        usuario_id=usuario.id if usuario else None,
        usuario_nome=usuario.nome if usuario else None,
        acao=acao,
        entidade=entidade,
        entidade_id=entidade_id,
        detalhes=json.dumps(detalhes, default=str, ensure_ascii=False) if detalhes else None,
    )
    db.add(log)
