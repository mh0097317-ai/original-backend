import React, { useCallback, useState } from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity, Alert, RefreshControl,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { colors, spacing, formatBRL, formatData } from '../theme';

export default function ContasScreen() {
  const { usuario } = useAuth();
  const [aba, setAba] = useState('pagar');
  const [itens, setItens] = useState([]);
  const [atualizando, setAtualizando] = useState(false);
  const podeEditar = usuario && usuario.role !== 'visualizador';

  const carregar = useCallback(async (qual = aba) => {
    try {
      const data = qual === 'pagar' ? await api.contasPagar() : await api.contasReceber();
      setItens(data.items);
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
    carregar(nova);
  }

  function confirmarBaixa(item) {
    const ehPagar = aba === 'pagar';
    Alert.alert(
      ehPagar ? 'Confirmar pagamento' : 'Confirmar recebimento',
      `${item.descricao} — ${formatBRL(item.valor)}`,
      [
        { text: 'Voltar', style: 'cancel' },
        {
          text: ehPagar ? 'Pagar' : 'Receber',
          onPress: async () => {
            try {
              if (ehPagar) await api.pagarConta(item.id);
              else await api.receberConta(item.id);
              carregar();
            } catch (e) {
              Alert.alert('Erro', e.message);
            }
          },
        },
      ]
    );
  }

  function renderItem({ item }) {
    const vencida = new Date(item.data_vencimento) < new Date();
    return (
      <View style={styles.item}>
        <View style={styles.itemEsq}>
          <Text style={styles.itemDesc} numberOfLines={1}>{item.descricao}</Text>
          <Text style={styles.itemMeta}>
            {aba === 'receber' && item.cliente_nome ? `${item.cliente_nome} · ` : ''}
            Doc. {item.numero_documento}
          </Text>
          <Text style={[styles.venc, vencida && styles.vencida]}>
            Vence {formatData(item.data_vencimento)}{vencida ? ' · VENCIDA' : ''}
          </Text>
        </View>
        <View style={styles.itemDir}>
          <Text style={styles.itemValor}>{formatBRL(item.valor)}</Text>
          {podeEditar && (
            <TouchableOpacity style={styles.botaoBaixa} onPress={() => confirmarBaixa(item)}>
              <Text style={styles.botaoBaixaTexto}>
                {aba === 'pagar' ? 'Pagar' : 'Receber'}
              </Text>
            </TouchableOpacity>
          )}
        </View>
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
      <View style={styles.abas}>
        <TouchableOpacity
          style={[styles.abaBtn, aba === 'pagar' && styles.abaAtiva]}
          onPress={() => trocarAba('pagar')}
        >
          <Text style={[styles.abaTexto, aba === 'pagar' && styles.abaTextoAtivo]}>A pagar</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.abaBtn, aba === 'receber' && styles.abaAtiva]}
          onPress={() => trocarAba('receber')}
        >
          <Text style={[styles.abaTexto, aba === 'receber' && styles.abaTextoAtivo]}>A receber</Text>
        </TouchableOpacity>
      </View>

      <FlatList
        data={itens}
        keyExtractor={(item) => item.id}
        renderItem={renderItem}
        refreshControl={<RefreshControl refreshing={atualizando} onRefresh={onRefresh} />}
        ListEmptyComponent={
          <Text style={styles.vazio}>
            Nenhuma conta {aba === 'pagar' ? 'a pagar' : 'a receber'} em aberto. 🎉
          </Text>
        }
        contentContainerStyle={{ paddingBottom: spacing.xl }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg, padding: spacing.md },
  abas: {
    flexDirection: 'row', backgroundColor: colors.card,
    borderRadius: 10, padding: 4, marginBottom: spacing.md,
  },
  abaBtn: { flex: 1, padding: spacing.sm, borderRadius: 8, alignItems: 'center' },
  abaAtiva: { backgroundColor: colors.primary },
  abaTexto: { color: colors.textMuted, fontWeight: '600' },
  abaTextoAtivo: { color: '#fff' },
  item: {
    backgroundColor: colors.card, borderRadius: 12, padding: spacing.md,
    flexDirection: 'row', justifyContent: 'space-between', marginBottom: spacing.sm,
  },
  itemEsq: { flex: 1, marginRight: spacing.sm },
  itemDesc: { fontWeight: '600', color: colors.text },
  itemMeta: { color: colors.textMuted, fontSize: 12, marginTop: 2 },
  venc: { color: colors.textMuted, fontSize: 12, marginTop: 4 },
  vencida: { color: colors.warning, fontWeight: '700' },
  itemDir: { alignItems: 'flex-end', justifyContent: 'space-between' },
  itemValor: { fontWeight: '700', color: colors.text },
  botaoBaixa: {
    backgroundColor: colors.accent, borderRadius: 8,
    paddingVertical: 6, paddingHorizontal: spacing.md, marginTop: spacing.sm,
  },
  botaoBaixaTexto: { color: '#fff', fontWeight: '600', fontSize: 13 },
  vazio: { textAlign: 'center', color: colors.textMuted, marginTop: spacing.xl },
});
