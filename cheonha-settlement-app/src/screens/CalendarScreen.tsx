import React, { useState, useEffect, useCallback } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator,
  Modal,
  TextInput,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { RouteProp, useNavigation, useRoute } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { colors, typography } from "../theme";
import { api, clearTokens, SettlementDay } from "../services/api";
import { RootStackParamList } from "../navigation/types";

type Nav = NativeStackNavigationProp<RootStackParamList, "Calendar">;
type CalendarRoute = RouteProp<RootStackParamList, "Calendar">;

const DAY_LABELS = ["월", "화", "수", "목", "금", "토", "일"];
const HIT_SLOP = { top: 12, bottom: 12, left: 12, right: 12 };

export default function CalendarScreen() {
  const navigation = useNavigation<Nav>();
  const route = useRoute<CalendarRoute>();
  const initialProfileName = route.params?.profileName ?? "";
  const initialPasswordChangeRequired =
    route.params?.requiresPasswordChange ?? false;
  const [year, setYear] = useState(new Date().getFullYear());
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [profileName, setProfileName] = useState(initialProfileName);
  const [settlements, setSettlements] = useState<SettlementDay[]>([]);
  const [totalBoxes, setTotalBoxes] = useState(0);
  const [totalAmount, setTotalAmount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [passwordChangeRequired, setPasswordChangeRequired] = useState(
    initialPasswordChangeRequired
  );
  const [showPasswordModal, setShowPasswordModal] = useState(
    initialPasswordChangeRequired
  );
  const [newPassword, setNewPassword] = useState("");
  const [newPasswordConfirm, setNewPasswordConfirm] = useState("");
  const [passwordSaving, setPasswordSaving] = useState(false);

  const monthStr = `${year}-${String(month).padStart(2, "0")}`;

  const fetchData = useCallback(async () => {
    setLoading(true);

    // Fetch profile
    const profileRes = await api.getProfile();
    if (profileRes.data) {
      setProfileName(profileRes.data.name);
      if (profileRes.data.requires_password_change) {
        setPasswordChangeRequired(true);
        setShowPasswordModal(true);
        setSettlements([]);
        setTotalBoxes(0);
        setTotalAmount(0);
        setLoading(false);
        return;
      }
      if (passwordChangeRequired) {
        setPasswordChangeRequired(false);
      }
    } else if (profileRes.error?.includes("세션")) {
      navigation.replace("Login");
      return;
    }

    // Fetch settlements
    const settleRes = await api.getSettlements(monthStr);
    if (settleRes.data) {
      setSettlements(settleRes.data.days);
      setTotalBoxes(settleRes.data.total_boxes);
      setTotalAmount(settleRes.data.total_amount);
    } else if (settleRes.error) {
      Alert.alert("오류", settleRes.error);
    }

    setLoading(false);
  }, [monthStr, navigation, passwordChangeRequired]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handlePrevMonth = () => {
    if (month === 1) {
      setYear((y) => y - 1);
      setMonth(12);
    } else {
      setMonth((m) => m - 1);
    }
  };

  const handleNextMonth = () => {
    if (month === 12) {
      setYear((y) => y + 1);
      setMonth(1);
    } else {
      setMonth((m) => m + 1);
    }
  };

  const handleLogout = () => {
    Alert.alert("로그아웃", "로그아웃 하시겠습니까?", [
      { text: "취소", style: "cancel" },
      {
        text: "로그아웃",
        style: "destructive",
        onPress: async () => {
          await clearTokens();
          navigation.replace("Login");
        },
      },
    ]);
  };

  const handlePinInput =
    (setter: React.Dispatch<React.SetStateAction<string>>) => (value: string) => {
      setter(value.replace(/\D/g, "").slice(0, 4));
    };

  const closePasswordModal = () => {
    if (passwordSaving || passwordChangeRequired) return;
    setShowPasswordModal(false);
    setNewPassword("");
    setNewPasswordConfirm("");
  };

  const handleForceLogout = async () => {
    await clearTokens();
    setPasswordChangeRequired(false);
    setShowPasswordModal(false);
    setNewPassword("");
    setNewPasswordConfirm("");
    navigation.replace("Login");
  };

  const handleChangePassword = async () => {
    if (newPassword.length !== 4 || newPasswordConfirm.length !== 4) {
      Alert.alert("알림", "비밀번호는 4자리 숫자로 입력해 주세요.");
      return;
    }
    if (passwordChangeRequired && newPassword === "0000") {
      Alert.alert(
        "\uc54c\ub9bc",
        "\ucd08\uae30 \ube44\ubc00\ubc88\ud638 0000\uacfc \ub2e4\ub978 4\uc790\ub9ac\ub97c \uc785\ub825\ud574 \uc8fc\uc138\uc694."
      );
      return;
    }
    if (newPassword !== newPasswordConfirm) {
      Alert.alert("알림", "비밀번호 확인이 일치하지 않습니다.");
      return;
    }

    setPasswordSaving(true);
    const { data, error } = await api.changePassword(newPassword, newPasswordConfirm);
    setPasswordSaving(false);

    if (error) {
      if (error.includes("세션")) {
        await clearTokens();
        navigation.replace("Login");
        return;
      }
      Alert.alert("오류", error);
      return;
    }

    setPasswordChangeRequired(false);
    setShowPasswordModal(false);
    setNewPassword("");
    setNewPasswordConfirm("");
    await fetchData();
    Alert.alert("완료", data?.detail || "비밀번호가 변경되었습니다.");
  };

  // Build calendar grid
  const calendarWeeks = buildCalendarWeeks(year, month, settlements);
  const today = new Date();
  const isCurrentMonth =
    today.getFullYear() === year && today.getMonth() + 1 === month;
  const todayDate = today.getDate();

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.monthSelector}>
          <TouchableOpacity onPress={handlePrevMonth} hitSlop={HIT_SLOP}>
            <Ionicons
              name="chevron-back"
              size={24}
              color={colors.textPrimary}
            />
          </TouchableOpacity>
          <Text style={styles.monthTitle}>
            {year}년 {month}월
          </Text>
          <TouchableOpacity onPress={handleNextMonth} hitSlop={HIT_SLOP}>
            <Ionicons
              name="chevron-forward"
              size={24}
              color={colors.textPrimary}
            />
          </TouchableOpacity>
        </View>
      </View>

      <View style={styles.toolRow}>
        <View style={styles.profileBtn}>
          <Ionicons
            name="person-outline"
            size={18}
            color={colors.textSecondary}
          />
          <Text style={styles.profileName}>{profileName}</Text>
        </View>
        <TouchableOpacity
          style={styles.toolButton}
          onPress={() => setShowPasswordModal(true)}
          activeOpacity={0.8}
        >
          <Text style={styles.toolButtonText}>비밀번호 변경</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.toolButton, styles.logoutButton]}
          onPress={handleLogout}
          activeOpacity={0.8}
        >
          <Text style={styles.toolButtonText}>로그아웃</Text>
        </TouchableOpacity>
      </View>

      {/* Day Headers */}
      <View style={styles.dayHeaderRow}>
        {DAY_LABELS.map((label, i) => (
          <Text
            key={label}
            style={[
              styles.dayHeaderText,
              i === 5 && { color: colors.saturdayBlue },
              i === 6 && { color: colors.sundayRed },
            ]}
          >
            {label}
          </Text>
        ))}
      </View>

      {/* Calendar Grid */}
      <View style={styles.calendarGrid}>
        {loading ? (
          <View style={styles.loadingCenter}>
            <ActivityIndicator size="large" color={colors.accentLight} />
          </View>
        ) : (
          calendarWeeks.map((week, wi) => (
            <View key={wi} style={styles.weekRow}>
              {week.map((cell, di) => {
                const isToday =
                  isCurrentMonth && cell.day === todayDate;
                const isSaturday = di === 5;
                const isSunday = di === 6;
                const hasData =
                  cell.day > 0 && cell.boxCount !== undefined;
                const isEmpty =
                  cell.day === 0 || (!hasData && (isSaturday || isSunday));

                return (
                  <View
                    key={di}
                    style={[
                      styles.cell,
                      isEmpty && styles.cellEmpty,
                      isToday && styles.cellToday,
                    ]}
                  >
                    {cell.day > 0 && (
                      <>
                        <Text
                          style={[
                            styles.cellDate,
                            isSaturday && { color: colors.saturdayBlue },
                            isSunday && { color: colors.sundayRed },
                            isToday && { color: colors.textInverse },
                          ]}
                        >
                          {cell.day}
                        </Text>
                        {hasData && (
                          <>
                            <Text
                              style={[
                                styles.cellBox,
                                isToday && {
                                  color: colors.whiteAlpha60,
                                },
                              ]}
                            >
                              {cell.boxCount}
                            </Text>
                            <Text
                              style={[
                                styles.cellAmount,
                                isToday && {
                                  color: colors.whiteAlpha60,
                                },
                              ]}
                            >
                              {formatManWon(cell.amount!)}
                            </Text>
                          </>
                        )}
                      </>
                    )}
                  </View>
                );
              })}
            </View>
          ))
        )}
      </View>

      {/* Monthly Summary */}
      <View style={styles.summary}>
        <View style={styles.summaryHalf}>
          <Text style={styles.summaryLabel}>이번 달 총 박스</Text>
          <Text style={styles.summaryValue}>
            {totalBoxes.toLocaleString()} 박스
          </Text>
        </View>
        <View style={styles.summaryDivider} />
        <View style={styles.summaryHalf}>
          <Text style={styles.summaryLabel}>이번 달 총 금액</Text>
          <Text style={styles.summaryValue}>
            {totalAmount.toLocaleString()}원
          </Text>
        </View>
      </View>

      {passwordChangeRequired && <View style={styles.lockedOverlay} />}

      <Modal
        visible={showPasswordModal}
        transparent
        animationType="fade"
        onRequestClose={closePasswordModal}
      >
        <View style={styles.modalBackdrop}>
          <KeyboardAvoidingView
            behavior={Platform.OS === "ios" ? "padding" : undefined}
            style={styles.modalCenter}
          >
            <View style={styles.modalCard}>
              <Text style={styles.modalTitle}>
                {passwordChangeRequired ? "비밀번호를 변경하세요" : "비밀번호 변경"}
              </Text>
              <Text style={styles.modalSubtitle}>
                {passwordChangeRequired
                  ? "초기 비밀번호로 로그인했습니다. 계속하려면 비밀번호를 변경하세요."
                  : "새 비밀번호 4자리 숫자를 입력해 주세요."}
              </Text>

              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>새 비밀번호</Text>
                <TextInput
                  style={styles.modalInput}
                  value={newPassword}
                  onChangeText={handlePinInput(setNewPassword)}
                  placeholder="4자리 숫자"
                  placeholderTextColor={colors.textMuted}
                  keyboardType="number-pad"
                  secureTextEntry
                  maxLength={4}
                />
              </View>

              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>비밀번호 확인</Text>
                <TextInput
                  style={styles.modalInput}
                  value={newPasswordConfirm}
                  onChangeText={handlePinInput(setNewPasswordConfirm)}
                  placeholder="4자리 숫자"
                  placeholderTextColor={colors.textMuted}
                  keyboardType="number-pad"
                  secureTextEntry
                  maxLength={4}
                />
              </View>

              <View style={styles.modalButtonRow}>
                <TouchableOpacity
                  style={[styles.modalButton, styles.modalCancelButton]}
                  onPress={passwordChangeRequired ? handleForceLogout : closePasswordModal}
                  disabled={passwordSaving}
                  activeOpacity={0.8}
                >
                  <Text style={styles.modalCancelButtonText}>
                    {passwordChangeRequired ? "로그아웃" : "취소"}
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.modalButton, passwordSaving && styles.buttonDisabled]}
                  onPress={handleChangePassword}
                  disabled={passwordSaving}
                  activeOpacity={0.8}
                >
                  {passwordSaving ? (
                    <ActivityIndicator color={colors.textInverse} />
                  ) : (
                    <Text style={styles.modalButtonText}>적용</Text>
                  )}
                </TouchableOpacity>
              </View>
            </View>
          </KeyboardAvoidingView>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

// --- Helper functions ---

function formatManWon(amount: number): string {
  const man = amount / 10000;
  if (man === Math.floor(man)) {
    return `${man.toFixed(0)}만`;
  }
  return `${man.toFixed(1)}만`;
}

interface CalendarCell {
  day: number; // 0 = empty
  boxCount?: number;
  amount?: number;
}

function buildCalendarWeeks(
  year: number,
  month: number,
  settlements: SettlementDay[]
): CalendarCell[][] {
  const firstDay = new Date(year, month - 1, 1);
  const daysInMonth = new Date(year, month, 0).getDate();

  // Monday=0 ... Sunday=6
  let startDow = firstDay.getDay() - 1;
  if (startDow < 0) startDow = 6;

  // Build settlement lookup
  const lookup = new Map<number, SettlementDay>();
  for (const s of settlements) {
    const d = parseInt(s.date.split("-")[2], 10);
    lookup.set(d, s);
  }

  const weeks: CalendarCell[][] = [];
  let currentDay = 1;

  for (let w = 0; w < 6; w++) {
    if (currentDay > daysInMonth) break;

    const week: CalendarCell[] = [];
    for (let d = 0; d < 7; d++) {
      if ((w === 0 && d < startDow) || currentDay > daysInMonth) {
        week.push({ day: 0 });
      } else {
        const settle = lookup.get(currentDay);
        week.push({
          day: currentDay,
          boxCount: settle?.box_count,
          amount: settle?.amount,
        });
        currentDay++;
      }
    }
    weeks.push(week);
  }

  return weeks;
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bgPrimary,
  },

  // Header
  header: {
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 16,
    height: 56,
  },
  monthSelector: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  monthTitle: {
    fontFamily: typography.fontFamily,
    fontSize: 18,
    fontWeight: "700",
    color: colors.textPrimary,
  },
  toolRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingHorizontal: 16,
    paddingBottom: 8,
  },
  profileBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    flex: 1,
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 9999,
    backgroundColor: colors.bgSecondary,
  },
  profileName: {
    fontSize: 12,
    fontWeight: "500",
    color: colors.textSecondary,
  },
  toolButton: {
    height: 36,
    paddingHorizontal: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.borderLight,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.bgPrimary,
  },
  logoutButton: {
    backgroundColor: colors.bgSecondary,
  },
  toolButtonText: {
    ...typography.captionSmall,
    color: colors.textPrimary,
  },

  // Day Headers
  dayHeaderRow: {
    flexDirection: "row",
    height: 28,
    alignItems: "center",
  },
  dayHeaderText: {
    flex: 1,
    textAlign: "center",
    ...typography.captionSmall,
    color: colors.textMuted,
  },

  // Calendar Grid
  calendarGrid: {
    flex: 1,
  },
  loadingCenter: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  weekRow: {
    flex: 1,
    flexDirection: "row",
  },
  cell: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 3,
    paddingHorizontal: 2,
    gap: 1,
    backgroundColor: colors.bgPrimary,
  },
  cellEmpty: {
    backgroundColor: colors.cellEmpty,
  },
  cellToday: {
    backgroundColor: colors.accentLight,
  },
  cellDate: {
    ...typography.calendarDate,
    color: colors.textPrimary,
  },
  cellBox: {
    ...typography.calendarBox,
    color: colors.textSecondary,
  },
  cellAmount: {
    ...typography.calendarAmount,
    color: colors.accentBlue,
  },

  // Summary
  summary: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.accentBlue,
    height: 72,
    paddingHorizontal: 20,
  },
  summaryHalf: {
    flex: 1,
    alignItems: "center",
    gap: 2,
  },
  summaryDivider: {
    width: 1,
    height: 40,
    backgroundColor: colors.whiteAlpha20,
  },
  summaryLabel: {
    ...typography.summaryLabel,
    color: colors.whiteAlpha60,
  },
  summaryValue: {
    ...typography.summaryValue,
    color: colors.textInverse,
  },
  lockedOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: colors.bgPrimary,
  },
  buttonDisabled: {
    opacity: 0.7,
  },
  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(15, 23, 42, 0.55)",
  },
  modalCenter: {
    flex: 1,
    justifyContent: "center",
    paddingHorizontal: 24,
  },
  modalCard: {
    borderRadius: 16,
    backgroundColor: colors.bgPrimary,
    padding: 20,
    gap: 16,
  },
  modalTitle: {
    ...typography.sectionTitle,
    color: colors.textPrimary,
  },
  modalSubtitle: {
    ...typography.bodySmall,
    color: colors.textSecondary,
  },
  modalField: {
    gap: 8,
  },
  modalLabel: {
    ...typography.label,
    color: colors.textPrimary,
  },
  modalInput: {
    height: 52,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderLight,
    paddingHorizontal: 16,
    ...typography.body,
    color: colors.textPrimary,
  },
  modalButtonRow: {
    flexDirection: "row",
    gap: 10,
  },
  modalButton: {
    flex: 1,
    height: 48,
    borderRadius: 12,
    backgroundColor: colors.accentBlue,
    alignItems: "center",
    justifyContent: "center",
  },
  modalCancelButton: {
    backgroundColor: colors.bgSecondary,
  },
  modalButtonText: {
    ...typography.label,
    color: colors.textInverse,
  },
  modalCancelButtonText: {
    ...typography.label,
    color: colors.textPrimary,
  },
});
