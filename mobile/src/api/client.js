import AsyncStorage from '@react-native-async-storage/async-storage';

// Ajuste para o endereço do seu backend:
// - Emulador Android: http://10.0.2.2:8000
// - Dispositivo físico: http://<IP-da-sua-máquina>:8000
// - Produção: https://sua-api.com
export const BASE_URL = 'http://10.0.2.2:8000';

const TOKEN_KEY = '@fluxocaixa/token';

export async function getToken() {
  return AsyncStorage.getItem(TOKEN_KEY);
}

export async function setToken(token) {
  if (token) await AsyncStorage.setItem(TOKEN_KEY, token);
  else await AsyncStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `Erro HTTP ${status}`);
    this.status = status;
  }
}

async function request(path, { method = 'GET', body, auth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (auth) {
    const token = await getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (res.status === 204) return null;

  let data = null;
  try {
    data = await res.json();
  } catch {
    // resposta sem corpo JSON
  }

  if (!res.ok) {
    const detail = data && data.detail
      ? (typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail))
      : null;
    throw new ApiError(res.status, detail);
  }
  return data;
}

export const api = {
  // Auth
  login: (email, senha) =>
    request('/api/auth/login', { method: 'POST', body: { email, senha }, auth: false }),
  me: () => request('/api/auth/me'),

  // Filiais e contas
  filiais: () => request('/api/filiais?limit=50'),
  contas: (filialId) =>
    request(`/api/contas?limit=100${filialId ? `&filial_id=${filialId}` : ''}`),

  // Relatórios
  saldoContas: (filialId) => request(`/api/relatorios/saldo-contas?filial_id=${filialId}`),
  resumoContas: () => request('/api/relatorios/resumo-contas'),

  // Movimentos
  movimentos: (skip = 0, limit = 25) =>
    request(`/api/movimentos?skip=${skip}&limit=${limit}`),
  criarMovimento: (payload) => request('/api/movimentos', { method: 'POST', body: payload }),
  cancelarMovimento: (id) => request(`/api/movimentos/${id}`, { method: 'DELETE' }),

  // Contas a pagar / receber
  contasPagar: (skip = 0) => request(`/api/contas-pagar?pago=false&skip=${skip}&limit=25`),
  pagarConta: (id) => request(`/api/contas-pagar/${id}/pagar`, { method: 'POST' }),
  contasReceber: (skip = 0) => request(`/api/contas-receber?recebido=false&skip=${skip}&limit=25`),
  receberConta: (id) => request(`/api/contas-receber/${id}/receber`, { method: 'POST' }),
};
