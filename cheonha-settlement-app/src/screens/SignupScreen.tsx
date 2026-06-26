import React, { useMemo, useState } from "react";
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
import { RouteProp, useNavigation, useRoute } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";

import TeamCodePicker from "../components/TeamCodePicker";
import { RootStackParamList } from "../navigation/types";
import {
  api,
  DATA_PROCESSING_CONSENT_URL,
  LOCATION_TERMS_URL,
  MARKETING_CONSENT_URL,
  PRIVACY_POLICY_URL,
  TERMS_OF_SERVICE_URL,
  saveTokens,
} from "../services/api";
import { useAppMessages } from "../services/appMessages";
import { colors, typography } from "../theme";

type SignupRoute = RouteProp<RootStackParamList, "Signup">;
type Nav = NativeStackNavigationProp<RootStackParamList, "Signup">;

function AgreementRow({
  checked,
  label,
  viewLabel,
  onPress,
  onOpenLink,
}: {
  checked: boolean;
  label: string;
  viewLabel?: string;
  onPress: () => void;
  onOpenLink?: () => void;
}) {
  return (
    <View style={styles.agreementRow}>
      <TouchableOpacity
        style={styles.agreementMain}
        activeOpacity={0.8}
        onPress={onPress}
        hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
        accessibilityRole="checkbox"
        accessibilityState={{ checked }}
      >
        <View style={[styles.checkbox, checked && styles.checkboxChecked]}>
          {checked ? (
            <Ionicons name="checkmark" size={18} color={colors.textInverse} />
          ) : null}
        </View>
        <Text style={styles.agreementLabel}>{label}</Text>
      </TouchableOpacity>
      {onOpenLink && viewLabel ? (
        <TouchableOpacity
          style={styles.linkButton}
          activeOpacity={0.7}
          onPress={onOpenLink}
          hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
        >
          <Text style={styles.linkText}>{viewLabel}</Text>
        </TouchableOpacity>
      ) : null}
    </View>
  );
}

export default function SignupScreen() {
  const navigation = useNavigation<Nav>();
  const route = useRoute<SignupRoute>();
  const { message } = useAppMessages();
  const mode = route.params?.mode ?? "new";
  const migrationMode = mode === "migration";

  const [name, setName] = useState(route.params?.initialName ?? "");
  const [teamCode, setTeamCode] = useState(route.params?.initialTeamCode ?? "");
  const [vehicleNumber, setVehicleNumber] = useState(
    route.params?.initialVehicleNumber ?? ""
  );
  const [password, setPassword] = useState(route.params?.initialPassword ?? "");
  const [passwordConfirm, setPasswordConfirm] = useState(
    route.params?.initialPassword ?? ""
  );
  const [agreePrivacyPolicy, setAgreePrivacyPolicy] = useState(false);
  const [agreeDataProcessing, setAgreeDataProcessing] = useState(false);
  const [agreeLocationTerms, setAgreeLocationTerms] = useState(false);
  const [agreeMarketingEvent, setAgreeMarketingEvent] = useState(false);
  const [agreeTerms, setAgreeTerms] = useState(false);
  const [showPicker, setShowPicker] = useState(false);
  const [loading, setLoading] = useState(false);

  const title = migrationMode
    ? message("signup_migration_title", "기존 정보로 회원가입")
    : message("signup_title", "회원가입");
  const subtitle = migrationMode
    ? message("signup_migration_subtitle", "기존 포인트와 근무 데이터를 그대로 이어서 사용합니다.")
    : message("signup_subtitle", "이름과 조가 시스템에 등록되어 있으면 자동 승인됩니다.");

  const requiredAgreed =
    agreePrivacyPolicy &&
    agreeDataProcessing &&
    agreeLocationTerms &&
    agreeTerms;

  const allAgreed = requiredAgreed && agreeMarketingEvent;

  const agreementLinks = useMemo(
    () => ({
      privacy: message("signup_privacy_policy_url", PRIVACY_POLICY_URL),
      dataProcessing: message(
        "signup_data_processing_url",
        DATA_PROCESSING_CONSENT_URL
      ),
      locationTerms: message("signup_location_terms_url", LOCATION_TERMS_URL),
      terms: message("signup_terms_url", TERMS_OF_SERVICE_URL),
      marketing: message("signup_marketing_url", MARKETING_CONSENT_URL),
    }),
    [message]
  );

  const canSubmit = useMemo(() => {
    return (
      name.trim().length > 0 &&
      teamCode.trim().length > 0 &&
      vehicleNumber.trim().length > 0 &&
      password.length === 4 &&
      passwordConfirm.length === 4 &&
      requiredAgreed
    );
  }, [
    name,
    password,
    passwordConfirm,
    requiredAgreed,
    teamCode,
    vehicleNumber,
  ]);

  const openUrl = async (url: string) => {
    try {
      await Linking.openURL(url);
    } catch {
      Alert.alert(
        message("generic_notice_title", "안내"),
        message("signup_link_open_failed_message", "링크를 열 수 없습니다.")
      );
    }
  };

  const setAllAgreements = (checked: boolean) => {
    setAgreePrivacyPolicy(checked);
    setAgreeDataProcessing(checked);
    setAgreeLocationTerms(checked);
    setAgreeMarketingEvent(checked);
    setAgreeTerms(checked);
  };

  const handleSubmit = async () => {
    if (!canSubmit) {
      Alert.alert(
        message("generic_notice_title", "안내"),
        message("signup_required_message", "입력과 약관 동의를 모두 완료해 주세요.")
      );
      return;
    }
    if (password !== passwordConfirm) {
      Alert.alert(
        message("generic_notice_title", "안내"),
        message("password_confirm_mismatch_message", "비밀번호 확인이 일치하지 않습니다.")
      );
      return;
    }

    setLoading(true);
    try {
      if (migrationMode) {
        const { data, error } = await api.completeSignup(
          password,
          passwordConfirm,
          vehicleNumber.trim(),
          agreePrivacyPolicy,
          agreeTerms,
          agreeDataProcessing,
          agreeLocationTerms,
          agreeMarketingEvent
        );
        if (error || !data) {
          Alert.alert(
            message("generic_error_title", "오류"),
            error || message("signup_migration_failed_message", "회원가입 처리에 실패했습니다.")
          );
          return;
        }
        navigation.replace("Calendar", {
          profileName: data.name,
          profileTeamCode: data.team_code,
          requiresPasswordChange: false,
        });
        return;
      }

      const { data, error } = await api.register(
        name.trim(),
        teamCode,
        password,
        passwordConfirm,
        vehicleNumber.trim(),
        agreePrivacyPolicy,
        agreeTerms,
        agreeDataProcessing,
        agreeLocationTerms,
        agreeMarketingEvent
      );
      if (error || !data) {
        Alert.alert(
          message("generic_error_title", "오류"),
          error || message("signup_failed_message", "회원가입에 실패했습니다.")
        );
        return;
      }

      await saveTokens(data.access, data.refresh);
      navigation.replace("Calendar", {
        profileName: data.name,
        profileTeamCode: data.team_code,
        requiresPasswordChange: false,
      });
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
          <View style={styles.header}>
            <TouchableOpacity
              style={styles.backButton}
              activeOpacity={0.7}
              onPress={() =>
                navigation.canGoBack()
                  ? navigation.goBack()
                  : navigation.replace("Login")
              }
            >
              <Ionicons name="chevron-back" size={22} color={colors.textPrimary} />
            </TouchableOpacity>
            <View style={styles.headerTextWrap}>
              <Text style={styles.title}>{title}</Text>
              <Text style={styles.subtitle}>{subtitle}</Text>
            </View>
          </View>

          <View style={styles.formCard}>
            <View style={styles.fieldGroup}>
              <Text style={styles.label}>{message("login_name_label", "이름")}</Text>
              <View style={styles.inputWrapper}>
                <TextInput
                  style={styles.input}
                  value={name}
                  onChangeText={setName}
                  editable={!migrationMode}
                  placeholder={message("login_name_placeholder", "이름을 입력해 주세요")}
                  placeholderTextColor={colors.textMuted}
                />
              </View>
            </View>

            <View style={styles.fieldGroup}>
              <Text style={styles.label}>{message("login_team_label", "조")}</Text>
              <TouchableOpacity
                style={styles.inputWrapper}
                onPress={() => !migrationMode && setShowPicker(true)}
                activeOpacity={migrationMode ? 1 : 0.8}
              >
                <Text style={[styles.input, !teamCode && styles.placeholder]}>
                  {teamCode
                    ? message("team_code_value_template", "{team_code}조", { team_code: teamCode })
                    : message("login_team_placeholder", "조를 선택해 주세요")}
                </Text>
                {!migrationMode ? (
                  <Ionicons
                    name="chevron-down"
                    size={20}
                    color={colors.textMuted}
                  />
                ) : null}
              </TouchableOpacity>
            </View>

            <View style={styles.fieldGroup}>
              <Text style={styles.label}>{message("vehicle_number_label", "차량번호")}</Text>
              <View style={styles.inputWrapper}>
                <TextInput
                  style={styles.input}
                  value={vehicleNumber}
                  onChangeText={setVehicleNumber}
                  placeholder={message("vehicle_number_placeholder", "예: 서울00배0000")}
                  placeholderTextColor={colors.textMuted}
                />
              </View>
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
            </View>

            <View style={styles.fieldGroup}>
              <Text style={styles.label}>{message("password_confirm_label", "비밀번호 확인")}</Text>
              <View style={styles.inputWrapper}>
                <TextInput
                  style={styles.input}
                  value={passwordConfirm}
                  onChangeText={(value) =>
                    setPasswordConfirm(value.replace(/\D/g, "").slice(0, 4))
                  }
                  placeholder={message("pin_confirm_placeholder", "4자리 숫자 다시 입력")}
                  placeholderTextColor={colors.textMuted}
                  keyboardType="number-pad"
                  secureTextEntry
                  maxLength={4}
                />
              </View>
            </View>

            <View style={styles.agreementCard}>
              <AgreementRow
                checked={allAgreed}
                label={message("signup_all_agreements_label", "전체 동의")}
                onPress={() => setAllAgreements(!allAgreed)}
              />
              <View style={styles.agreementDivider} />
              <AgreementRow
                checked={agreeTerms}
                label={message("signup_terms_agreement_label", "[필수] CLEVER 서비스 이용약관 동의")}
                viewLabel={message("signup_agreement_view_label", "자세히")}
                onPress={() => setAgreeTerms((prev) => !prev)}
                onOpenLink={() => openUrl(agreementLinks.terms)}
              />
              <AgreementRow
                checked={agreePrivacyPolicy}
                label={message("signup_privacy_agreement_label", "[필수] 개인정보 처리방침 동의")}
                viewLabel={message("signup_agreement_view_label", "자세히")}
                onPress={() => setAgreePrivacyPolicy((prev) => !prev)}
                onOpenLink={() => openUrl(agreementLinks.privacy)}
              />
              <AgreementRow
                checked={agreeLocationTerms}
                label={message("signup_location_terms_agreement_label", "[필수] 위치기반서비스 이용약관 동의")}
                viewLabel={message("signup_agreement_view_label", "자세히")}
                onPress={() => setAgreeLocationTerms((prev) => !prev)}
                onOpenLink={() => openUrl(agreementLinks.locationTerms)}
              />
              <AgreementRow
                checked={agreeDataProcessing}
                label={message("signup_data_processing_agreement_label", "[필수] 배송 운영 및 서비스 고도화를 위한 데이터 처리 동의")}
                viewLabel={message("signup_agreement_view_label", "자세히")}
                onPress={() => setAgreeDataProcessing((prev) => !prev)}
                onOpenLink={() => openUrl(agreementLinks.dataProcessing)}
              />
              <AgreementRow
                checked={agreeMarketingEvent}
                label={message("signup_marketing_agreement_label", "[선택] 마케팅 및 이벤트 정보 수신 동의")}
                viewLabel={message("signup_agreement_view_label", "자세히")}
                onPress={() => setAgreeMarketingEvent((prev) => !prev)}
                onOpenLink={() => openUrl(agreementLinks.marketing)}
              />
            </View>

            <TouchableOpacity
              style={[
                styles.submitButton,
                (!canSubmit || loading) && styles.submitButtonDisabled,
              ]}
              activeOpacity={0.85}
              onPress={handleSubmit}
              disabled={!canSubmit || loading}
            >
              {loading ? (
                <ActivityIndicator color={colors.textInverse} />
              ) : (
                <Text style={styles.submitButtonText}>
                  {migrationMode
                    ? message("signup_migration_submit_label", "기존 정보로 가입 완료")
                    : message("signup_button_label", "회원가입")}
                </Text>
              )}
            </TouchableOpacity>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>

      <TeamCodePicker
        visible={showPicker}
        selected={teamCode}
        onClose={() => setShowPicker(false)}
        onSelect={(value) => {
          setTeamCode(value);
          setShowPicker(false);
        }}
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
    padding: 24,
    gap: 20,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  backButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.bgSecondary,
    alignItems: "center",
    justifyContent: "center",
  },
  headerTextWrap: {
    flex: 1,
    gap: 4,
  },
  title: {
    ...typography.screenTitle,
    color: colors.textPrimary,
  },
  subtitle: {
    ...typography.bodySmall,
    color: colors.textSecondary,
  },
  formCard: {
    borderRadius: 12,
    backgroundColor: colors.bgPrimary,
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
    backgroundColor: colors.bgPrimary,
  },
  input: {
    ...typography.body,
    color: colors.textPrimary,
    flex: 1,
  },
  placeholder: {
    color: colors.textMuted,
  },
  agreementCard: {
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.borderLight,
    paddingHorizontal: 14,
    paddingVertical: 8,
    gap: 4,
    backgroundColor: colors.bgSecondary,
  },
  agreementRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
    minHeight: 52,
  },
  agreementDivider: {
    height: 1,
    backgroundColor: colors.borderLight,
  },
  agreementMain: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    flex: 1,
    minHeight: 52,
  },
  checkbox: {
    width: 28,
    height: 28,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.borderLight,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.bgPrimary,
  },
  checkboxChecked: {
    backgroundColor: colors.accentBlue,
    borderColor: colors.accentBlue,
  },
  agreementLabel: {
    ...typography.bodySmall,
    color: colors.textPrimary,
    flex: 1,
  },
  linkButton: {
    minHeight: 44,
    minWidth: 78,
    alignItems: "flex-end",
    justifyContent: "center",
  },
  linkText: {
    ...typography.caption,
    color: colors.accentBlue,
    textDecorationLine: "underline",
  },
  submitButton: {
    minHeight: 56,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.accentBlue,
  },
  submitButtonDisabled: {
    opacity: 0.5,
  },
  submitButtonText: {
    ...typography.sectionTitle,
    color: colors.textInverse,
  },
});
