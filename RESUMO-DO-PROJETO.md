# Sistema de Fluxo de Caixa — Distribuidora
**Repositório:** `mh0097317-ai/original-backend` · **Branch:** `main` (tudo mesclado e deployável)

## O que é
Sistema completo de gestão financeira para distribuidora: backend + app mobile.

## Backend (raiz do repo) — FastAPI + PostgreSQL (SQLAlchemy async)
- **Autenticação JWT** com papéis: `admin`, `gestor`, `visualizador` (RBAC em todas as rotas; escopo por filial)
  - Primeiro usuário criado via bootstrap: `POST /api/auth/cadastro` (só funciona uma vez, vira admin)
- **Fluxo de caixa**: filiais, contas (caixa/banco), movimentos de entrada/saída com categorias, saldo atualizado atomicamente (ACID), cancelamento reverte saldo
- **Contas a pagar/receber** com fornecedores, vencimentos e baixa
- **Relatórios**: fluxo de caixa diário, DRE mensal, resumo de contas, saldo por conta
- **Conciliação bancária via Pluggy (Open Finance)**:
  - Página `/conectar-banco` com widget Pluggy Connect (aberta em WebView pelo app)
  - Importação de extrato com deduplicação
  - Motor de conciliação automática (conta + tipo + valor + janela ±3 dias; escolhe melhor candidato por proximidade de data e semelhança de descrição)
  - Divergências acionáveis: conciliar manual, lançar no caixa, ignorar
  - Configuração: `PLUGGY_CLIENT_ID` e `PLUGGY_CLIENT_SECRET` no `.env` (sem elas, responde 503)
- **Chat da equipe**: texto e mensagens de voz (áudio base64), apagar (autor/admin)
- **Auditoria imutável** de todas as ações (`/api/auditoria`, só admin)
- **Paginação** genérica em todas as listagens (`total`, `skip`, `limit`, `items`)
- **20 testes** (pytest, SQLite in-memory) — todos passando
- Deploy: `Procfile` + `runtime.txt` (python-3.11.9); env vars: `DATABASE_URL` (postgresql+asyncpg), `SECRET_KEY`

## App mobile (`mobile/`) — React Native + Expo SDK 51
Abas: **Visão Geral** (saldos, a pagar/receber, toggle Face ID) · **Movimentos** (lançar/cancelar) ·
**Pagar/Receber** (baixa em um toque) · **Conciliação** (sincronizar banco, resolver divergências,
botão Conectar Banco → WebView Pluggy) · **Equipe** (chat com voz — segurar 🎤 grava)
- Login JWT persistido (AsyncStorage); RBAC refletido na UI
- **Desbloqueio biométrico (Face ID/digital)**: pede UMA vez ao abrir o app, nunca por aba
- Config da API: `mobile/src/api/client.js` → `BASE_URL`
- Rodar: `cd mobile && npm install && npx expo start` (Expo Go)

## Endpoints principais
`/api/auth/*` (login, token OAuth2 p/ Swagger, usuários) · `/api/filiais` · `/api/contas` ·
`/api/movimentos` · `/api/fornecedores` · `/api/contas-pagar` · `/api/contas-receber` ·
`/api/relatorios/{fluxo-caixa,dre,resumo-contas,saldo-contas}` ·
`/api/conciliacao/*` (connect-token, conexoes, importar, conciliar, transacoes, resumo) ·
`/api/chat/mensagens` · `/api/auditoria` · Docs: `/docs`

## Ideia de integração com o Easy Due
Dívidas/contas do Easy Due podem virar **contas a pagar** no fluxo de caixa
(`POST /api/contas-pagar`) e aparecer na conciliação quando o pagamento passar no banco.
