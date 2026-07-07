import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  KeyboardAvoidingView, Platform, ActivityIndicator,
} from 'react-native';
import { useAuth } from '../context/AuthContext';
import { colors, spacing } from '../theme';

export default function LoginScreen() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [erro, setErro] = useState(null);
  const [enviando, setEnviando] = useState(false);

  async function entrar() {
    if (!email || !senha) {
      setErro('Informe e-mail e senha');
      return;
    }
    setErro(null);
    setEnviando(true);
    try {
      await login(email.trim(), senha);
    } catch (e) {
      setErro(e.message || 'Falha no login');
    } finally {
      setEnviando(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <View style={styles.logo}>
        <Text style={styles.logoIcon}>💰</Text>
        <Text style={styles.titulo}>Fluxo de Caixa</Text>
        <Text style={styles.subtitulo}>Distribuidora</Text>
      </View>

      <View style={styles.form}>
        <TextInput
          style={styles.input}
          placeholder="E-mail"
          placeholderTextColor={colors.textMuted}
          autoCapitalize="none"
          keyboardType="email-address"
          value={email}
          onChangeText={setEmail}
        />
        <TextInput
          style={styles.input}
          placeholder="Senha"
          placeholderTextColor={colors.textMuted}
          secureTextEntry
          value={senha}
          onChangeText={setSenha}
        />

        {erro && <Text style={styles.erro}>{erro}</Text>}

        <TouchableOpacity style={styles.botao} onPress={entrar} disabled={enviando}>
          {enviando
            ? <ActivityIndicator color="#fff" />
            : <Text style={styles.botaoTexto}>Entrar</Text>}
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.primary, justifyContent: 'center', padding: spacing.lg },
  logo: { alignItems: 'center', marginBottom: spacing.xl },
  logoIcon: { fontSize: 56, marginBottom: spacing.sm },
  titulo: { color: '#fff', fontSize: 28, fontWeight: '700' },
  subtitulo: { color: '#94A3B8', fontSize: 16, marginTop: spacing.xs },
  form: { backgroundColor: colors.card, borderRadius: 16, padding: spacing.lg },
  input: {
    borderWidth: 1, borderColor: colors.border, borderRadius: 10,
    padding: spacing.md, marginBottom: spacing.md, fontSize: 16, color: colors.text,
  },
  erro: { color: colors.danger, marginBottom: spacing.md, textAlign: 'center' },
  botao: {
    backgroundColor: colors.accent, borderRadius: 10,
    padding: spacing.md, alignItems: 'center',
  },
  botaoTexto: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
