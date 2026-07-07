# Fluxo de Caixa — App Mobile

App em **React Native (Expo)** para o backend de fluxo de caixa da distribuidora.
Roda em **Android e iOS** com o mesmo código.

## Funcionalidades

- **Login** com JWT (usuários e papéis do backend: admin / gestor / visualizador)
- **Visão Geral**: saldo total, saldo por conta, totais a pagar/receber e vencidas
- **Movimentos**: lista com entradas/saídas, lançamento rápido (FAB) e
  cancelamento com reversão de saldo (segurar o item)
- **Pagar / Receber**: contas em aberto com baixa em um toque
- Visualizador vê tudo, mas não consegue lançar/baixar (RBAC respeitado na UI e na API)

## Como rodar

1. Suba o backend (na raiz do repositório):
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

2. Ajuste a URL da API em `src/api/client.js`:
   - Emulador Android: `http://10.0.2.2:8000` (padrão)
   - Aparelho físico: `http://<IP-da-sua-máquina>:8000` (mesma rede Wi-Fi)

3. Instale e inicie:
   ```bash
   cd mobile
   npm install
   npx expo start
   ```

4. Leia o QR code com o app **Expo Go** (Android/iOS) ou aperte `a` para
   abrir no emulador Android.

## Primeiro acesso

O primeiro usuário do sistema é criado pelo endpoint de bootstrap:

```bash
curl -X POST http://localhost:8000/api/auth/cadastro \
  -H 'Content-Type: application/json' \
  -d '{"nome": "Admin", "email": "admin@dist.com", "senha": "senha123"}'
```

Depois é só entrar no app com esse e-mail/senha.

## Estrutura

```
mobile/
├── App.js                  # navegação (stack + tabs) e bootstrap
└── src/
    ├── api/client.js       # cliente HTTP + token JWT (AsyncStorage)
    ├── context/AuthContext.js
    ├── theme.js            # cores, espaçamento, formatação BRL
    └── screens/
        ├── LoginScreen.js
        ├── DashboardScreen.js
        ├── MovimentosScreen.js
        ├── NovoMovimentoScreen.js
        └── ContasScreen.js
```
