# main.py
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from database import engine, AsyncSessionLocal, Base
from models import Veiculo, Categoria, Promocao, CategoriaEnum
from routers import auth, veiculos, reservas, gps, avaliacoes, notificacoes, promocoes


# ── Seed: dados iniciais ───────────────────────────────────
async def seed_data():
    async with AsyncSessionLocal() as db:
        # Categorias
        cats_existentes = await db.execute(select(Categoria))
        if not cats_existentes.scalars().first():
            categorias = [
                Categoria(slug=CategoriaEnum.economy,  nome="Economy",   nome_en="Economy",  icone="🚗", descricao="Veículos econômicos"),
                Categoria(slug=CategoriaEnum.suv,      nome="SUV",       nome_en="SUV",      icone="🚙", descricao="Utilitários esportivos"),
                Categoria(slug=CategoriaEnum.luxo,     nome="Luxo",      nome_en="Luxury",   icone="🏎️", descricao="Veículos premium"),
                Categoria(slug=CategoriaEnum.sport,    nome="Esportivo", nome_en="Sport",    icone="🚀", descricao="Alta performance"),
                Categoria(slug=CategoriaEnum.eletrico, nome="Elétrico",  nome_en="Electric", icone="⚡", descricao="Frota elétrica"),
            ]
            db.add_all(categorias)

        # Veículos
        veic_existentes = await db.execute(select(Veiculo))
        if not veic_existentes.scalars().first():
            veiculos_seed = [
                Veiculo(nome="VW Gol",              marca="Volkswagen", modelo="Gol",           ano=2023, placa="ORI-0001", categoria=CategoriaEnum.economy,  preco_dia=89,  preco_semana=540,  preco_mes=1800, potencia_cv=116, combustivel="flex",     portas=4, lugares=5, cambio="manual"),
                Veiculo(nome="Toyota Corolla Cross", marca="Toyota",     modelo="Corolla Cross", ano=2024, placa="ORI-0002", categoria=CategoriaEnum.suv,      preco_dia=179, preco_semana=1100, preco_mes=3600, potencia_cv=182, combustivel="flex",     portas=4, lugares=5, cambio="automatico"),
                Veiculo(nome="BMW Série 3",          marca="BMW",        modelo="330i",          ano=2024, placa="ORI-0003", categoria=CategoriaEnum.luxo,     preco_dia=350, preco_semana=2100, preco_mes=7000, potencia_cv=258, combustivel="gasolina", portas=4, lugares=5, cambio="automatico"),
                Veiculo(nome="Ford Mustang GT",      marca="Ford",       modelo="Mustang GT",    ano=2023, placa="ORI-0004", categoria=CategoriaEnum.sport,    preco_dia=480, preco_semana=2800, preco_mes=9000, potencia_cv=450, combustivel="gasolina", portas=2, lugares=4, cambio="manual"),
                Veiculo(nome="Jeep Compass",         marca="Jeep",       modelo="Compass",       ano=2024, placa="ORI-0005", categoria=CategoriaEnum.suv,      preco_dia=195, preco_semana=1200, preco_mes=3900, potencia_cv=185, combustivel="flex",     portas=4, lugares=5, cambio="automatico"),
                Veiculo(nome="Tesla Model 3",        marca="Tesla",      modelo="Model 3",       ano=2024, placa="ORI-0006", categoria=CategoriaEnum.eletrico, preco_dia=320, preco_semana=1900, preco_mes=6200, potencia_cv=0,   combustivel="eletrico", portas=4, lugares=5, cambio="automatico"),
                Veiculo(nome="Toyota SW4",           marca="Toyota",     modelo="SW4",           ano=2023, placa="ORI-0007", categoria=CategoriaEnum.suv,      preco_dia=220, preco_semana=1350, preco_mes=4400, potencia_cv=190, combustivel="diesel",   portas=4, lugares=7, cambio="automatico"),
                Veiculo(nome="BMW 530i",             marca="BMW",        modelo="530i",          ano=2024, placa="ORI-0008", categoria=CategoriaEnum.luxo,     preco_dia=390, preco_semana=2300, preco_mes=7800, potencia_cv=252, combustivel="gasolina", portas=4, lugares=5, cambio="automatico"),
            ]
            db.add_all(veiculos_seed)

        # Promoções
        promo_existentes = await db.execute(select(Promocao))
        if not promo_existentes.scalars().first():
            promos = [
                Promocao(codigo="SUV30",    descricao="30% de desconto em todos os SUVs",        descricao_en="30% off all SUV rentals",       desconto_pct=30, categoria=CategoriaEnum.suv,      min_dias=1, valido_ate=datetime(2026, 12, 31), usos_maximos=500),
                Promocao(codigo="NEW2024",  descricao="Primeira semana grátis para novos usuários", descricao_en="First week free",             desconto_pct=100,categoria=None,                   min_dias=7, valido_ate=datetime(2026, 12, 31), usos_maximos=1000),
                Promocao(codigo="FERIAS25", descricao="25% off em aluguéis acima de 7 dias",     descricao_en="25% off rentals over 7 days",   desconto_pct=25, categoria=None,                   min_dias=7, valido_ate=datetime(2026, 12, 31), usos_maximos=300),
                Promocao(codigo="EV15",     descricao="15% em veículos elétricos",               descricao_en="15% off electric vehicles",      desconto_pct=15, categoria=CategoriaEnum.eletrico, min_dias=1, valido_ate=datetime(2099, 12, 31), usos_maximos=None),
            ]
            db.add_all(promos)

        await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Cria tabelas e insere dados de seed
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_data()
    print("✅ Banco de dados pronto!")
    yield
    await engine.dispose()


# ── App ────────────────────────────────────────────────────
app = FastAPI(
    title="Original Aluguel de Carros — API",
    description="Backend completo para o app de aluguel de veículos",
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

# Routers
app.include_router(auth.router)
app.include_router(veiculos.router)
app.include_router(reservas.router)
app.include_router(gps.router)
app.include_router(avaliacoes.router)
app.include_router(notificacoes.router)
app.include_router(promocoes.router)


@app.get("/", tags=["Status"])
async def root():
    return {
        "status": "online",
        "app": "Original Aluguel de Carros",
        "versao": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Status"])
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
