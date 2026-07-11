# main.py
from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from database import engine, AsyncSessionLocal, Base
from models import Filial, Conta, Movimento, Fornecedor, ContaPagar, ContaReceber
from models import TipoConta, TipoMovimento, CategoriaMovimento
from routers import (
    auth, filiais, contas, movimentos, fornecedores,
    contas_pagar, contas_receber, relatorios, auditoria, conciliacao, chat,
)


# ── Seed: dados iniciais ───────────────────────────────────
async def seed_data():
    async with AsyncSessionLocal() as db:
        # Filiais
        filiais_existentes = await db.execute(select(Filial))
        if not filiais_existentes.scalars().first():
            filiais = [
                Filial(
                    nome="Filial São Paulo",
                    cnpj="12.345.678/0001-90",
                    endereco="Avenida Paulista, 1000",
                    cidade="São Paulo",
                    estado="SP",
                    telefone="(11) 3000-0000",
                    email="sp@distribuidora.com"
                ),
                Filial(
                    nome="Filial Rio de Janeiro",
                    cnpj="12.345.678/0001-91",
                    endereco="Avenida Atlântica, 500",
                    cidade="Rio de Janeiro",
                    estado="RJ",
                    telefone="(21) 3000-0000",
                    email="rj@distribuidora.com"
                ),
            ]
            db.add_all(filiais)
            await db.flush()

            # Contas
            contas = []
            for filial in filiais:
                contas.extend([
                    Conta(
                        filial_id=filial.id,
                        nome=f"Caixa {filial.nome}",
                        tipo=TipoConta.caixa,
                        saldo_inicial=Decimal("10000.00"),
                        saldo_atual=Decimal("10000.00")
                    ),
                    Conta(
                        filial_id=filial.id,
                        nome=f"Banco do Brasil - {filial.nome}",
                        tipo=TipoConta.banco,
                        numero_conta="12345-6",
                        banco="Banco do Brasil",
                        saldo_inicial=Decimal("50000.00"),
                        saldo_atual=Decimal("50000.00")
                    ),
                ])
            db.add_all(contas)

            # Fornecedores
            fornecedores = [
                Fornecedor(
                    nome="Fornecedor ABC Ltda",
                    cnpj="98.765.432/0001-10",
                    contato="João Silva",
                    email="contato@fornecedorabc.com",
                    telefone="(11) 9999-9999"
                ),
                Fornecedor(
                    nome="Distribuidor XYZ S.A.",
                    cnpj="98.765.432/0001-11",
                    contato="Maria Santos",
                    email="contato@xyzltda.com",
                    telefone="(21) 9999-9999"
                ),
            ]
            db.add_all(fornecedores)

            await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_data()
    print("✅ Sistema de Fluxo de Caixa inicializado!")
    yield
    await engine.dispose()


# ── App ────────────────────────────────────────────────────
app = FastAPI(
    title="Sistema de Fluxo de Caixa — API",
    description="Backend robusto para gestão de fluxo de caixa de distribuidora",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(auth.router)
app.include_router(filiais.router)
app.include_router(contas.router)
app.include_router(movimentos.router)
app.include_router(fornecedores.router)
app.include_router(contas_pagar.router)
app.include_router(contas_receber.router)
app.include_router(relatorios.router)
app.include_router(auditoria.router)
app.include_router(conciliacao.router)
app.include_router(chat.router)


@app.get("/", tags=["Status"])
async def root():
    return {
        "status": "online",
        "app": "Sistema de Fluxo de Caixa — API",
        "versao": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Status"])
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
