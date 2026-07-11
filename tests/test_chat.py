"""Testes do chat interno (texto e voz)."""
import base64

from tests.test_api import auth, _bootstrap_admin, _criar_filial


async def test_enviar_e_listar_texto(client):
    token = await _bootstrap_admin(client)

    r = await client.post("/api/chat/mensagens", headers=auth(token),
                          json={"tipo": "texto", "conteudo": "Bom dia, equipe!"})
    assert r.status_code == 201, r.text
    assert r.json()["usuario_nome"] == "Admin"

    r = await client.get("/api/chat/mensagens", headers=auth(token))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["conteudo"] == "Bom dia, equipe!"


async def test_enviar_audio_base64(client):
    token = await _bootstrap_admin(client)
    audio_fake = base64.b64encode(b"m4a-bytes-de-teste").decode()

    r = await client.post("/api/chat/mensagens", headers=auth(token),
                          json={"tipo": "audio", "conteudo": audio_fake, "duracao_seg": 4})
    assert r.status_code == 201, r.text
    assert r.json()["tipo"] == "audio"
    assert r.json()["duracao_seg"] == 4


async def test_mensagem_vazia_rejeitada(client):
    token = await _bootstrap_admin(client)
    r = await client.post("/api/chat/mensagens", headers=auth(token),
                          json={"tipo": "texto", "conteudo": "   "})
    assert r.status_code == 422


async def test_apagar_so_autor_ou_admin(client):
    token = await _bootstrap_admin(client)
    filial_id = await _criar_filial(client, token)

    # admin cria um gestor que manda mensagem
    await client.post("/api/auth/usuarios", headers=auth(token), json={
        "nome": "Gestor", "email": "gestor@dist.com", "senha": "senha123",
        "role": "gestor", "filial_id": filial_id,
    })
    r = await client.post("/api/auth/login", json={"email": "gestor@dist.com", "senha": "senha123"})
    gestor_token = r.json()["access_token"]

    r = await client.post("/api/chat/mensagens", headers=auth(gestor_token),
                          json={"conteudo": "mensagem do gestor"})
    msg_admin = await client.post("/api/chat/mensagens", headers=auth(token),
                                  json={"conteudo": "mensagem do admin"})

    # gestor não apaga mensagem do admin
    r = await client.request("DELETE", f"/api/chat/mensagens/{msg_admin.json()['id']}",
                             headers=auth(gestor_token))
    assert r.status_code == 403

    # admin apaga qualquer uma
    r = await client.request("DELETE", f"/api/chat/mensagens/{msg_admin.json()['id']}",
                             headers=auth(token))
    assert r.status_code == 204
