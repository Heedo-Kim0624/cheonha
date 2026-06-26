import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  AppState,
  Linking,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";

import {
  getAppEntryPermissionStatus,
  requestAppEntryPermissions,
  type AppPermissionItem,
} from "../services/workSession";
import { useAppMessages } from "../services/appMessages";
import { colors, typography } from "../theme";

interface PermissionGateScreenProps {
  onGranted: () => void;
}

function PermissionRow({
  item,
  message,
}: {
  item: AppPermissionItem;
  message: (key: string, fallback: string) => string;
}) {
  const granted = item.granted;
  const label = message(`permission_${item.key}_label`, item.label);
  const description = message(`permission_${item.key}_description`, item.description);
  return (
    <View style={styles.permissionRow}>
      <View
        style={[
          styles.permissionIcon,
          granted ? styles.permissionIconGranted : styles.permissionIconMissing,
        ]}
      >
        <Ionicons
          name={granted ? "checkmark" : "close"}
          size={18}
          color={colors.textInverse}
        />
      </View>
      <View style={styles.permissionTextBlock}>
        <View style={styles.permissionHeader}>
          <Text style={styles.permissionLabel}>{label}</Text>
          <View
            style={[
              styles.permissionModeChip,
              item.requiredMode === "always"
                ? styles.permissionModeAlways
                : styles.permissionModeAllow,
            ]}
          >
            <Text style={styles.permissionModeText}>
              {item.requiredMode === "always"
                ? message("permission_mode_always_label", "항상 허용")
                : message("permission_mode_allow_label", "허용")}
            </Text>
          </View>
        </View>
        <Text style={styles.permissionDescription}>{description}</Text>
      </View>
    </View>
  );
}

export default function PermissionGateScreen({
  onGranted,
}: PermissionGateScreenProps) {
  const { message } = useAppMessages();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [items, setItems] = useState<AppPermissionItem[]>([]);

  const refreshStatus = useCallback(async () => {
    const status = await getAppEntryPermissionStatus();
    setItems(status.items);
    if (status.allGranted) {
      onGranted();
    }
  }, [onGranted]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      await refreshStatus();
      if (mounted) {
        setLoading(false);
      }
    })();

    const subscription = AppState.addEventListener("change", (nextState) => {
      if (nextState === "active") {
        void refreshStatus();
      }
    });

    return () => {
      mounted = false;
      subscription.remove();
    };
  }, [refreshStatus]);

  const handleRequestPermissions = useCallback(async () => {
    setSubmitting(true);
    try {
      const status = await requestAppEntryPermissions();
      setItems(status.items);

      if (status.allGranted) {
        onGranted();
        return;
      }

      Alert.alert(
        message("permission_missing_title", "권한이 아직 부족합니다"),
        message(
          "permission_missing_body",
          "앱을 사용하려면 모든 필수 권한이 필요합니다.\n위치는 반드시 '항상 허용'으로 설정해야 합니다."
        ),
        [
          { text: message("generic_close_label", "닫기"), style: "cancel" },
          {
            text: message("location_permission_settings_label", "설정 열기"),
            onPress: () => {
              void Linking.openSettings();
            },
          },
        ]
      );
    } finally {
      setSubmitting(false);
    }
  }, [message, onGranted]);

  const handleOpenSettings = useCallback(() => {
    void Linking.openSettings();
  }, []);

  if (Platform.OS !== "android") {
    return null;
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.heroCard}>
          <View style={styles.heroIcon}>
            <Ionicons
              name="shield-checkmark-outline"
              size={34}
              color={colors.textInverse}
            />
          </View>
          <Text style={styles.title}>{message("permission_gate_title", "권한을 허용해주세요")}</Text>
          <Text style={styles.description}>
            {message("permission_gate_description", "위치, 블루투스, 알림 권한이 모두 있어야만 앱에 들어갈 수 있습니다.")}
          </Text>
          <Text style={styles.description}>
            {message("permission_gate_location_prefix", "위치는 반드시 ")}
            <Text style={styles.descriptionStrong}>{message("permission_mode_always_label", "항상 허용")}</Text>
            {message("permission_gate_location_suffix", "으로 설정해야 합니다.")}
          </Text>
        </View>

        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>{message("permission_status_section_title", "필수 권한 상태")}</Text>
          {loading ? (
            <View style={styles.loaderRow}>
              <ActivityIndicator color={colors.accentBlue} />
              <Text style={styles.loaderText}>{message("root_permission_loading_text", "권한 상태 확인 중...")}</Text>
            </View>
          ) : (
            <View style={styles.permissionList}>
              {items.map((item) => (
                <PermissionRow key={item.key} item={item} message={message} />
              ))}
            </View>
          )}
        </View>

        <View style={styles.buttonStack}>
          <Pressable
            style={[
              styles.primaryButton,
              submitting && styles.buttonDisabled,
            ]}
            onPress={handleRequestPermissions}
            disabled={submitting}
          >
            {submitting ? (
              <ActivityIndicator color={colors.textInverse} />
            ) : (
              <Text style={styles.primaryButtonText}>{message("permission_request_button_label", "권한 허용하기")}</Text>
            )}
          </Pressable>

          <Pressable style={styles.secondaryButton} onPress={handleOpenSettings}>
            <Text style={styles.secondaryButtonText}>{message("location_permission_settings_label", "앱 설정 열기")}</Text>
          </Pressable>

          <Pressable style={styles.tertiaryButton} onPress={refreshStatus}>
            <Text style={styles.tertiaryButtonText}>{message("permission_recheck_button_label", "권한 다시 확인")}</Text>
          </Pressable>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bgPrimary,
  },
  content: {
    padding: 20,
    gap: 16,
  },
  heroCard: {
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderLight,
    backgroundColor: colors.bgPrimary,
    padding: 20,
    gap: 10,
  },
  heroIcon: {
    width: 54,
    height: 54,
    borderRadius: 12,
    backgroundColor: colors.accentBlue,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 4,
  },
  title: {
    ...typography.screenTitle,
    color: colors.textPrimary,
  },
  description: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    lineHeight: 22,
  },
  descriptionStrong: {
    color: colors.textPrimary,
    fontWeight: "700",
  },
  sectionCard: {
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderLight,
    backgroundColor: colors.bgPrimary,
    padding: 20,
    gap: 12,
  },
  sectionTitle: {
    ...typography.sectionTitle,
    color: colors.textPrimary,
  },
  loaderRow: {
    minHeight: 72,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
  },
  loaderText: {
    ...typography.bodySmall,
    color: colors.textSecondary,
  },
  permissionList: {
    gap: 12,
  },
  permissionRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 12,
    borderRadius: 10,
    backgroundColor: colors.bgSecondary,
    padding: 14,
  },
  permissionIcon: {
    width: 30,
    height: 30,
    borderRadius: 999,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 2,
  },
  permissionIconGranted: {
    backgroundColor: colors.successGreen,
  },
  permissionIconMissing: {
    backgroundColor: colors.sundayRed,
  },
  permissionTextBlock: {
    flex: 1,
    gap: 4,
  },
  permissionHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
  },
  permissionLabel: {
    ...typography.body,
    color: colors.textPrimary,
    fontWeight: "700",
    flex: 1,
  },
  permissionModeChip: {
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  permissionModeAlways: {
    backgroundColor: "#FEE2E2",
  },
  permissionModeAllow: {
    backgroundColor: "#DBEAFE",
  },
  permissionModeText: {
    ...typography.captionSmall,
    color: colors.textPrimary,
  },
  permissionDescription: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    lineHeight: 20,
  },
  buttonStack: {
    gap: 10,
    paddingBottom: 24,
  },
  primaryButton: {
    minHeight: 52,
    borderRadius: 10,
    backgroundColor: colors.accentBlue,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 16,
  },
  primaryButtonText: {
    ...typography.body,
    color: colors.textInverse,
    fontWeight: "700",
  },
  secondaryButton: {
    minHeight: 52,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.borderLight,
    backgroundColor: colors.bgPrimary,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 16,
  },
  secondaryButtonText: {
    ...typography.body,
    color: colors.textPrimary,
    fontWeight: "600",
  },
  tertiaryButton: {
    minHeight: 44,
    alignItems: "center",
    justifyContent: "center",
  },
  tertiaryButtonText: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    textDecorationLine: "underline",
  },
  buttonDisabled: {
    opacity: 0.7,
  },
});
