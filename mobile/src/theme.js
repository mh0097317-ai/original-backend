// Tema central do app — cores e espaçamentos
export const colors = {
  primary: '#0F172A',      // azul-escuro (header, botões)
  accent: '#2563EB',       // azul de ação
  success: '#16A34A',      // entradas
  danger: '#DC2626',       // saídas
  warning: '#D97706',      // vencidas
  bg: '#F1F5F9',
  card: '#FFFFFF',
  text: '#0F172A',
  textMuted: '#64748B',
  border: '#E2E8F0',
};

export const spacing = { xs: 4, sm: 8, md: 16, lg: 24, xl: 32 };

export function formatBRL(valor) {
  const n = Number(valor || 0);
  return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

export function formatData(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString('pt-BR');
}
