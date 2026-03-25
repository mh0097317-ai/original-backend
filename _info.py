# ============================================================
# ORIGINAL ALUGUEL DE CARROS — Backend FastAPI + PostgreSQL
# ============================================================
# Estrutura de arquivos:
#
# original_backend/
# ├── main.py              ← ponto de entrada
# ├── database.py          ← conexão com PostgreSQL
# ├── models.py            ← tabelas (SQLAlchemy)
# ├── schemas.py           ← validação (Pydantic)
# ├── routers/
# │   ├── auth.py
# │   ├── veiculos.py
# │   ├── reservas.py
# │   ├── gps.py
# │   ├── avaliacoes.py
# │   ├── notificacoes.py
# │   └── promocoes.py
# ├── requirements.txt
# └── .env
# ============================================================


# ────────────────────────────────────────────────────────────
# requirements.txt
# ────────────────────────────────────────────────────────────
REQUIREMENTS = """
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy==2.0.30
asyncpg==0.29.0
alembic==1.13.1
pydantic[email]==2.7.1
pydantic-settings==2.2.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
python-dotenv==1.0.1
httpx==0.27.0
"""

# ────────────────────────────────────────────────────────────
# .env  (copie e preencha)
# ────────────────────────────────────────────────────────────
ENV_EXAMPLE = """
DATABASE_URL=postgresql+asyncpg://postgres:senha@localhost:5432/original_aluguel
SECRET_KEY=troque_por_uma_chave_secreta_longa_e_aleatoria
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
"""
