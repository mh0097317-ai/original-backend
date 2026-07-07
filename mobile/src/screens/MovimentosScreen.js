import React, { useCallback, useState } from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity, Alert, RefreshControl,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { colors, spacing, formatBRL, formatData } from '../theme';

const CATEGORIAS = {
  vendas: 'Vendas',
  recebimento: 'Recebimento',
  pagamento_fornecedor: 'Pgto. fornecedor',
  despesa_operacional: 'Despesa operacional',
  impostos: 'Impostos',
  folha_pagamento: 'Folha',
  financeiro: 'Financeiro',
  estoque: 'Estoque',
  outro: 'Outro',
};

export default function MovimentosScreen({ navigation }) {
  const { usuario } = useAuth();
  const [itens, setItens] = useState([]);
  const [total, setTotal] = useState(0);
  const [atualizando, setAtualizando] = useState(false);
  const podeEditar = usuario && usuario.role !== 'visualizador';

  const carregar = useCallback(async () => {
    try {
      const data = await api.movimentos(0, 50);
      setItens(data.items);
      setTotal(data.total);
    } catch (e) {
      Alert.alert('Erro', e.message);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      carregar();
    }, [carregar])
  );

  async function onRefresh() {
    setAtualizando(true);
    await carregar();
    setAtualizando(false);
  }

  function confirmarCancelamento(mov) {
    Alert.alert(
      'Cancelar movimento',
      `Cancelar "${mov.descricao}" (${formatBRL(mov.valor)})? O saldo será revertido.`,
      [
        { text: 'Voltar', style: 'cancel' },
        {
          text: 'Cancelar movimento',
          style: 'destructive',
          onPress: async () => {
            try {
              await api.cancelarMovimento(mov.id);
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
    const entrada = item.tipo === 'entrada';
    const cancelado = item.status === 'cancelado';
    return (
      <TouchableOpacity
        style={[styles.item, cancelado && styles.itemCancelado]}
        onLongPress={() => podeEditar && !cancelado && confirmarCancelamento(item)}
      >
        <View style={styles.itemEsq}>
          <Text style={styles.itemDesc} numberOfLines={1}>{item.descricao}</Text>
          <Text style={styles.itemMeta}>
            {CATEGORIAS[item.categoria] || item.categoria} · {formatData(item.data_movimento)}
            {cancelado ? ' · CANCELADO' : ''}
          </Text>
        </View>
        <Text style={[
          styles.itemValor,
          { color: cancelado ? colors.textMuted : entrada ? colors.success : colors.danger },
        ]}>
          {entrada ? '+' : '−'} {formatBRL(item.valor)}
        </Text>
      </TouchableOpacity>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.contador}>{total} movimento(s)</Text>
      <FlatList
        data={itens}
        keyExtractor={(item) => item.id}
        renderItem={renderItem}
        refreshControl={<RefreshControl refreshing={atualizando} onRefresh={onRefresh} />}
        ListEmptyComponent={
          <Text style={styles.vazio}>Nenhum movimento ainda. Toque em + para lançar.</Text>
        }
        contentContainerStyle={{ paddingBottom: 96 }}
      />
      {podeEditar && (
        <TouchableOpacity
          style={styles.fab}
          onPress={() => navigation.navigate('NovoMovimento')}
        >
          <Text style={styles.fabTexto}>＋</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg, padding: spacing.md },
  contador: { color: colors.textMuted, marginBottom: spacing.sm },
  item: {
    backgroundColor: colors.card, borderRadius: 12, padding: spacing.md,
    flexDirection: 'row', justifyContent: 'space-between',
    alignItems: 'center', marginBottom: spacing.sm,
  },
  itemCancelado: { opacity: 0.5 },
  itemEsq: { flex: 1, marginRight: spacing.sm },
  itemDesc: { fontWeight: '600', color: colors.text },
  itemMeta: { color: colors.textMuted, fontSize: 12, marginTop: 2 },
  itemValor: { fontWeight: '700' },
  vazio: { textAlign: 'center', color: colors.textMuted, marginTop: spacing.xl },
  fab: {
    position: 'absolute', right: spacing.lg, bottom: spacing.lg,
    width: 56, height: 56, borderRadius: 28, backgroundColor: colors.accent,
    alignItems: 'center', justifyContent: 'center', elevation: 4,
    shadowColor: '#000', shadowOpacity: 0.2, shadowRadius: 6, shadowOffset: { width: 0, height: 3 },
  },
  fabTexto: { color: '#fff', fontSize: 28, lineHeight: 32 },
});
