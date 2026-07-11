import React, { useEffect, useState } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, Alert, ActivityIndicator, ScrollView,
} from 'react-native';
import { WebView } from 'react-native-webview';
import { api, BASE_URL } from '../api/client';
import { colors, spacing } from '../theme';

// Fluxo: widget (WebView do Pluggy Connect) → vincular (escolhe conta
// do banco × conta do sistema) → pronto.
export default function ConectarBancoScreen({ navigation }) {
  const [etapa, setEtapa] = useState('carregando'); // carregando | widget | vincular
  const [urlWidget, setUrlWidget] = useState(null);
  const [itemId, setItemId] = useState(null);
  const [bancoNome, setBancoNome] = useState(null);
  const [contasBanco, setContasBanco] = useState([]);
  const [contasSistema, setContasSistema] = useState([]);
  const [contaBancoSel, setContaBancoSel] = useState(null);
  const [contaSistemaSel, setContaSistemaSel] = useState(null);
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const { access_token } = await api.connectToken();
        const sandbox = __DEV__ ? '&sandbox=1' : '';
        setUrlWidget(`${BASE_URL}/conectar-banco?connect_token=${access_token}${sandbox}`);
        setEtapa('widget');
      } catch (e) {
        Alert.alert('Erro', e.message, [{ text: 'OK', onPress: () => navigation.goBack() }]);
      }
    })();
  }, []);

  async function aoReceberMensagem(evento) {
    let dados;
    try {
      dados = JSON.parse(evento.nativeEvent.data);
    } catch {
      return;
    }
    if (dados.event === 'success') {
      setItemId(dados.itemId);
      setBancoNome(dados.connector || 'Banco conectado');
      try {
        const [banco, sistema] = await Promise.all([
          api.contasPluggy(dados.itemId),
          api.contas(),
        ]);
        setContasBanco(banco);
        setContasSistema(sistema.items);
        if (banco.length === 1) setContaBancoSel(banco[0].id);
        setEtapa('vincular');
      } catch (e) {
        Alert.alert('Erro', e.message);
      }
    } else if (dados.event === 'error') {
      Alert.alert('Conexão falhou', dados.message || 'Tente novamente.');
    }
  }

  async function vincular() {
    if (!contaBancoSel || !contaSistemaSel) {
      Alert.alert('Atenção', 'Escolha a conta do banco e a conta do sistema.');
      return;
    }
    setSalvando(true);
    try {
      await api.criarConexaoBancaria({
        conta_id: contaSistemaSel,
        pluggy_item_id: itemId,
        pluggy_account_id: contaBancoSel,
        banco_nome: bancoNome,
      });
      Alert.alert('Tudo certo! 🏦', 'Banco conectado. Use "Sincronizar" para importar o extrato.', [
        { text: 'OK', onPress: () => navigation.goBack() },
      ]);
    } catch (e) {
      Alert.alert('Erro', e.message);
    } finally {
      setSalvando(false);
    }
  }

  if (etapa === 'carregando') {
    return (
      <View style={styles.centro}>
        <ActivityIndicator size="large" color={colors.accent} />
        <Text style={styles.aviso}>Gerando conexão segura…</Text>
      </View>
    );
  }

  if (etapa === 'widget') {
    return (
      <WebView
        source={{ uri: urlWidget }}
        onMessage={aoReceberMensagem}
        startInLoadingState
        renderLoading={() => (
          <View style={styles.centro}>
            <ActivityIndicator size="large" color={colors.accent} />
          </View>
        )}
      />
    );
  }

  // etapa === 'vincular'
  return (
    <ScrollView style={styles.container}>
      <Text style={styles.titulo}>✅ {bancoNome}</Text>
      <Text style={styles.subtitulo}>
        Agora vincule a conta do banco a uma conta do sistema:
      </Text>

      <Text style={styles.label}>Conta no banco</Text>
      {contasBanco.map((c) => (
        <TouchableOpacity
          key={c.id}
          style={[styles.opcao, contaBancoSel === c.id && styles.opcaoAtiva]}
          onPress={() => setContaBancoSel(c.id)}
        >
          <Text style={[styles.opcaoTexto, contaBancoSel === c.id && styles.opcaoTextoAtivo]}>
            {c.nome}{c.numero ? ` · ${c.numero}` : ''}
          </Text>
        </TouchableOpacity>
      ))}

      <Text style={styles.label}>Conta no sistema</Text>
      {contasSistema.map((c) => (
        <TouchableOpacity
          key={c.id}
          style={[styles.opcao, contaSistemaSel === c.id && styles.opcaoAtiva]}
          onPress={() => setContaSistemaSel(c.id)}
        >
          <Text style={[styles.opcaoTexto, contaSistemaSel === c.id && styles.opcaoTextoAtivo]}>
            {c.nome} ({c.tipo})
          </Text>
        </TouchableOpacity>
      ))}

      <TouchableOpacity style={styles.botao} onPress={vincular} disabled={salvando}>
        {salvando
          ? <ActivityIndicator color="#fff" />
          : <Text style={styles.botaoTexto}>Vincular contas</Text>}
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  centro: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.bg },
  aviso: { color: colors.textMuted, marginTop: spacing.md },
  container: { flex: 1, backgroundColor: colors.bg, padding: spacing.md },
  titulo: { fontSize: 20, fontWeight: '700', color: colors.text },
  subtitulo: { color: colors.textMuted, marginTop: spacing.xs, marginBottom: spacing.md },
  label: { fontWeight: '600', color: colors.text, marginTop: spacing.md, marginBottom: spacing.sm },
  opcao: {
    backgroundColor: colors.card, borderWidth: 1, borderColor: colors.border,
    borderRadius: 10, padding: spacing.md, marginBottom: spacing.sm,
  },
  opcaoAtiva: { borderColor: colors.accent, backgroundColor: '#EFF6FF' },
  opcaoTexto: { color: colors.text },
  opcaoTextoAtivo: { color: colors.accent, fontWeight: '600' },
  botao: {
    backgroundColor: colors.accent, borderRadius: 10, padding: spacing.md,
    alignItems: 'center', marginTop: spacing.lg, marginBottom: spacing.xl,
  },
  botaoTexto: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
