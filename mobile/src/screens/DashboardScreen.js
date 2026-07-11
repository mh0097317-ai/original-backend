import React, { useCallback, useEffect, useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, RefreshControl, TouchableOpacity,
  Switch, Alert,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import {
  biometriaAtiva, biometriaDisponivel, definirBiometria, autenticarBiometria,
} from '../biometria';
import { colors, spacing, formatBRL } from '../theme';

export default function DashboardScreen() {
  const { usuario, logout } = useAuth();
  const [saldo, setSaldo] = useState(null);
  const [resumo, setResumo] = useState(null);
  const [filial, setFilial] = useState(null);
  const [erro, setErro] = useState(null);
  const [atualizando, setAtualizando] = useState(false);
  const [bioDisponivel, setBioDisponivel] = useState(false);
  const [bioAtiva, setBioAtiva] = useState(false);

  useEffect(() => {
    (async () => {
      setBioDisponivel(await biometriaDisponivel());
      setBioAtiva(await biometriaAtiva());
    })();
  }, []);

  async function alternarBiometria(valor) {
    if (valor) {
      // confirma a biometria antes de ativar, para não trancar o usuário
      const ok = await autenticarBiometria();
      if (!ok) {
        Alert.alert('Face ID', 'Autenticação não confirmada — o desbloqueio não foi ativado.');
        return;
      }
    }
    await definirBiometria(valor);
    setBioAtiva(valor);
  }

  const carregar = useCallback(async () => {
    setErro(null);
    try {
      // Admin vê a primeira filial; gestor/visualizador a própria
      let filialId = usuario?.filial_id;
      let filialInfo = null;
      const filiais = await api.filiais();
      if (filialId) {
        filialInfo = filiais.items.find((f) => f.id === filialId) || null;
      } else if (filiais.items.length > 0) {
        filialInfo = filiais.items[0];
        filialId = filialInfo.id;
      }
      setFilial(filialInfo);

      const [s, r] = await Promise.all([
        filialId ? api.saldoContas(filialId) : Promise.resolve(null),
        api.resumoContas(),
      ]);
      setSaldo(s);
      setResumo(r);
    } catch (e) {
      setErro(e.message);
    }
  }, [usuario]);

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

  return (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={atualizando} onRefresh={onRefresh} />}
    >
      <View style={styles.header}>
        <View>
          <Text style={styles.ola}>Olá, {usuario?.nome} 👋</Text>
          <Text style={styles.filial}>{filial ? filial.nome : 'Sem filial'}</Text>
        </View>
        <TouchableOpacity onPress={logout}>
          <Text style={styles.sair}>Sair</Text>
        </TouchableOpacity>
      </View>

      {erro && <Text style={styles.erro}>{erro}</Text>}

      <View style={styles.cardSaldo}>
        <Text style={styles.cardLabel}>Saldo total em contas</Text>
        <Text style={styles.cardValor}>
          {saldo ? formatBRL(saldo.saldo_total) : '—'}
        </Text>
      </View>

      {saldo && saldo.contas.map((c) => (
        <View key={c.id} style={styles.linhaConta}>
          <View>
            <Text style={styles.contaNome}>{c.nome}</Text>
            <Text style={styles.contaTipo}>{c.tipo}</Text>
          </View>
          <Text style={styles.contaSaldo}>{formatBRL(c.saldo)}</Text>
        </View>
      ))}

      {bioDisponivel && (
        <View style={styles.linhaConta}>
          <View>
            <Text style={styles.contaNome}>🔐 Entrar com Face ID</Text>
            <Text style={styles.contaTipo}>Pede o desbloqueio só ao abrir o app</Text>
          </View>
          <Switch
            value={bioAtiva}
            onValueChange={alternarBiometria}
            trackColor={{ true: colors.accent }}
          />
        </View>
      )}

      {resumo && (
        <View style={styles.gridResumo}>
          <View style={[styles.tile, { borderLeftColor: colors.danger }]}>
            <Text style={styles.tileLabel}>A pagar</Text>
            <Text style={[styles.tileValor, { color: colors.danger }]}>
              {formatBRL(resumo.total_contas_pagar)}
            </Text>
            {resumo.contas_pagar_vencidas > 0 && (
              <Text style={styles.vencidas}>{resumo.contas_pagar_vencidas} vencida(s)</Text>
            )}
          </View>
          <View style={[styles.tile, { borderLeftColor: colors.success }]}>
            <Text style={styles.tileLabel}>A receber</Text>
            <Text style={[styles.tileValor, { color: colors.success }]}>
              {formatBRL(resumo.total_contas_receber)}
            </Text>
            {resumo.contas_receber_vencidas > 0 && (
              <Text style={styles.vencidas}>{resumo.contas_receber_vencidas} vencida(s)</Text>
            )}
          </View>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg, padding: spacing.md },
  header: {
    flexDirection: 'row', justifyContent: 'space-between',
    alignItems: 'center', marginBottom: spacing.md, marginTop: spacing.sm,
  },
  ola: { fontSize: 20, fontWeight: '700', color: colors.text },
  filial: { color: colors.textMuted, marginTop: 2 },
  sair: { color: colors.accent, fontWeight: '600' },
  erro: { color: colors.danger, marginBottom: spacing.md },
  cardSaldo: {
    backgroundColor: colors.primary, borderRadius: 16,
    padding: spacing.lg, marginBottom: spacing.md,
  },
  cardLabel: { color: '#94A3B8', fontSize: 14 },
  cardValor: { color: '#fff', fontSize: 32, fontWeight: '700', marginTop: spacing.xs },
  linhaConta: {
    backgroundColor: colors.card, borderRadius: 12, padding: spacing.md,
    flexDirection: 'row', justifyContent: 'space-between',
    alignItems: 'center', marginBottom: spacing.sm,
  },
  contaNome: { fontWeight: '600', color: colors.text },
  contaTipo: { color: colors.textMuted, fontSize: 12, marginTop: 2 },
  contaSaldo: { fontWeight: '700', color: colors.text },
  gridResumo: { flexDirection: 'row', gap: spacing.sm, marginTop: spacing.sm, marginBottom: spacing.xl },
  tile: {
    flex: 1, backgroundColor: colors.card, borderRadius: 12,
    padding: spacing.md, borderLeftWidth: 4,
  },
  tileLabel: { color: colors.textMuted, fontSize: 13 },
  tileValor: { fontSize: 18, fontWeight: '700', marginTop: spacing.xs },
  vencidas: { color: colors.warning, fontSize: 12, marginTop: spacing.xs, fontWeight: '600' },
});
