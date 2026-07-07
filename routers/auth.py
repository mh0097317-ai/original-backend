# routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Usuario, Filial, RoleEnum, AcaoAudit
from schemas import UsuarioCadastro, UsuarioLogin, UsuarioOut, Token, TrocarSenha, Mensagem, Pagina
from security import (
    hash_senha, verificar_senha, criar_token,
    get_usuario_atual, requer_admin, registrar_audit,
)

router = APIRouter(prefix="/api/auth", tags=["Autenticação"])


async def _validar_filial(db: AsyncSession, filial_id: str):
    filial = await db.execute(select(Filial).where(Filial.id == filial_id))
    if not filial.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Filial não encontrada")


@router.post("/cadastro", response_model=Token, status_code=status.HTTP_201_CREATED)
async def cadastrar(dados: UsuarioCadastro, db: AsyncSession = Depends(get_db)):
    """Cria um usuário.

    O primeiro usuário do sistema é criado como admin sem autenticação
    (bootstrap). A partir daí, somente admins podem cadastrar usuários —
    use POST /api/auth/usuarios.
    """
    total = await db.execute(select(func.count(Usuario.id)))
    primeiro_usuario = (total.scalar() or 0) == 0

    if not primeiro_usuario:
        raise HTTPException(
            status_code=403,
            detail="Sistema já inicializado. Apenas admins cadastram novos usuários (POST /api/auth/usuarios).",
        )

    existe = await db.execute(select(Usuario).where(Usuario.email == dados.email))
    if existe.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        senha_hash=hash_senha(dados.senha),
        role=RoleEnum.admin,  # bootstrap → admin
        filial_id=None,
    )
    db.add(usuario)
    await db.flush()
    await registrar_audit(db, usuario, AcaoAudit.criar, "usuario", usuario.id,
                          {"email": usuario.email, "role": usuario.role.value})
    return Token(access_token=criar_token({"sub": usuario.id}),
                 usuario=UsuarioOut.model_validate(usuario))


@router.post("/usuarios", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
async def criar_usuario(
    dados: UsuarioCadastro,
    db: AsyncSession = Depends(get_db),
    admin: Usuario = Depends(requer_admin),
):
    existe = await db.execute(select(Usuario).where(Usuario.email == dados.email))
    if existe.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    if dados.role != RoleEnum.admin:
        if not dados.filial_id:
            raise HTTPException(status_code=400, detail="Gestor/visualizador exige filial_id")
        await _validar_filial(db, dados.filial_id)

    usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        senha_hash=hash_senha(dados.senha),
        role=dados.role,
        filial_id=dados.filial_id if dados.role != RoleEnum.admin else None,
    )
    db.add(usuario)
    await db.flush()
    await registrar_audit(db, admin, AcaoAudit.criar, "usuario", usuario.id,
                          {"email": usuario.email, "role": usuario.role.value})
    return usuario


@router.get("/usuarios", response_model=Pagina[UsuarioOut])
async def listar_usuarios(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    admin: Usuario = Depends(requer_admin),
):
    limit = min(limit, 200)
    total = await db.execute(select(func.count(Usuario.id)))
    result = await db.execute(select(Usuario).offset(skip).limit(limit))
    return Pagina(total=total.scalar() or 0, skip=skip, limit=limit,
                  items=list(result.scalars().all()))


@router.post("/login", response_model=Token)
async def login(dados: UsuarioLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Usuario).where(Usuario.email == dados.email))
    usuario = result.scalar_one_or_none()
    if not usuario or not verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")
    if not usuario.ativo:
        raise HTTPException(status_code=403, detail="Conta desativada")

    await registrar_audit(db, usuario, AcaoAudit.login, "usuario", usuario.id)
    return Token(access_token=criar_token({"sub": usuario.id}),
                 usuario=UsuarioOut.model_validate(usuario))


@router.post("/token", response_model=Token)
async def login_oauth(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Endpoint OAuth2 (form) para o botão Authorize do Swagger. username = e-mail."""
    result = await db.execute(select(Usuario).where(Usuario.email == form.username))
    usuario = result.scalar_one_or_none()
    if not usuario or not verificar_senha(form.password, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")
    if not usuario.ativo:
        raise HTTPException(status_code=403, detail="Conta desativada")
    return Token(access_token=criar_token({"sub": usuario.id}),
                 usuario=UsuarioOut.model_validate(usuario))


@router.get("/me", response_model=UsuarioOut)
async def meu_perfil(usuario: Usuario = Depends(get_usuario_atual)):
    return usuario


@router.post("/trocar-senha", response_model=Mensagem)
async def trocar_senha(
    dados: TrocarSenha,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    if not verificar_senha(dados.senha_atual, usuario.senha_hash):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    usuario.senha_hash = hash_senha(dados.nova_senha)
    db.add(usuario)
    return Mensagem(mensagem="Senha alterada com sucesso")
