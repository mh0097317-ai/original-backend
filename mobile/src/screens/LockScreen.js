import React, { useEffect, useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { autenticarBiometria } from '../biometria';
import { colors, spacing } from '../theme';

export default function LockScreen({ aoDesbloquear }) {
  const [falhou, setFalhou] = useState(false);

  async function tentar() {
    setFalhou(false);
    const ok = await autenticarBiometria();
    if (ok) aoDesbloquear();
    else setFalhou(true);
  }

  // Dispara o Face ID automaticamente ao abrir
  useEffect(() => {
    tentar();
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.icone}>🔒</Text>
      <Text style={styles.titulo}>Fluxo de Caixa</Text>
      <Text style={styles.subtitulo}>Desbloqueie com Face ID ou digital</Text>

      {falhou && (
        <TouchableOpacity style={styles.botao} onPress={tentar}>
          <Text style={styles.botaoTexto}>Tentar novamente</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1, backgroundColor: colors.primary,
    alignItems: 'center', justifyContent: 'center', padding: spacing.lg,
  },
  icone: { fontSize: 56, marginBottom: spacing.md },
  titulo: { color: '#fff', fontSize: 24, fontWeight: '700' },
  subtitulo: { color: '#94A3B8', marginTop: spacing.sm },
  botao: {
    marginTop: spacing.xl, backgroundColor: colors.accent,
    borderRadius: 10, paddingVertical: spacing.md, paddingHorizontal: spacing.xl,
  },
  botaoTexto: { color: '#fff', fontWeight: '600', fontSize: 16 },
});
