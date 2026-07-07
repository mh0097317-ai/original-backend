import React, { useEffect, useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ScrollView, Alert, ActivityIndicator,
} from 'react-native';
import { api } from '../api/client';
import { colors, spacing } from '../theme';

const CATEGORIAS_ENTRADA = [
  { key: 'vendas', label: 'Vendas' },
  { key: 'recebimento', label: 'Recebimento' },
  { key: 'financeiro', label: 'Financeiro' },
  { key: 'outro', label: 'Outro' },
];

const CATEGORIAS_SAIDA = [
  { key: 'pagamento_fornecedor', label: 'Fornecedor' },
  { key: 'despesa_operacional', label: 'Despesa' },
  { key: 'impostos', label: 'Impostos' },
  { key: 'folha_pagamento', label: 'Folha' },
  { key: 'estoque', label: 'Estoque' },
  { key: 'outro', label: 'Outro' },
];

export default function NovoMovimentoScreen({ navigation }) {
  const [contas, setContas] = useState([]);
  const [contaId, setContaId] = useState(null);
  const [tipo, setTipo] = useState('entrada');
  const [categoria, setCategoria] = useState('vendas');
  const [descricao, setDescricao] = useState('');
  const [valor, setValor] = useState('');
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    api.contas()
      .then((data) => {
        setContas(data.items);
        if (data.items.length > 0) setContaId(data.items[0].id);
      })
      .catch((e) => Alert.alert('Erro', e.message));
  }, []);

  const categorias = tipo === 'entrada' ? CATEGORIAS_ENTRADA : CATEGORIAS_SAIDA;

  function trocarTipo(novoTipo) {
    setTipo(novoTipo);
    setCategoria(novoTipo === 'entrada' ? 'vendas' : 'pagamento_fornecedor');
  }

  async function salvar() {
    const valorNum = parseFloat(valor.replace(',', '.'));
    if (!contaId) return Alert.alert('Atenção', 'Selecione uma conta');
    if (!descricao.trim()) return Alert.alert('Atenção', 'Informe a descrição');
    if (!valorNum || valorNum <= 0) return Alert.alert('Atenção', 'Informe um valor válido');

    setEnviando(true);
    try {
      const agora = new Date().toISOString();
      await api.criarMovimento({
        conta_id: contaId,
        tipo,
        categoria,
        descricao: descricao.trim(),
        valor: valorNum.toFixed(2),
        data_movimento: agora,
        data_competencia: agora,
      });
      navigation.goBack();
    } catch (e) {
      Alert.alert('Erro', e.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <ScrollView style={styles.container} keyboardShouldPersistTaps="handled">
      <Text style={styles.label}>Tipo</Text>
      <View style={styles.linha}>
        <TouchableOpacity
          style={[styles.chip, tipo === 'entrada' && styles.chipEntrada]}
          onPress={() => trocarTipo('entrada')}
        >
          <Text style={[styles.chipTexto, tipo === 'entrada' && styles.chipTextoAtivo]}>
            ↓ Entrada
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.chip, tipo === 'saida' && styles.chipSaida]}
          onPress={() => trocarTipo('saida')}
        >
          <Text style={[styles.chipTexto, tipo === 'saida' && styles.chipTextoAtivo]}>
            ↑ Saída
          </Text>
        </TouchableOpacity>
      </View>

      <Text style={styles.label}>Conta</Text>
      <View style={styles.linhaWrap}>
        {contas.map((c) => (
          <TouchableOpacity
            key={c.id}
            style={[styles.chip, contaId === c.id && styles.chipAtivo]}
            onPress={() => setContaId(c.id)}
          >
            <Text style={[styles.chipTexto, contaId === c.id && styles.chipTextoAtivo]}>
              {c.nome}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <Text style={styles.label}>Categoria</Text>
      <View style={styles.linhaWrap}>
        {categorias.map((c) => (
          <TouchableOpacity
            key={c.key}
            style={[styles.chip, categoria === c.key && styles.chipAtivo]}
            onPress={() => setCategoria(c.key)}
          >
            <Text style={[styles.chipTexto, categoria === c.key && styles.chipTextoAtivo]}>
              {c.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <Text style={styles.label}>Descrição</Text>
      <TextInput
        style={styles.input}
        placeholder="Ex.: Venda pedido #1234"
        placeholderTextColor={colors.textMuted}
        value={descricao}
        onChangeText={setDescricao}
      />

      <Text style={styles.label}>Valor (R$)</Text>
      <TextInput
        style={styles.input}
        placeholder="0,00"
        placeholderTextColor={colors.textMuted}
        keyboardType="decimal-pad"
        value={valor}
        onChangeText={setValor}
      />

      <TouchableOpacity style={styles.botao} onPress={salvar} disabled={enviando}>
        {enviando
          ? <ActivityIndicator color="#fff" />
          : <Text style={styles.botaoTexto}>Salvar movimento</Text>}
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg, padding: spacing.md },
  label: { fontWeight: '600', color: colors.text, marginBottom: spacing.sm, marginTop: spacing.md },
  linha: { flexDirection: 'row', gap: spacing.sm },
  linhaWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  chip: {
    borderWidth: 1, borderColor: colors.border, backgroundColor: colors.card,
    borderRadius: 20, paddingVertical: spacing.sm, paddingHorizontal: spacing.md,
  },
  chipAtivo: { backgroundColor: colors.accent, borderColor: colors.accent },
  chipEntrada: { backgroundColor: colors.success, borderColor: colors.success },
  chipSaida: { backgroundColor: colors.danger, borderColor: colors.danger },
  chipTexto: { color: colors.text },
  chipTextoAtivo: { color: '#fff', fontWeight: '600' },
  input: {
    borderWidth: 1, borderColor: colors.border, borderRadius: 10, backgroundColor: colors.card,
    padding: spacing.md, fontSize: 16, color: colors.text,
  },
  botao: {
    backgroundColor: colors.accent, borderRadius: 10, padding: spacing.md,
    alignItems: 'center', marginTop: spacing.lg, marginBottom: spacing.xl,
  },
  botaoTexto: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
