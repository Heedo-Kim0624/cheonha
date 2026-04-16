import React, { useEffect, useState } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { RootStackParamList } from "./types";
import LoginScreen from "../screens/LoginScreen";
import CalendarScreen from "../screens/CalendarScreen";
import {
  clearTokens,
  hasStoredSession,
  restoreStoredSession,
} from "../services/api";
import { colors, typography } from "../theme";

const Stack = createNativeStackNavigator<RootStackParamList>();

export default function RootNavigator() {
  const [bootReady, setBootReady] = useState(false);
  const [initialRoute, setInitialRoute] =
    useState<keyof RootStackParamList>("Login");
  const [calendarParams, setCalendarParams] =
    useState<RootStackParamList["Calendar"]>();

  useEffect(() => {
    let mounted = true;

    (async () => {
      const stored = await hasStoredSession();
      if (!stored) {
        if (mounted) {
          setInitialRoute("Login");
          setBootReady(true);
        }
        return;
      }

      const profileRes = await restoreStoredSession();
      if (!mounted) return;

      if (profileRes.data) {
        setInitialRoute("Calendar");
        setCalendarParams({
          profileName: profileRes.data.name,
          profileTeamCode: profileRes.data.team_code,
          requiresPasswordChange: profileRes.data.requires_password_change,
        });
      } else {
        await clearTokens();
        setInitialRoute("Login");
      }

      setBootReady(true);
    })();

    return () => {
      mounted = false;
    };
  }, []);

  if (!bootReady) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={colors.accentBlue} />
        <Text style={styles.loadingText}>로그인 상태 확인 중...</Text>
      </View>
    );
  }

  return (
    <Stack.Navigator
      initialRouteName={initialRoute}
      screenOptions={{ headerShown: false }}
    >
      <Stack.Screen name="Login" component={LoginScreen} />
      <Stack.Screen
        name="Calendar"
        component={CalendarScreen}
        initialParams={calendarParams}
      />
    </Stack.Navigator>
  );
}

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
    backgroundColor: colors.bgPrimary,
  },
  loadingText: {
    ...typography.bodySmall,
    color: colors.textSecondary,
  },
});
