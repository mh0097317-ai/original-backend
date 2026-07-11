# pluggy_client.py
"""Cliente da API do Pluggy (Open Finance Brasil) — https://docs.pluggy.ai

Autentica com CLIENT_ID/CLIENT_SECRET, mantém a apiKey em cache e expõe
o que a conciliação precisa: contas, transações e connect token (para o
widget de conexão do banco no frontend/app).

Sem credenciais configuradas os endpoints de conciliação respondem 503 —
o resto do sistema segue funcionando normalmente.
"""
from datetime import datetime, timedelta

import httpx
from fastapi import HTTPException

from database import settings

PLUGGY_BASE = "https://api.pluggy.ai"


class PluggyClient:
    def __init__(self, client_id: str, client_secret: str):
        self._client_id = client_id
        self._client_secret = client_secret
        self._api_key: str | None = None
        self._api_key_expira: datetime = datetime.min

    async def _apikey(self) -> str:
        # apiKey do Pluggy vale 2h; renova com folga de 30min
        if self._api_key and datetime.utcnow() < self._api_key_expira:
            return self._api_key
        async with httpx.AsyncClient(timeout=30) as http:
            r = await http.post(f"{PLUGGY_BASE}/auth", json={
                "clientId": self._client_id,
                "clientSecret": self._client_secret,
            })
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail="Falha ao autenticar no Pluggy")
        self._api_key = r.json()["apiKey"]
        self._api_key_expira = datetime.utcnow() + timedelta(minutes=90)
        return self._api_key

    async def _get(self, path: str, params: dict | None = None) -> dict:
        headers = {"X-API-KEY": await self._apikey()}
        async with httpx.AsyncClient(timeout=30) as http:
            r = await http.get(f"{PLUGGY_BASE}{path}", params=params, headers=headers)
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Erro do Pluggy em {path}")
        return r.json()

    async def criar_connect_token(self, item_id: str | None = None) -> str:
        """Token para o widget Pluggy Connect (frontend/app conecta o banco)."""
        headers = {"X-API-KEY": await self._apikey()}
        body = {"itemId": item_id} if item_id else {}
        async with httpx.AsyncClient(timeout=30) as http:
            r = await http.post(f"{PLUGGY_BASE}/connect_token", json=body, headers=headers)
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail="Falha ao criar connect token")
        return r.json()["accessToken"]

    async def contas(self, item_id: str) -> list[dict]:
        data = await self._get("/accounts", {"itemId": item_id})
        return data.get("results", [])

    async def transacoes(self, account_id: str, de: datetime, ate: datetime) -> list[dict]:
        """Transações da conta no período, paginando até o fim."""
        resultados: list[dict] = []
        page = 1
        while True:
            data = await self._get("/transactions", {
                "accountId": account_id,
                "from": de.date().isoformat(),
                "to": ate.date().isoformat(),
                "pageSize": 200,
                "page": page,
            })
            resultados.extend(data.get("results", []))
            if page >= data.get("totalPages", 1):
                break
            page += 1
        return resultados


def get_pluggy_client() -> PluggyClient:
    """Dependência FastAPI — sobrescrevível nos testes."""
    if not settings.PLUGGY_CLIENT_ID or not settings.PLUGGY_CLIENT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Integração Pluggy não configurada (defina PLUGGY_CLIENT_ID e PLUGGY_CLIENT_SECRET)",
        )
    return PluggyClient(settings.PLUGGY_CLIENT_ID, settings.PLUGGY_CLIENT_SECRET)
