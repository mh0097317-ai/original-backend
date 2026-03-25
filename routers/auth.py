# routers/auth.py
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db, settings
from models import Usuario
from schemas import UsuarioCadastro, UsuarioLogin, UsuarioOut, UsuarioAtualizar, Token, Mensagem

router = APIRouter(prefix="/auth", tags=["Autenticação"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_senha(senha: str) -> str:
    return pwd_context.hash(senha)


def verificar_senha(senha: str, hash: str) -> bool:
    return pwd_context.verify(senha, hash)


def criar_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    payload = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
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


# ── Endpoints ──────────────────────────────────────────────

@router.post("/cadastro", response_model=Token, status_code=201)
async def cadastrar(dados: UsuarioCadastro, db: AsyncSession = Depends(get_db)):
    # Verifica e-mail duplicado
    result = await db.execute(select(Usuario).where(Usuario.email == dados.email))
    if result.scalar_one_or_none():
        raise HTTPException(400, "E-mail já cadastrado")

    usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        senha_hash=hash_senha(dados.senha),
        telefone=dados.telefone,
        cnh=dados.cnh,
        plano=dados.plano,
    )
    db.add(usuario)
    await db.flush()

    token = criar_token({"sub": usuario.id})
    return Token(access_token=token, usuario=UsuarioOut.model_validate(usuario))


@router.post("/login", response_model=Token)
async def login(dados: UsuarioLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Usuario).where(Usuario.email == dados.email))
    usuario = result.scalar_one_or_none()

    if not usuario or not verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(401, "E-mail ou senha incorretos")

    if not usuario.ativo:
        raise HTTPException(403, "Conta desativada")

    token = criar_token({"sub": usuario.id})
    return Token(access_token=token, usuario=UsuarioOut.model_validate(usuario))


@router.get("/me", response_model=UsuarioOut)
async def meu_perfil(usuario: Usuario = Depends(get_usuario_atual)):
    return UsuarioOut.model_validate(usuario)


@router.patch("/me", response_model=UsuarioOut)
async def atualizar_perfil(
    dados: UsuarioAtualizar,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    for campo, valor in dados.model_dump(exclude_none=True).items():
        setattr(usuario, campo, valor)
    usuario.atualizado_em = datetime.utcnow()
    await db.flush()
    return UsuarioOut.model_validate(usuario)


@router.post("/trocar-senha", response_model=Mensagem)
async def trocar_senha(
    senha_atual: str,
    nova_senha: str,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    if not verificar_senha(senha_atual, usuario.senha_hash):
        raise HTTPException(400, "Senha atual incorreta")
    usuario.senha_hash = hash_senha(nova_senha)
    await db.flush()
    return Mensagem(mensagem="Senha alterada com sucesso")
