# db_types.py
"""Tipos de coluna portáveis entre PostgreSQL e SQLite.

Em produção o backend roda em PostgreSQL (asyncpg). Para que a suíte de
testes possa rodar em SQLite in-memory (sem subir um banco real), os IDs
usam um GUID que vira UUID nativo no Postgres e CHAR(36) nos demais.
"""
import uuid
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


class GUID(TypeDecorator):
    """UUID portável: UUID nativo no Postgres, CHAR(36) no resto."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=False))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return str(value)


def gen_uuid() -> str:
    return str(uuid.uuid4())
