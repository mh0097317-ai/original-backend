import React, { createContext, useContext, useEffect, useState } from 'react';
import { api, getToken, setToken } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    // Restaura sessão salva ao abrir o app
    (async () => {
      try {
        const token = await getToken();
        if (token) {
          const me = await api.me();
          setUsuario(me);
        }
      } catch {
        await setToken(null);
      } finally {
        setCarregando(false);
      }
    })();
  }, []);

  async function login(email, senha) {
    const data = await api.login(email, senha);
    await setToken(data.access_token);
    setUsuario(data.usuario);
  }

  async function logout() {
    await setToken(null);
    setUsuario(null);
  }

  return (
    <AuthContext.Provider value={{ usuario, carregando, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
