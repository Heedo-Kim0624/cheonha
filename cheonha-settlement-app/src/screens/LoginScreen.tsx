import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Linking,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";

import TeamCodePicker from "../components/TeamCodePicker";
import { RootStackParamList } from "../navigation/types";
import {
  api,
  PRIVACY_POLICY_URL,
  saveTokens,
} from "../services/api";
import { useAppMessages } from "../services/appMessages";
import { colors, typography } from "../theme";

type Nav = NativeStackNavigationProp<RootStackParamList, "Login">;

export default function LoginScreen() {
  const navigation = useNavigation<Nav>();
  const [name, setName] = useState("");
  const [teamCode, setTeamCode] = useState("");
  const [password, setPassword] = useState("");
  const [showPicker, setShowPicker] = useState(false);
  const [loading, setLoading] = useState(false);
  const { message } = useAppMessages();

  const openPrivacyPolicy = async () => {
    try {
      await Linking.openURL(
        message("signup_privacy_policy_url", PRIVACY_POLICY_URL)
      );
    } catch {
      Alert.alert(
        message("generic_notice_title", "안내"),
        message(
          "privacy_open_failed_message",
          "개인정보처리방침 페이지를 열 수 없습니다."
        )
      );
    }
  };

  const handleLogin = async () => {
    if (!name.trim()) {
      Alert.alert(
        message("generic_notice_title", "안내"),
        message("login_name_required_message", "이름을 입력해 주세요.")
      );
      return;
    }
    if (!teamCode.trim()) {
      Alert.alert(
        message("generic_notice_title", "안내"),
        message("login_team_required_message", "조를 선택해 주세요.")
      );
      return;
    }
    if (password.length !== 4) {
      Alert.alert(
        message("generic_notice_title", "안내"),
        message(
          "login_password_required_message",
          "비밀번호 4자리를 입력해 주세요."
        )
      );
      return;
    }

    setLoading(true);
    try {
      const { data, error } = await api.login(name.trim(), teamCode, password);
      if (error || !data) {
        Alert.alert(
          message("generic_error_title", "오류"),
          error || message("login_failed_message", "로그인에 실패했습니다.")
        );
        return;
      }

      await saveTokens(data.access, data.refresh);

      const goCalendar = () =>
        navigation.replace("Calendar", {
          profileName: data.name,
          profileTeamCode: data.team_code,
          requiresPasswordChange: data.requires_password_change,
        });

      if (data.signup_completed === false) {
        Alert.alert(
          message("login_signup_prompt_title", "회원가입 안내"),
          message("login_signup_prompt_body", "기존 정보로 회원가입 하시겠습니까?"),
          [
            {
              text: message("login_signup_later_label", "나중에"),
              style: "cancel",
              onPress: goCalendar,
            },
            {
              text: message("signup_button_label", "회원가입"),
              onPress: () =>
                navigation.replace("Signup", {
                  mode: "migration",
                  initialName: data.name,
                  initialTeamCode: data.team_code,
                  initialVehicleNumber: data.vehicle_number,
                  initialPassword: password,
                }),
            },
          ]
        );
        return;
      }

      goCalendar();
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
        >
          <View style={styles.hero}>
            <View style={styles.logoCircle}>
              <Ionicons name="bus" size={34} color={colors.textInverse} />
            </View>
            <Text style={styles.appName}>CLEVER_CH</Text>
            <Text style={styles.appDesc}>{message("login_description", "정산 조회와 근무 기록을 위해 로그인해 주세요.")}</Text>
          </View>

          <View style={styles.formArea}>
            <View style={styles.fieldGroup}>
              <Text style={styles.label}>{message("login_name_label", "이름")}</Text>
              <View style={styles.inputWrapper}>
                <TextInput
                  style={styles.input}
                  value={name}
                  onChangeText={setName}
                  placeholder={message("login_name_placeholder", "이름을 입력해 주세요")}
                  placeholderTextColor={colors.textMuted}
                />
              </View>
            </View>

            <View style={styles.fieldGroup}>
              <Text style={styles.label}>{message("login_team_label", "조")}</Text>
              <TouchableOpacity
                style={styles.inputWrapper}
                activeOpacity={0.8}
                onPress={() => setShowPicker(true)}
              >
                <Text style={[styles.input, !teamCode && styles.placeholder]}>
                  {teamCode
                    ? message("team_code_value_template", "{team_code}조", { team_code: teamCode })
                    : message("login_team_placeholder", "조를 선택해 주세요")}
                </Text>
                <Ionicons
                  name="chevron-down"
                  size={20}
                  color={colors.textMuted}
                />
              </TouchableOpacity>
            </View>

            <View style={styles.fieldGroup}>
              <Text style={styles.label}>{message("login_password_label", "비밀번호")}</Text>
              <View style={styles.inputWrapper}>
                <TextInput
                  style={styles.input}
                  value={password}
                  onChangeText={(value) =>
                    setPassword(value.replace(/\D/g, "").slice(0, 4))
                  }
                  placeholder={message("pin_placeholder", "4자리 숫자")}
                  placeholderTextColor={colors.textMuted}
                  keyboardType="number-pad"
                  secureTextEntry
                  maxLength={4}
                />
              </View>
              <Text style={styles.helperText}>{message("login_password_helper", "기존 앱 비밀번호는 그대로 사용합니다.")}</Text>
            </View>

            <TouchableOpacity
              style={[styles.primaryButton, loading && styles.buttonDisabled]}
              activeOpacity={0.85}
              onPress={handleLogin}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color={colors.textInverse} />
              ) : (
                <Text style={styles.primaryButtonText}>{message("login_button_label", "로그인")}</Text>
              )}
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.secondaryButton}
              activeOpacity={0.8}
              onPress={() => navigation.navigate("Signup", { mode: "new" })}
            >
              <Text style={styles.secondaryButtonText}>{message("signup_button_label", "회원가입")}</Text>
            </TouchableOpacity>

            <TouchableOpacity
              onPress={openPrivacyPolicy}
              activeOpacity={0.7}
              style={styles.privacyLink}
            >
              <Text style={styles.privacyLinkText}>{message("privacy_policy_link_label", "개인정보처리방침")}</Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>

      <TeamCodePicker
        visible={showPicker}
        selected={teamCode}
        onSelect={(value) => {
          setTeamCode(value);
          setShowPicker(false);
        }}
        onClose={() => setShowPicker(false)}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bgPrimary,
  },
  flex: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: "center",
    paddingHorizontal: 24,
    paddingVertical: 32,
    gap: 28,
  },
  hero: {
    alignItems: "center",
    gap: 10,
  },
  logoCircle: {
    width: 78,
    height: 78,
    borderRadius: 39,
    backgroundColor: colors.accentBlue,
    alignItems: "center",
    justifyContent: "center",
  },
  appName: {
    ...typography.appTitle,
    color: colors.accentBlue,
  },
  appDesc: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    textAlign: "center",
  },
  formArea: {
    gap: 18,
  },
  fieldGroup: {
    gap: 8,
  },
  label: {
    ...typography.label,
    color: colors.textPrimary,
  },
  inputWrapper: {
    minHeight: 52,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.borderLight,
    paddingHorizontal: 16,
    flexDirection: "row",
    alignItems: "center",
  },
  input: {
    ...typography.body,
    color: colors.textPrimary,
    flex: 1,
  },
  placeholder: {
    color: colors.textMuted,
  },
  helperText: {
    ...typography.captionSmall,
    color: colors.textSecondary,
  },
  primaryButton: {
    minHeight: 56,
    borderRadius: 8,
    backgroundColor: colors.accentBlue,
    justifyContent: "center",
    alignItems: "center",
  },
  primaryButtonText: {
    ...typography.sectionTitle,
    color: colors.textInverse,
  },
  secondaryButton: {
    minHeight: 52,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.borderLight,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: colors.bgPrimary,
  },
  secondaryButtonText: {
    ...typography.body,
    color: colors.textPrimary,
    fontWeight: "600",
  },
  buttonDisabled: {
    opacity: 0.7,
  },
  privacyLink: {
    alignItems: "center",
    paddingTop: 4,
  },
  privacyLinkText: {
    ...typography.bodySmall,
    color: colors.accentBlue,
    textDecorationLine: "underline",
  },
});
