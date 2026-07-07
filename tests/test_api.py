"""Testes de integração ponta-a-ponta do sistema de fluxo de caixa."""
from datetime import datetime, timedelta


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _bootstrap_admin(client) -> str:
    """Cria o primeiro usuário (admin) e devolve o token."""
    r = await client.post("/api/auth/cadastro", json={
        "nome": "Admin", "email": "admin@dist.com", "senha": "senha123",
    })
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


async def _criar_filial(client, token: str) -> str:
    r = await client.post("/api/filiais", headers=auth(token), json={
        "nome": "Matriz", "cnpj": "11.111.111/0001-11",
        "endereco": "Rua A, 1", "cidade": "SP", "estado": "SP",
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _criar_conta(client, token: str, filial_id: str, saldo: str = "1000.00") -> str:
    r = await client.post("/api/contas", headers=auth(token), json={
        "filial_id": filial_id, "nome": "Caixa", "tipo": "caixa",
        "saldo_inicial": saldo,
    })
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["saldo_atual"] == saldo
    return data["id"]


async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_acesso_sem_token_bloqueado(client):
    r = await client.get("/api/filiais")
    assert r.status_code == 401


async def test_bootstrap_so_uma_vez(client):
    await _bootstrap_admin(client)
    # Segundo cadastro deve ser bloqueado (sistema já inicializado)
    r = await client.post("/api/auth/cadastro", json={
        "nome": "Outro", "email": "outro@dist.com", "senha": "senha123",
    })
    assert r.status_code == 403


async def test_fluxo_completo_e_saldo(client):
    token = await _bootstrap_admin(client)
    filial_id = await _criar_filial(client, token)
    conta_id = await _criar_conta(client, token, filial_id, "1000.00")

    agora = datetime.utcnow().isoformat()

    # Entrada de 500 → saldo 1500
    r = await client.post("/api/movimentos", headers=auth(token), json={
        "conta_id": conta_id, "tipo": "entrada", "categoria": "vendas",
        "descricao": "Venda 1", "valor": "500.00",
        "data_movimento": agora, "data_competencia": agora,
    })
    assert r.status_code == 201, r.text

    # Saída de 200 → saldo 1300
    r = await client.post("/api/movimentos", headers=auth(token), json={
        "conta_id": conta_id, "tipo": "saida", "categoria": "despesa_operacional",
        "descricao": "Aluguel", "valor": "200.00",
        "data_movimento": agora, "data_competencia": agora,
    })
    assert r.status_code == 201, r.text

    # Saldo da conta deve refletir os movimentos
    r = await client.get(f"/api/relatorios/saldo-contas?filial_id={filial_id}", headers=auth(token))
    assert r.status_code == 200
    assert r.json()["saldo_total"] == 1300.0

    # Listagem paginada
    r = await client.get("/api/movimentos", headers=auth(token))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


async def test_saldo_insuficiente(client):
    token = await _bootstrap_admin(client)
    filial_id = await _criar_filial(client, token)
    conta_id = await _criar_conta(client, token, filial_id, "100.00")
    agora = datetime.utcnow().isoformat()

    r = await client.post("/api/movimentos", headers=auth(token), json={
        "conta_id": conta_id, "tipo": "saida", "categoria": "despesa_operacional",
        "descricao": "Estouro", "valor": "999.00",
        "data_movimento": agora, "data_competencia": agora,
    })
    assert r.status_code == 400
    assert "insuficiente" in r.json()["detail"].lower()


async def test_cancelamento_reverte_saldo(client):
    token = await _bootstrap_admin(client)
    filial_id = await _criar_filial(client, token)
    conta_id = await _criar_conta(client, token, filial_id, "1000.00")
    agora = datetime.utcnow().isoformat()

    r = await client.post("/api/movimentos", headers=auth(token), json={
        "conta_id": conta_id, "tipo": "saida", "categoria": "impostos",
        "descricao": "Imposto", "valor": "300.00",
        "data_movimento": agora, "data_competencia": agora,
    })
    mov_id = r.json()["id"]

    # saldo 700 após saída
    r = await client.get(f"/api/relatorios/saldo-contas?filial_id={filial_id}", headers=auth(token))
    assert r.json()["saldo_total"] == 700.0

    # Cancela → saldo volta a 1000
    r = await client.request("DELETE", f"/api/movimentos/{mov_id}", headers=auth(token))
    assert r.status_code == 200
    assert r.json()["status"] == "cancelado"

    r = await client.get(f"/api/relatorios/saldo-contas?filial_id={filial_id}", headers=auth(token))
    assert r.json()["saldo_total"] == 1000.0


async def test_rbac_visualizador_nao_cria(client):
    token = await _bootstrap_admin(client)
    filial_id = await _criar_filial(client, token)
    conta_id = await _criar_conta(client, token, filial_id, "1000.00")

    # admin cria um visualizador
    r = await client.post("/api/auth/usuarios", headers=auth(token), json={
        "nome": "Vis", "email": "vis@dist.com", "senha": "senha123",
        "role": "visualizador", "filial_id": filial_id,
    })
    assert r.status_code == 201, r.text

    # visualizador faz login
    r = await client.post("/api/auth/login", json={"email": "vis@dist.com", "senha": "senha123"})
    vis_token = r.json()["access_token"]

    # visualizador consegue ler
    r = await client.get("/api/movimentos", headers=auth(vis_token))
    assert r.status_code == 200

    # mas não consegue criar movimento (403)
    agora = datetime.utcnow().isoformat()
    r = await client.post("/api/movimentos", headers=auth(vis_token), json={
        "conta_id": conta_id, "tipo": "entrada", "categoria": "vendas",
        "descricao": "X", "valor": "10.00",
        "data_movimento": agora, "data_competencia": agora,
    })
    assert r.status_code == 403


async def test_dre_e_auditoria(client):
    token = await _bootstrap_admin(client)
    filial_id = await _criar_filial(client, token)
    conta_id = await _criar_conta(client, token, filial_id, "0.00")
    hoje = datetime.utcnow()
    iso = hoje.isoformat()

    await client.post("/api/movimentos", headers=auth(token), json={
        "conta_id": conta_id, "tipo": "entrada", "categoria": "vendas",
        "descricao": "Venda", "valor": "1000.00",
        "data_movimento": iso, "data_competencia": iso,
    })

    r = await client.get(
        f"/api/relatorios/dre?filial_id={filial_id}&mes={hoje.month}&ano={hoje.year}",
        headers=auth(token),
    )
    assert r.status_code == 200
    assert r.json()["receitas_vendas"] == "1000.00"

    # Auditoria registrou as ações
    r = await client.get("/api/auditoria", headers=auth(token))
    assert r.status_code == 200
    assert r.json()["total"] > 0
