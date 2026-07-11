import React, { useEffect, useState } from 'react';
import { Text, View, ActivityIndicator, StyleSheet } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';

import { AuthProvider, useAuth } from './src/context/AuthContext';
import LoginScreen from './src/screens/LoginScreen';
import DashboardScreen from './src/screens/DashboardScreen';
import MovimentosScreen from './src/screens/MovimentosScreen';
import NovoMovimentoScreen from './src/screens/NovoMovimentoScreen';
import ContasScreen from './src/screens/ContasScreen';
import ConciliacaoScreen from './src/screens/ConciliacaoScreen';
import ChatScreen from './src/screens/ChatScreen';
import LockScreen from './src/screens/LockScreen';
import { biometriaAtiva, biometriaDisponivel } from './src/biometria';
import { colors } from './src/theme';

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

function TabIcon({ emoji, focused }) {
  return <Text style={{ fontSize: 20, opacity: focused ? 1 : 0.45 }}>{emoji}</Text>;
}

function Tabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: colors.primary },
        headerTintColor: '#fff',
        tabBarActiveTintColor: colors.accent,
      }}
    >
      <Tab.Screen
        name="Dashboard"
        component={DashboardScreen}
        options={{
          title: 'Visão Geral',
          tabBarIcon: (p) => <TabIcon emoji="📊" {...p} />,
        }}
      />
      <Tab.Screen
        name="Movimentos"
        component={MovimentosScreen}
        options={{
          title: 'Movimentos',
          tabBarIcon: (p) => <TabIcon emoji="💸" {...p} />,
        }}
      />
      <Tab.Screen
        name="Contas"
        component={ContasScreen}
        options={{
          title: 'Pagar / Receber',
          tabBarIcon: (p) => <TabIcon emoji="📅" {...p} />,
        }}
      />
      <Tab.Screen
        name="Conciliacao"
        component={ConciliacaoScreen}
        options={{
          title: 'Conciliação',
          tabBarIcon: (p) => <TabIcon emoji="🏦" {...p} />,
        }}
      />
      <Tab.Screen
        name="Chat"
        component={ChatScreen}
        options={{
          title: 'Equipe',
          tabBarIcon: (p) => <TabIcon emoji="💬" {...p} />,
        }}
      />
    </Tab.Navigator>
  );
}

function Rotas() {
  const { usuario, carregando } = useAuth();
  // Bloqueio biométrico: exigido UMA vez, na abertura do app.
  // Depois de desbloqueado, nenhuma aba pede de novo.
  const [precisaBio, setPrecisaBio] = useState(null); // null = verificando
  const [desbloqueado, setDesbloqueado] = useState(false);

  useEffect(() => {
    (async () => {
      const exigir = (await biometriaAtiva()) && (await biometriaDisponivel());
      setPrecisaBio(exigir);
    })();
  }, []);

  if (carregando || precisaBio === null) {
    return (
      <View style={styles.splash}>
        <ActivityIndicator size="large" color="#fff" />
      </View>
    );
  }

  if (usuario && precisaBio && !desbloqueado) {
    return <LockScreen aoDesbloquear={() => setDesbloqueado(true)} />;
  }

  return (
    <Stack.Navigator>
      {usuario ? (
        <>
          <Stack.Screen name="Home" component={Tabs} options={{ headerShown: false }} />
          <Stack.Screen
            name="NovoMovimento"
            component={NovoMovimentoScreen}
            options={{
              title: 'Novo movimento',
              headerStyle: { backgroundColor: colors.primary },
              headerTintColor: '#fff',
            }}
          />
        </>
      ) : (
        <Stack.Screen name="Login" component={LoginScreen} options={{ headerShown: false }} />
      )}
    </Stack.Navigator>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <NavigationContainer>
        <StatusBar style="light" />
        <Rotas />
      </NavigationContainer>
    </AuthProvider>
  );
}

const styles = StyleSheet.create({
  splash: {
    flex: 1, backgroundColor: colors.primary,
    alignItems: 'center', justifyContent: 'center',
  },
});
