import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, AppState, StyleSheet, Text, View } from "react-native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";

import CalendarScreen from "../screens/CalendarScreen";
import LoginScreen from "../screens/LoginScreen";
import PermissionGateScreen from "../screens/PermissionGateScreen";
import SignupScreen from "../screens/SignupScreen";
import { clearTokens, hasStoredSession, restoreStoredSession } from "../services/api";
import { useAppMessages } from "../services/appMessages";
import { getAppEntryPermissionStatus } from "../services/workSession";
import { colors, typography } from "../theme";
import { RootStackParamList } from "./types";

const Stack = createNativeStackNavigator<RootStackParamList>();

export default function RootNavigator() {
  const { message } = useAppMessages();
  const [permissionsResolved, setPermissionsResolved] = useState(false);
  const [permissionsGranted, setPermissionsGranted] = useState(false);
  const [bootReady, setBootReady] = useState(false);
  const [initialRoute, setInitialRoute] =
    useState<keyof RootStackParamList>("Login");
  const [calendarParams, setCalendarParams] =
    useState<RootStackParamList["Calendar"]>();

  const resolvePermissions = useCallback(async () => {
    const status = await getAppEntryPermissionStatus();
    setPermissionsGranted(status.allGranted);
    setPermissionsResolved(true);
    return status.allGranted;
  }, []);

  useEffect(() => {
    void resolvePermissions();
  }, [resolvePermissions]);

  useEffect(() => {
    const subscription = AppState.addEventListener("change", (nextState) => {
      if (nextState !== "active") {
        return;
      }

      void (async () => {
        const granted = await resolvePermissions();
        if (!granted) {
          setBootReady(false);
          setInitialRoute("Login");
          setCalendarParams(undefined);
        }
      })();
    });

    return () => {
      subscription.remove();
    };
  }, [resolvePermissions]);

  useEffect(() => {
    if (!permissionsGranted) {
      return;
    }

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
      if (!mounted) {
        return;
      }

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
  }, [permissionsGranted]);

  if (!permissionsResolved) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={colors.accentBlue} />
        <Text style={styles.loadingText}>{message("root_permission_loading_text", "권한 상태 확인 중...")}</Text>
      </View>
    );
  }

  if (!permissionsGranted) {
    return (
      <PermissionGateScreen
        onGranted={() => {
          setPermissionsGranted(true);
          setBootReady(false);
        }}
      />
    );
  }

  if (!bootReady) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={colors.accentBlue} />
        <Text style={styles.loadingText}>{message("root_login_loading_text", "로그인 상태 확인 중...")}</Text>
      </View>
    );
  }

  return (
    <Stack.Navigator
      initialRouteName={initialRoute}
      screenOptions={{ headerShown: false }}
    >
      <Stack.Screen name="Login" component={LoginScreen} />
      <Stack.Screen name="Signup" component={SignupScreen} />
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
