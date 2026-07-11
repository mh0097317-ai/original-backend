import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  View, Text, TextInput, StyleSheet, FlatList, TouchableOpacity,
  Alert, KeyboardAvoidingView, Platform,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { colors, spacing } from '../theme';

function horaDe(iso) {
  const d = new Date(iso + (iso.endsWith('Z') ? '' : 'Z'));
  return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

export default function ChatScreen() {
  const { usuario } = useAuth();
  const [mensagens, setMensagens] = useState([]);
  const [texto, setTexto] = useState('');
  const [gravando, setGravando] = useState(false);
  const [tocandoId, setTocandoId] = useState(null);
  const gravacaoRef = useRef(null);
  const somRef = useRef(null);
  const pollRef = useRef(null);

  const carregar = useCallback(async () => {
    try {
      const data = await api.mensagensChat();
      setMensagens(data.items); // já vem mais recente primeiro (lista invertida)
    } catch {
      // silencioso no polling — erro pontual não deve gerar alerta em loop
    }
  }, []);

  // Carrega ao focar e atualiza a cada 4s enquanto a aba está aberta
  useFocusEffect(
    useCallback(() => {
      carregar();
      pollRef.current = setInterval(carregar, 4000);
      return () => {
        clearInterval(pollRef.current);
        if (somRef.current) {
          somRef.current.unloadAsync();
          somRef.current = null;
        }
      };
    }, [carregar])
  );

  async function enviarTexto() {
    const conteudo = texto.trim();
    if (!conteudo) return;
    setTexto('');
    try {
      await api.enviarMensagemTexto(conteudo);
      await carregar();
    } catch (e) {
      Alert.alert('Erro', e.message);
      setTexto(conteudo);
    }
  }

  async function iniciarGravacao() {
    try {
      const perm = await Audio.requestPermissionsAsync();
      if (!perm.granted) {
        Alert.alert('Microfone', 'Permita o acesso ao microfone para mandar áudio.');
        return;
      }
      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      gravacaoRef.current = recording;
      setGravando(true);
    } catch (e) {
      Alert.alert('Erro', 'Não foi possível iniciar a gravação.');
    }
  }

  async function pararEEnviar() {
    const recording = gravacaoRef.current;
    if (!recording) return;
    setGravando(false);
    gravacaoRef.current = null;
    try {
      await recording.stopAndUnloadAsync();
      const status = await recording.getStatusAsync();
      const duracao = Math.max(1, Math.round((status.durationMillis || 0) / 1000));
      const uri = recording.getURI();
      const base64 = await FileSystem.readAsStringAsync(uri, {
        encoding: FileSystem.EncodingType.Base64,
      });
      await api.enviarMensagemAudio(base64, duracao);
      await carregar();
    } catch (e) {
      Alert.alert('Erro', e.message || 'Falha ao enviar o áudio.');
    }
  }

  async function tocarAudio(item) {
    try {
      if (somRef.current) {
        await somRef.current.unloadAsync();
        somRef.current = null;
        if (tocandoId === item.id) {
          setTocandoId(null);
          return;
        }
      }
      await Audio.setAudioModeAsync({ allowsRecordingIOS: false, playsInSilentModeIOS: true });
      const arquivo = `${FileSystem.cacheDirectory}chat-${item.id}.m4a`;
      await FileSystem.writeAsStringAsync(arquivo, item.conteudo, {
        encoding: FileSystem.EncodingType.Base64,
      });
      const { sound } = await Audio.Sound.createAsync({ uri: arquivo }, { shouldPlay: true });
      somRef.current = sound;
      setTocandoId(item.id);
      sound.setOnPlaybackStatusUpdate((s) => {
        if (s.didJustFinish) {
          setTocandoId(null);
          sound.unloadAsync();
          somRef.current = null;
        }
      });
    } catch (e) {
      Alert.alert('Erro', 'Não foi possível tocar o áudio.');
    }
  }

  function confirmarApagar(item) {
    const podeApagar = item.usuario_id === usuario.id || usuario.role === 'admin';
    if (!podeApagar) return;
    Alert.alert('Apagar mensagem', 'Essa mensagem será removida para todos.', [
      { text: 'Voltar', style: 'cancel' },
      {
        text: 'Apagar',
        style: 'destructive',
        onPress: async () => {
          try {
            await api.apagarMensagem(item.id);
            await carregar();
          } catch (e) {
            Alert.alert('Erro', e.message);
          }
        },
      },
    ]);
  }

  function renderItem({ item }) {
    const minha = item.usuario_id === usuario.id;
    return (
      <TouchableOpacity
        activeOpacity={0.8}
        onLongPress={() => confirmarApagar(item)}
        style={[styles.balao, minha ? styles.balaoMeu : styles.balaoOutro]}
      >
        {!minha && <Text style={styles.autor}>{item.usuario_nome}</Text>}
        {item.tipo === 'audio' ? (
          <TouchableOpacity style={styles.audio} onPress={() => tocarAudio(item)}>
            <Text style={styles.audioIcone}>{tocandoId === item.id ? '⏸' : '▶️'}</Text>
            <View style={styles.audioBarra} />
            <Text style={[styles.audioDuracao, minha && { color: '#DBEAFE' }]}>
              {item.duracao_seg || 0}s
            </Text>
          </TouchableOpacity>
        ) : (
          <Text style={[styles.textoMsg, minha && styles.textoMsgMeu]}>{item.conteudo}</Text>
        )}
        <Text style={[styles.hora, minha && { color: '#BFDBFE' }]}>{horaDe(item.criado_em)}</Text>
      </TouchableOpacity>
    );
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={90}
    >
      <FlatList
        inverted
        data={mensagens}
        keyExtractor={(item) => item.id}
        renderItem={renderItem}
        contentContainerStyle={{ padding: spacing.md }}
        ListEmptyComponent={
          <Text style={styles.vazio}>Sem mensagens ainda. Diga oi para a equipe! 👋</Text>
        }
      />

      <View style={styles.rodape}>
        <TextInput
          style={styles.input}
          placeholder={gravando ? 'Gravando áudio…' : 'Mensagem'}
          placeholderTextColor={gravando ? colors.danger : colors.textMuted}
          value={texto}
          onChangeText={setTexto}
          editable={!gravando}
          multiline
        />
        {texto.trim() ? (
          <TouchableOpacity style={styles.botaoEnviar} onPress={enviarTexto}>
            <Text style={styles.botaoIcone}>➤</Text>
          </TouchableOpacity>
        ) : (
          <TouchableOpacity
            style={[styles.botaoEnviar, gravando && styles.botaoGravando]}
            onPressIn={iniciarGravacao}
            onPressOut={pararEEnviar}
          >
            <Text style={styles.botaoIcone}>🎤</Text>
          </TouchableOpacity>
        )}
      </View>
      {gravando && (
        <Text style={styles.dicaGravacao}>Solte para enviar o áudio</Text>
      )}
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  balao: {
    maxWidth: '80%', borderRadius: 14, padding: spacing.md,
    marginBottom: spacing.sm,
  },
  balaoMeu: { alignSelf: 'flex-end', backgroundColor: colors.accent, borderBottomRightRadius: 4 },
  balaoOutro: { alignSelf: 'flex-start', backgroundColor: colors.card, borderBottomLeftRadius: 4 },
  autor: { fontSize: 12, fontWeight: '700', color: colors.accent, marginBottom: 2 },
  textoMsg: { color: colors.text, fontSize: 15 },
  textoMsgMeu: { color: '#fff' },
  audio: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, minWidth: 140 },
  audioIcone: { fontSize: 18 },
  audioBarra: { flex: 1, height: 3, backgroundColor: '#94A3B8', borderRadius: 2 },
  audioDuracao: { fontSize: 12, color: colors.textMuted },
  hora: { fontSize: 10, color: colors.textMuted, alignSelf: 'flex-end', marginTop: 4 },
  vazio: { textAlign: 'center', color: colors.textMuted, transform: [{ scaleY: -1 }] },
  rodape: {
    flexDirection: 'row', alignItems: 'flex-end', gap: spacing.sm,
    padding: spacing.sm, backgroundColor: colors.card,
    borderTopWidth: 1, borderTopColor: colors.border,
  },
  input: {
    flex: 1, borderWidth: 1, borderColor: colors.border, borderRadius: 20,
    paddingHorizontal: spacing.md, paddingVertical: spacing.sm,
    fontSize: 15, color: colors.text, maxHeight: 100, backgroundColor: colors.bg,
  },
  botaoEnviar: {
    width: 44, height: 44, borderRadius: 22, backgroundColor: colors.accent,
    alignItems: 'center', justifyContent: 'center',
  },
  botaoGravando: { backgroundColor: colors.danger, transform: [{ scale: 1.15 }] },
  botaoIcone: { color: '#fff', fontSize: 18 },
  dicaGravacao: {
    textAlign: 'center', color: colors.danger, fontSize: 12,
    paddingBottom: spacing.sm, backgroundColor: colors.card,
  },
});
