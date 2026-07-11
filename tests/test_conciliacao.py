"""Testes da conciliação bancária com cliente Pluggy simulado."""
from datetime import datetime, timedelta

from main import app
from pluggy_client import get_pluggy_client
from tests.test_api import auth, _bootstrap_admin, _criar_filial, _criar_conta


class PluggyFake:
    """Simula a API do Pluggy com um extrato controlado pelos testes."""

    def __init__(self, transacoes=None):
        self._transacoes = transacoes or []

    async def criar_connect_token(self, item_id=None):
        return "connect-token-fake"

    async def contas(self, item_id):
        return [{"id": "acc-1", "name": "Conta Corrente"}]

    async def transacoes(self, account_id, de, ate):
        return self._transacoes


def usar_pluggy_fake(transacoes):
    fake = PluggyFake(transacoes)
    app.dependency_overrides[get_pluggy_client] = lambda: fake
    return fake


async def _setup_conexao(client, token, conta_id):
    r = await client.post("/api/conciliacao/conexoes", headers=auth(token), json={
        "conta_id": conta_id,
        "pluggy_item_id": "item-1",
        "pluggy_account_id": "acc-1",
        "banco_nome": "Banco Teste",
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def test_pluggy_nao_configurado_responde_503(client):
    token = await _bootstrap_admin(client)
    r = await client.post("/api/conciliacao/connect-token", headers=auth(token))
    assert r.status_code == 503


async def test_importar_e_conciliar_automatico(client):
    token = await _bootstrap_admin(client)
    filial_id = await _criar_filial(client, token)
    conta_id = await _criar_conta(client, token, filial_id, "1000.00")
    conexao_id = await _setup_conexao(client, token, conta_id)

    agora = datetime.utcnow()
    iso = agora.isoformat()

    # Lança no caixa uma venda de 500 (vai casar com o crédito do extrato)
    r = await client.post("/api/movimentos", headers=auth(token), json={
        "conta_id": conta_id, "tipo": "entrada", "categoria": "vendas",
        "descricao": "Venda PIX", "valor": "500.00",
        "data_movimento": iso, "data_competencia": iso,
    })
    assert r.status_code == 201

    # Extrato do banco: o crédito de 500 (casa) e um débito de 80 (divergente)
    usar_pluggy_fake([
        {"id": "trx-1", "description": "PIX RECEBIDO",
         "amount": 500.00, "type": "CREDIT", "date": agora.isoformat() + "Z"},
        {"id": "trx-2", "description": "TARIFA BANCARIA",
         "amount": -80.00, "type": "DEBIT", "date": agora.isoformat() + "Z"},
    ])

    r = await client.post(
        f"/api/conciliacao/conexoes/{conexao_id}/importar",
        headers=auth(token),
        json={"data_inicio": (agora - timedelta(days=7)).isoformat(), "data_fim": iso},
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"importadas": 2, "ja_existentes": 0}

    # Reimportar não duplica
    r = await client.post(
        f"/api/conciliacao/conexoes/{conexao_id}/importar",
        headers=auth(token),
        json={"data_inicio": (agora - timedelta(days=7)).isoformat(), "data_fim": iso},
    )
    assert r.json() == {"importadas": 0, "ja_existentes": 2}

    # Conciliação automática: 1 casa, 1 divergente
    r = await client.post(
        f"/api/conciliacao/conexoes/{conexao_id}/conciliar", headers=auth(token)
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"conciliadas": 1, "divergentes": 1, "pendentes": 0}

    # Resumo reflete o estado
    r = await client.get("/api/conciliacao/resumo", headers=auth(token))
    body = r.json()
    assert body["conciliadas"] == 1
    assert body["divergentes"] == 1


async def test_lancar_divergente_no_caixa(client):
    token = await _bootstrap_admin(client)
    filial_id = await _criar_filial(client, token)
    conta_id = await _criar_conta(client, token, filial_id, "1000.00")
    conexao_id = await _setup_conexao(client, token, conta_id)

    agora = datetime.utcnow()
    usar_pluggy_fake([
        {"id": "trx-tarifa", "description": "TARIFA MENSAL",
         "amount": -50.00, "type": "DEBIT", "date": agora.isoformat() + "Z"},
    ])

    await client.post(
        f"/api/conciliacao/conexoes/{conexao_id}/importar",
        headers=auth(token),
        json={"data_inicio": (agora - timedelta(days=7)).isoformat(),
              "data_fim": agora.isoformat()},
    )
    await client.post(f"/api/conciliacao/conexoes/{conexao_id}/conciliar", headers=auth(token))

    # Pega a transação divergente
    r = await client.get("/api/conciliacao/transacoes?situacao=divergente", headers=auth(token))
    trans = r.json()["items"][0]
    assert trans["descricao"] == "TARIFA MENSAL"

    # Lança direto no caixa a partir do extrato
    r = await client.post(
        f"/api/conciliacao/transacoes/{trans['id']}/lancar",
        headers=auth(token),
        json={"categoria": "despesa_operacional"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status_conciliacao"] == "conciliado"
    assert r.json()["movimento_id"]

    # Saldo caiu 50 (1000 → 950)
    r = await client.get(f"/api/relatorios/saldo-contas?filial_id={filial_id}", headers=auth(token))
    assert r.json()["saldo_total"] == 950.0


async def test_visualizador_nao_concilia(client):
    token = await _bootstrap_admin(client)
    filial_id = await _criar_filial(client, token)
    conta_id = await _criar_conta(client, token, filial_id)
    conexao_id = await _setup_conexao(client, token, conta_id)

    await client.post("/api/auth/usuarios", headers=auth(token), json={
        "nome": "Vis", "email": "vis2@dist.com", "senha": "senha123",
        "role": "visualizador", "filial_id": filial_id,
    })
    r = await client.post("/api/auth/login", json={"email": "vis2@dist.com", "senha": "senha123"})
    vis_token = r.json()["access_token"]

    r = await client.post(
        f"/api/conciliacao/conexoes/{conexao_id}/conciliar", headers=auth(vis_token)
    )
    assert r.status_code == 403
