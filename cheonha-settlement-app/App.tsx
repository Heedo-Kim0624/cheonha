import React from "react";
import { StatusBar } from "expo-status-bar";
import { NavigationContainer } from "@react-navigation/native";
import { Alert, Linking } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import RootNavigator from "./src/navigation/RootNavigator";
import { AppMessagesProvider, useAppMessages } from "./src/services/appMessages";
import { installAppAlertTransform } from "./src/services/alertMessageTransform";
import {
  getClientAppBuildNumber,
  getClientAppVersionName,
} from "./src/services/api";

const PLAY_STORE_FALLBACK_URL =
  "https://play.google.com/store/apps/details?id=com.cheonha.settlement";

function parseVersionCode(value: string | undefined) {
  const parsed = Number.parseInt(String(value || "0").trim(), 10);
  return Number.isFinite(parsed) ? parsed : 0;
}

function AppContent() {
  const { messages, message } = useAppMessages();
  const updatePromptKeyRef = React.useRef("");

  React.useEffect(() => {
    installAppAlertTransform(() => messages);
  }, [messages]);

  React.useEffect(() => {
    const currentVersionCode = getClientAppBuildNumber();
    const latestVersionCode = parseVersionCode(
      messages.app_update_latest_version_code
    );
    const minimumVersionCode = parseVersionCode(
      messages.app_update_min_version_code
    );
    const shouldPrompt =
      currentVersionCode > 0 &&
      (latestVersionCode > currentVersionCode ||
        minimumVersionCode > currentVersionCode);

    if (!shouldPrompt) {
      return;
    }

    const promptKey = `${currentVersionCode}:${latestVersionCode}:${minimumVersionCode}`;
    if (updatePromptKeyRef.current === promptKey) {
      return;
    }
    updatePromptKeyRef.current = promptKey;

    const forceUpdate = minimumVersionCode > currentVersionCode;
    const latestVersionName =
      String(messages.app_update_latest_version_name || "").trim() ||
      String(latestVersionCode || "");
    const playStoreUrl =
      String(messages.app_update_play_store_url || "").trim() ||
      PLAY_STORE_FALLBACK_URL;
    const openStore = async () => {
      try {
        await Linking.openURL(playStoreUrl);
      } catch {
        await Linking.openURL(PLAY_STORE_FALLBACK_URL);
      }
    };

    const buttons = forceUpdate
      ? [
          {
            text: message("app_update_button_label", "업데이트"),
            onPress: () => {
              void openStore();
            },
          },
        ]
      : [
          {
            text: message("app_update_later_label", "나중에"),
            style: "cancel" as const,
          },
          {
            text: message("app_update_button_label", "업데이트"),
            onPress: () => {
              void openStore();
            },
          },
        ];

    Alert.alert(
      message("app_update_title", "앱 업데이트 안내"),
      message(
        "app_update_body_template",
        "새 버전({version})이 준비되었습니다. 안정적인 이용을 위해 업데이트해 주세요.",
        {
          version: latestVersionName,
          current_version: getClientAppVersionName(),
        }
      ),
      buttons,
      { cancelable: !forceUpdate }
    );
  }, [message, messages]);

  return (
    <NavigationContainer>
      <StatusBar style="dark" />
      <RootNavigator />
    </NavigationContainer>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <AppMessagesProvider>
        <AppContent />
      </AppMessagesProvider>
    </SafeAreaProvider>
  );
}
