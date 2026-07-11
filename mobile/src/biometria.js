// Desbloqueio por biometria (Face ID / digital).
// Regra: pede autenticação UMA vez, ao abrir o app. Nunca por aba.
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as LocalAuthentication from 'expo-local-authentication';

const CHAVE = '@fluxocaixa/biometria';

export async function biometriaDisponivel() {
  const temHardware = await LocalAuthentication.hasHardwareAsync();
  const cadastrada = await LocalAuthentication.isEnrolledAsync();
  return temHardware && cadastrada;
}

export async function biometriaAtiva() {
  return (await AsyncStorage.getItem(CHAVE)) === '1';
}

export async function definirBiometria(ativa) {
  if (ativa) await AsyncStorage.setItem(CHAVE, '1');
  else await AsyncStorage.removeItem(CHAVE);
}

export async function autenticarBiometria() {
  const r = await LocalAuthentication.authenticateAsync({
    promptMessage: 'Desbloqueie o Fluxo de Caixa',
    cancelLabel: 'Cancelar',
  });
  return r.success;
}
