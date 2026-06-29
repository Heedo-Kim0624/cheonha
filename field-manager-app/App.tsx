import 'react-native-gesture-handler'
import React, { useEffect, useState } from 'react'
import { ActivityIndicator, StyleSheet, View } from 'react-native'
import { NavigationContainer } from '@react-navigation/native'
import { createNativeStackNavigator } from '@react-navigation/native-stack'
import { StatusBar } from 'expo-status-bar'
import { SafeAreaProvider } from 'react-native-safe-area-context'
import { GestureHandlerRootView } from 'react-native-gesture-handler'

import LoginScreen from './src/screens/LoginScreen'
import MainScreen from './src/screens/MainScreen'
import SubscriptionRequestScreen from './src/screens/SubscriptionRequestScreen'
import SubscriptionReturnScreen from './src/screens/SubscriptionReturnScreen'
import ASRequestScreen from './src/screens/ASRequestScreen'
import RequestHistoryScreen from './src/screens/RequestHistoryScreen'
import { RootStackParamList } from './src/navigation/types'
import { hasStoredSession } from './src/services/api'
import { colors } from './src/theme'

const Stack = createNativeStackNavigator<RootStackParamList>()

export default function App() {
  const [bootstrapped, setBootstrapped] = useState(false)
  const [initialRouteName, setInitialRouteName] =
    useState<keyof RootStackParamList>('Login')

  useEffect(() => {
    let active = true

    ;(async () => {
      const hasSession = await hasStoredSession().catch(() => false)
      if (!active) {
        return
      }
      setInitialRouteName(hasSession ? 'Main' : 'Login')
      setBootstrapped(true)
    })()

    return () => {
      active = false
    }
  }, [])

  if (!bootstrapped) {
    return (
      <SafeAreaProvider>
        <GestureHandlerRootView style={styles.root}>
          <View style={styles.bootContainer}>
            <StatusBar style="dark" />
            <ActivityIndicator size="large" color={colors.primary} />
          </View>
        </GestureHandlerRootView>
      </SafeAreaProvider>
    )
  }

  return (
    <SafeAreaProvider>
      <GestureHandlerRootView style={styles.root}>
        <StatusBar style="dark" />
        <NavigationContainer>
          <Stack.Navigator
            initialRouteName={initialRouteName}
            screenOptions={{ headerShown: false }}
          >
            <Stack.Screen name="Login" component={LoginScreen} />
            <Stack.Screen name="Main" component={MainScreen} />
            <Stack.Screen name="SubscriptionRequest" component={SubscriptionRequestScreen} />
            <Stack.Screen name="SubscriptionReturn" component={SubscriptionReturnScreen} />
            <Stack.Screen name="ASRequest" component={ASRequestScreen} />
            <Stack.Screen name="RequestHistory" component={RequestHistoryScreen} />
          </Stack.Navigator>
        </NavigationContainer>
      </GestureHandlerRootView>
    </SafeAreaProvider>
  )
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  bootContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.bg,
  },
})
