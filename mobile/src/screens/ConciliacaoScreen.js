import React, { useCallback, useState } from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity, Alert,
  RefreshControl, ActivityIndicator,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { colors, spacing, formatBRL, formatData } from '../theme';

const ABAS = [
  { key: 'divergente', label: 'Divergentes' },
  { key: 'pendente', label: 'Pendentes' },
  { key: 'conciliado', label: 'Conciliadas' },
];

const CATEGORIAS_LANCAR = [
  { key: 'despesa_operacional', label: 'Despesa' },
  { key: 'pagamento_fornecedor', label: 'Fornecedor' },
  { key: 'impostos', label: 'Impostos' },
  { key: 'recebimento', label: 'Recebimento' },
  { key: 'vendas', label: 'Vendas' },
  { key: 'outro', label: 'Outro' },
];

export default function ConciliacaoScreen() {
  const { usuario } = useAuth();
  const [aba, setAba] = useState('divergente');
  const [resumo, setResumo] = useState(null);
  const [itens, setItens] = useState([]);
  const [atualizando, setAtualizando] = useState(false);
  const [sincronizando, setSincronizando] = useState(false);
  const [lancandoId, setLancandoId] = useState(null); // item expandido p/ escolher categoria
  const podeEditar = usuario && usuario.role !== 'visualizador';

  const carregar = useCallback(async (qual = aba) => {
    try {
      const [r, t] = await Promise.all([
        api.resumoConciliacao(),
        api.transacoesBancarias(qual),
      ]);
      setResumo(r);
      setItens(t.items);
    } catch (e) {
      Alert.alert('Erro', e.message);
    }
  }, [aba]);

  useFocusEffect(
    useCallback(() => {
      carregar();
    }, [carregar])
  );

  function trocarAba(nova) {
    setAba(nova);
    setItens([]);
    setLancandoId(null);
    carregar(nova);
  }

  async function sincronizar() {
    setSincronizando(true);
    try {
      const conexoes = await api.conexoesBancarias();
      if (conexoes.items.length === 0) {
        Alert.alert(
          'Nenhum banco conectado',
          'Conecte o banco da empresa via Pluggy no painel web para começar a conciliar.'
        );
        return;
      }
      const fim = new Date();
      const inicio = new Date(fim.getTime() - 30 * 24 * 60 * 60 * 1000);
      let importadas = 0;
      let conciliadas = 0;
      let divergentes = 0;
      for (const cx of conexoes.items) {
        const imp = await api.importarExtrato(cx.id, inicio.toISOString(), fim.toISOString());
        importadas += imp.importadas;
        const rec = await api.conciliarAutomatico(cx.id);
        conciliadas += rec.conciliadas;
        divergentes += rec.divergentes;
      }
      Alert.alert(
        'Sincronização concluída',
        `${importadas} transação(ões) importada(s)\n${conciliadas} conciliada(s) automaticamente\n${divergentes} divergente(s) para revisar`
      );
      await carregar();
    } catch (e) {
      Alert.alert('Erro na sincronização', e.message);
    } finally {
      setSincronizando(false);
    }
  }

  async function lancar(item, categoria) {
    try {
      await api.lancarTransacao(item.id, categoria);
      setLancandoId(null);
      await carregar();
    } catch (e) {
      Alert.alert('Erro', e.message);
    }
  }

  function confirmarIgnorar(item) {
    Alert.alert(
      'Ignorar transação',
      `"${item.descricao}" (${formatBRL(item.valor)}) não será mais listada como divergência.`,
      [
        { text: 'Voltar', style: 'cancel' },
        {
          text: 'Ignorar',
          style: 'destructive',
          onPress: async () => {
            try {
              await api.ignorarTransacao(item.id);
              await carregar();
            } catch (e) {
              Alert.alert('Erro', e.message);
            }
          },
        },
      ]
    );
  }

  function renderItem({ item }) {
    const entrada = item.tipo === 'entrada';
    const divergente = item.status_conciliacao === 'divergente';
    const expandido = lancandoId === item.id;
    return (
      <View style={[styles.item, divergente && styles.itemDivergente]}>
        <View style={styles.itemLinha}>
          <View style={styles.itemEsq}>
            <Text style={styles.itemDesc} numberOfLines={1}>{item.descricao}</Text>
            <Text style={styles.itemMeta}>
              {formatData(item.data)}
              {item.status_conciliacao === 'conciliado' ? ' · ✓ conciliada' : ''}
            </Text>
          </View>
          <Text style={[styles.itemValor, { color: entrada ? colors.success : colors.danger }]}>
            {entrada ? '+' : '−'} {formatBRL(item.valor)}
          </Text>
        </View>

        {divergente && podeEditar && (
          <View style={styles.acoes}>
            <TouchableOpacity
              style={styles.acaoLancar}
              onPress={() => setLancandoId(expandido ? null : item.id)}
            >
              <Text style={styles.acaoLancarTexto}>
                {expandido ? 'Cancelar' : 'Lançar no caixa'}
              </Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.acaoIgnorar} onPress={() => confirmarIgnorar(item)}>
              <Text style={styles.acaoIgnorarTexto}>Ignorar</Text>
            </TouchableOpacity>
          </View>
        )}

        {expandido && (
          <View style={styles.categorias}>
            <Text style={styles.categoriasLabel}>Lançar como:</Text>
            <View style={styles.categoriasChips}>
              {CATEGORIAS_LANCAR.map((c) => (
                <TouchableOpacity
                  key={c.key}
                  style={styles.chip}
                  onPress={() => lancar(item, c.key)}
                >
                  <Text style={styles.chipTexto}>{c.label}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        )}
      </View>
    );
  }

  async function onRefresh() {
    setAtualizando(true);
    await carregar();
    setAtualizando(false);
  }

  return (
    <View style={styles.container}>
      {resumo && (
        <View style={styles.resumo}>
          <View style={styles.stat}>
            <Text style={[styles.statNum, { color: colors.success }]}>{resumo.conciliadas}</Text>
            <Text style={styles.statLabel}>conciliadas</Text>
          </View>
          <View style={styles.stat}>
            <Text style={[styles.statNum, { color: colors.warning }]}>{resumo.divergentes}</Text>
            <Text style={styles.statLabel}>divergentes</Text>
          </View>
          <View style={styles.stat}>
            <Text style={[styles.statNum, { color: colors.textMuted }]}>{resumo.pendentes}</Text>
            <Text style={styles.statLabel}>pendentes</Text>
          </View>
        </View>
      )}

      {podeEditar && (
        <TouchableOpacity style={styles.botaoSync} onPress={sincronizar} disabled={sincronizando}>
          {sincronizando
            ? <ActivityIndicator color="#fff" />
            : <Text style={styles.botaoSyncTexto}>🔄 Sincronizar com o banco</Text>}
        </TouchableOpacity>
      )}

      <View style={styles.abas}>
        {ABAS.map((a) => (
          <TouchableOpacity
            key={a.key}
            style={[styles.abaBtn, aba === a.key && styles.abaAtiva]}
            onPress={() => trocarAba(a.key)}
          >
            <Text style={[styles.abaTexto, aba === a.key && styles.abaTextoAtivo]}>{a.label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <FlatList
        data={itens}
        keyExtractor={(item) => item.id}
        renderItem={renderItem}
        refreshControl={<RefreshControl refreshing={atualizando} onRefresh={onRefresh} />}
        ListEmptyComponent={
          <Text style={styles.vazio}>
            {aba === 'divergente'
              ? 'Nenhuma divergência. Extrato e caixa estão batendo. 🎉'
              : 'Nada por aqui.'}
          </Text>
        }
        contentContainerStyle={{ paddingBottom: spacing.xl }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg, padding: spacing.md },
  resumo: {
    flexDirection: 'row', backgroundColor: colors.card,
    borderRadius: 12, padding: spacing.md, marginBottom: spacing.sm,
  },
  stat: { flex: 1, alignItems: 'center' },
  statNum: { fontSize: 22, fontWeight: '700' },
  statLabel: { color: colors.textMuted, fontSize: 12, marginTop: 2 },
  botaoSync: {
    backgroundColor: colors.accent, borderRadius: 10,
    padding: spacing.md, alignItems: 'center', marginBottom: spacing.sm,
  },
  botaoSyncTexto: { color: '#fff', fontWeight: '600' },
  abas: {
    flexDirection: 'row', backgroundColor: colors.card,
    borderRadius: 10, padding: 4, marginBottom: spacing.md,
  },
  abaBtn: { flex: 1, padding: spacing.sm, borderRadius: 8, alignItems: 'center' },
  abaAtiva: { backgroundColor: colors.primary },
  abaTexto: { color: colors.textMuted, fontWeight: '600', fontSize: 13 },
  abaTextoAtivo: { color: '#fff' },
  item: {
    backgroundColor: colors.card, borderRadius: 12,
    padding: spacing.md, marginBottom: spacing.sm,
  },
  itemDivergente: { borderLeftWidth: 4, borderLeftColor: colors.warning },
  itemLinha: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  itemEsq: { flex: 1, marginRight: spacing.sm },
  itemDesc: { fontWeight: '600', color: colors.text },
  itemMeta: { color: colors.textMuted, fontSize: 12, marginTop: 2 },
  itemValor: { fontWeight: '700' },
  acoes: { flexDirection: 'row', gap: spacing.sm, marginTop: spacing.md },
  acaoLancar: {
    flex: 1, backgroundColor: colors.accent, borderRadius: 8,
    padding: spacing.sm, alignItems: 'center',
  },
  acaoLancarTexto: { color: '#fff', fontWeight: '600', fontSize: 13 },
  acaoIgnorar: {
    flex: 1, borderWidth: 1, borderColor: colors.border, borderRadius: 8,
    padding: spacing.sm, alignItems: 'center',
  },
  acaoIgnorarTexto: { color: colors.textMuted, fontWeight: '600', fontSize: 13 },
  categorias: { marginTop: spacing.md },
  categoriasLabel: { color: colors.textMuted, fontSize: 12, marginBottom: spacing.sm },
  categoriasChips: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  chip: {
    borderWidth: 1, borderColor: colors.accent, borderRadius: 16,
    paddingVertical: 6, paddingHorizontal: spacing.md,
  },
  chipTexto: { color: colors.accent, fontWeight: '600', fontSize: 13 },
  vazio: { textAlign: 'center', color: colors.textMuted, marginTop: spacing.xl },
});
