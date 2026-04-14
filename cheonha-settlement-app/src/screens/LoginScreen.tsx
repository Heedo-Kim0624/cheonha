import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { colors, typography } from "../theme";
import { api, saveTokens } from "../services/api";
import { RootStackParamList } from "../navigation/types";
import TeamCodePicker from "../components/TeamCodePicker";

type Nav = NativeStackNavigationProp<RootStackParamList, "Login">;

export default function LoginScreen() {
  const navigation = useNavigation<Nav>();
  const [name, setName] = useState("");
  const [teamCode, setTeamCode] = useState("");
  const [password, setPassword] = useState("");
  const [showPicker, setShowPicker] = useState(false);
  const [loading, setLoading] = useState(false);

  const handlePasswordChange = (value: string) => {
    setPassword(value.replace(/\D/g, "").slice(0, 4));
  };

  const handleLogin = async () => {
    if (!name.trim()) {
      Alert.alert("알림", "이름을 입력해 주세요.");
      return;
    }
    if (!teamCode) {
      Alert.alert("알림", "소속 조를 선택해 주세요.");
      return;
    }
    if (password.length !== 4) {
      Alert.alert("알림", "비밀번호 4자리를 입력해 주세요.");
      return;
    }

    setLoading(true);
    const { data, error } = await api.login(name.trim(), teamCode, password);
    setLoading(false);

    if (error) {
      Alert.alert("오류", error);
      return;
    }

    if (data) {
      await saveTokens(data.access, data.refresh);
      navigation.replace("Calendar", {
        profileName: data.name,
        requiresPasswordChange: data.requires_password_change,
      });
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
          {/* Logo Area */}
          <View style={styles.logoArea}>
            <View style={styles.logoCircle}>
              <Ionicons name="bus" size={36} color={colors.textInverse} />
            </View>
            <Text style={styles.appName}>천하정산</Text>
            <Text style={styles.appDesc}>로그인하여 정산을 확인하세요</Text>
          </View>

          {/* Form */}
          <View style={styles.formArea}>
            {/* Name Field */}
            <View style={styles.fieldGroup}>
              <Text style={styles.label}>이름</Text>
              <View style={styles.inputWrapper}>
                <TextInput
                  style={styles.input}
                  placeholder="이름을 입력하세요"
                  placeholderTextColor={colors.textMuted}
                  value={name}
                  onChangeText={setName}
                  autoCapitalize="none"
                />
              </View>
            </View>

            {/* Team Code Field */}
            <View style={styles.fieldGroup}>
              <Text style={styles.label}>소속 조</Text>
              <TouchableOpacity
                style={styles.inputWrapper}
                onPress={() => setShowPicker(true)}
                activeOpacity={0.7}
              >
                <Text
                  style={[styles.input, !teamCode && styles.placeholder]}
                >
                  {teamCode
                    ? `${teamCode}조`
                    : "조를 선택하세요 (A-Z)"}
                </Text>
                <Ionicons
                  name="chevron-down"
                  size={20}
                  color={colors.textMuted}
                />
              </TouchableOpacity>
            </View>

            <View style={styles.fieldGroup}>
              <Text style={styles.label}>비밀번호</Text>
              <View style={styles.inputWrapper}>
                <TextInput
                  style={styles.input}
                  placeholder="비밀번호 4자리"
                  placeholderTextColor={colors.textMuted}
                  value={password}
                  onChangeText={handlePasswordChange}
                  keyboardType="number-pad"
                  maxLength={4}
                  secureTextEntry
                />
              </View>
              <Text style={styles.helperText}>초기 비밀번호는 0000입니다.</Text>
            </View>

            {/* Login Button */}
            <TouchableOpacity
              style={[styles.button, loading && styles.buttonDisabled]}
              onPress={handleLogin}
              disabled={loading}
              activeOpacity={0.8}
            >
              {loading ? (
                <ActivityIndicator color={colors.textInverse} />
              ) : (
                <Text style={styles.buttonText}>로그인</Text>
              )}
            </TouchableOpacity>
          </View>

        </ScrollView>
      </KeyboardAvoidingView>

      <TeamCodePicker
        visible={showPicker}
        selected={teamCode}
        onSelect={(code) => {
          setTeamCode(code);
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
  loadingContainer: {
    justifyContent: "center",
    alignItems: "center",
    gap: 12,
  },
  scrollContent: {
    flexGrow: 1,
    paddingHorizontal: 24,
    justifyContent: "center",
    gap: 32,
  },

  // Logo
  logoArea: {
    alignItems: "center",
    gap: 12,
  },
  logoCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: colors.accentBlue,
    justifyContent: "center",
    alignItems: "center",
  },
  appName: {
    ...typography.appTitle,
    color: colors.accentBlue,
  },
  appDesc: {
    ...typography.bodySmall,
    color: colors.textSecondary,
  },

  // Form
  formArea: {
    gap: 20,
  },
  fieldGroup: {
    gap: 8,
  },
  label: {
    ...typography.label,
    color: colors.textPrimary,
  },
  inputWrapper: {
    flexDirection: "row",
    alignItems: "center",
    height: 52,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderLight,
    paddingHorizontal: 16,
  },
  input: {
    flex: 1,
    ...typography.body,
    color: colors.textPrimary,
  },
  placeholder: {
    color: colors.textMuted,
  },
  helperText: {
    ...typography.captionSmall,
    color: colors.textSecondary,
  },

  // Button
  button: {
    height: 56,
    borderRadius: 12,
    backgroundColor: colors.accentBlue,
    justifyContent: "center",
    alignItems: "center",
  },
  buttonDisabled: {
    opacity: 0.7,
  },
  buttonText: {
    ...typography.sectionTitle,
    color: colors.textInverse,
  },

  // Link
  linkRow: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 6,
  },
  linkText: {
    ...typography.label,
    fontWeight: "400",
    color: colors.textSecondary,
  },
  linkAction: {
    ...typography.label,
    color: colors.accentLight,
  },
});
