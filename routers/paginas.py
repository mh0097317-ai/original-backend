# routers/paginas.py
"""Páginas web leves servidas pelo próprio backend.

/conectar-banco carrega o widget oficial Pluggy Connect. É aberta pela
WebView do app (que injeta o connect token de curta duração via query
string) e avisa o app do resultado via postMessage.
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Páginas"])

_PAGINA_CONECTAR = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Conectar banco</title>
  <style>
    body { margin:0; font-family:-apple-system,Roboto,sans-serif; background:#0F172A;
           color:#fff; display:flex; align-items:center; justify-content:center;
           min-height:100vh; text-align:center; }
    .box { padding:24px; }
    .spinner { margin:16px auto; width:36px; height:36px; border:4px solid #334155;
               border-top-color:#2563EB; border-radius:50%; animation:g 1s linear infinite; }
    @keyframes g { to { transform: rotate(360deg); } }
    .erro { color:#F87171; }
  </style>
</head>
<body>
  <div class="box">
    <div id="status">
      <div class="spinner"></div>
      <p>Abrindo conexão segura com o banco…</p>
    </div>
  </div>
  <script src="https://cdn.pluggy.ai/pluggy-connect/v2.9.1/pluggy-connect.js"></script>
  <script>
    function avisarApp(payload) {
      if (window.ReactNativeWebView) {
        window.ReactNativeWebView.postMessage(JSON.stringify(payload));
      }
    }
    function mostrarErro(msg) {
      document.getElementById('status').innerHTML =
        '<p class="erro">' + msg + '</p>';
    }

    var params = new URLSearchParams(location.search);
    var token = params.get('connect_token');
    if (!token) {
      mostrarErro('Token de conexão ausente. Abra esta página pelo app.');
    } else {
      var connect = new PluggyConnect({
        connectToken: token,
        includeSandbox: params.get('sandbox') === '1',
        onSuccess: function (data) {
          avisarApp({ event: 'success', itemId: data.item.id,
                      connector: data.item.connector && data.item.connector.name });
          document.getElementById('status').innerHTML =
            '<p>✅ Banco conectado! Volte ao app para concluir.</p>';
        },
        onError: function (err) {
          avisarApp({ event: 'error',
                      message: (err && err.message) || 'Falha na conexão' });
          mostrarErro('Não foi possível conectar. Feche e tente novamente.');
        },
        onClose: function () {
          avisarApp({ event: 'close' });
        },
      });
      connect.init();
    }
  </script>
</body>
</html>"""


@router.get("/conectar-banco", response_class=HTMLResponse, include_in_schema=False)
async def pagina_conectar_banco():
    return HTMLResponse(content=_PAGINA_CONECTAR)
