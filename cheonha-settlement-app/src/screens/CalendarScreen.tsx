import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  AppState,
  Keyboard,
  KeyboardAvoidingView,
  Modal,
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
import { colors, typography } from "../theme";
import {
  api,
  clearTokens,
  getInquirySeenVersion,
  saveInquirySeenVersion,
  SettlementDay,
  SettlementInquiryDetailResponse,
  SettlementInquiryMessage,
} from "../services/api";
import {
  getStoredVehicleNumber,
  getWorkSessionState,
  requestWorkSessionPermissions,
  saveVehicleNumber,
  startWorkSession,
  stopWorkSession,
} from "../services/workSession";
import { RootStackParamList } from "../navigation/types";

type Nav = NativeStackNavigationProp<RootStackParamList, "Calendar">;
type CalendarRoute = RouteProp<RootStackParamList, "Calendar">;

const DAY_LABELS = ["월", "화", "수", "목", "금", "토", "일"];
const HIT_SLOP = { top: 12, bottom: 12, left: 12, right: 12 };
const EMPTY_SESSION_STATE = { running: false, sampleCount: 0, vehicleNumber: "", exportedUri: null, exportedFileName: null };

interface CalendarCell {
  day: number;
  date?: string;
  boxCount?: number;
  amount?: number;
  adjustmentAmount?: number;
  inquiryStatus?: SettlementDay["inquiry_status"];
}

export default function CalendarScreen() {
  const navigation = useNavigation<Nav>();
  const route = useRoute<CalendarRoute>();
  const [year, setYear] = useState(new Date().getFullYear());
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [profileName, setProfileName] = useState(route.params?.profileName ?? "");
  const [profileTeamCode, setProfileTeamCode] = useState(route.params?.profileTeamCode ?? "");
  const [settlements, setSettlements] = useState<SettlementDay[]>([]);
  const [totalBoxes, setTotalBoxes] = useState(0);
  const [totalAmount, setTotalAmount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [passwordChangeRequired, setPasswordChangeRequired] = useState(route.params?.requiresPasswordChange ?? false);
  const [showPasswordModal, setShowPasswordModal] = useState(route.params?.requiresPasswordChange ?? false);
  const [showVehicleModal, setShowVehicleModal] = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [newPasswordConfirm, setNewPasswordConfirm] = useState("");
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [vehicleSaving, setVehicleSaving] = useState(false);
  const [vehicleNumber, setVehicleNumber] = useState("");
  const [vehicleNumberDraft, setVehicleNumberDraft] = useState("");
  const [sessionRunning, setSessionRunning] = useState(false);
  const [sessionBusy, setSessionBusy] = useState(false);
  const [showInquiryModal, setShowInquiryModal] = useState(false);
  const [selectedInquiry, setSelectedInquiry] = useState<SettlementInquiryDetailResponse | null>(null);
  const [inquiryLoading, setInquiryLoading] = useState(false);
  const [inquirySubmitting, setInquirySubmitting] = useState(false);
  const [inquiryMessage, setInquiryMessage] = useState("");

  const monthStr = `${year}-${String(month).padStart(2, "0")}`;

  const applySeenInquiryStatus = useCallback(
    async (
      days: SettlementDay[],
      nextProfileName = profileName,
      nextProfileTeamCode = profileTeamCode
    ) => {
      if (!nextProfileName.trim() || !nextProfileTeamCode.trim()) {
        return days;
      }

      return Promise.all(
        days.map(async (item) => {
          if (
            item.inquiry_status !== "answered" ||
            !item.inquiry_updated_at
          ) {
            return item;
          }

          const seenVersion = await getInquirySeenVersion(
            nextProfileName,
            nextProfileTeamCode,
            item.date
          );

          if (seenVersion && seenVersion === item.inquiry_updated_at) {
            return { ...item, inquiry_status: null };
          }

          return item;
        })
      );
    },
    [profileName, profileTeamCode]
  );

  const loadSettlements = useCallback(
    async (
      options: {
        silent?: boolean;
        nextProfileName?: string;
        nextProfileTeamCode?: string;
      } = {}
    ) => {
      const { silent = false, nextProfileName, nextProfileTeamCode } = options;
      const settleRes = await api.getSettlements(monthStr);

      if (settleRes.data) {
        const nextDays = await applySeenInquiryStatus(
          settleRes.data.days,
          nextProfileName ?? profileName,
          nextProfileTeamCode ?? profileTeamCode
        );
        setSettlements(nextDays);
        setTotalBoxes(settleRes.data.total_boxes);
        setTotalAmount(settleRes.data.total_amount);
        return true;
      }

      if (settleRes.error && !silent) {
        Alert.alert("오류", settleRes.error);
      }
      return false;
    },
    [applySeenInquiryStatus, monthStr, profileName, profileTeamCode]
  );

  const fetchData = useCallback(async () => {
    setLoading(true);
    const profileRes = await api.getProfile();
    if (profileRes.data) {
      setProfileName(profileRes.data.name);
      setProfileTeamCode(profileRes.data.team_code);
      if (profileRes.data.requires_password_change) {
        setPasswordChangeRequired(true);
        setShowPasswordModal(true);
        setSettlements([]);
        setTotalBoxes(0);
        setTotalAmount(0);
        setLoading(false);
        return;
      }
      if (passwordChangeRequired) setPasswordChangeRequired(false);
    } else if (profileRes.error?.includes("세션") || profileRes.error?.includes("?몄뀡")) {
      navigation.replace("Login");
      return;
    } else if (profileRes.error) {
      Alert.alert("오류", profileRes.error);
      setLoading(false);
      return;
    }

    await loadSettlements({
      nextProfileName: profileRes.data?.name,
      nextProfileTeamCode: profileRes.data?.team_code,
    });
    setLoading(false);
  }, [loadSettlements, navigation, passwordChangeRequired]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      const sessionState = await getWorkSessionState().catch(() => EMPTY_SESSION_STATE);
      const storedVehicle =
        profileName && profileTeamCode
          ? await getStoredVehicleNumber(profileName, profileTeamCode)
          : "";
      if (!mounted) return;
      const resolvedVehicle = sessionState.running && sessionState.vehicleNumber ? sessionState.vehicleNumber : storedVehicle;
      setVehicleNumber(resolvedVehicle);
      setVehicleNumberDraft(resolvedVehicle);
      setSessionRunning(sessionState.running);
    })();
    return () => {
      mounted = false;
    };
  }, [profileName, profileTeamCode]);

  useEffect(() => {
    if (!sessionRunning) return;
    const interval = setInterval(async () => {
      const state = await getWorkSessionState().catch(() => null);
      if (!state) return;
      setSessionRunning(state.running);
      if (state.running && state.vehicleNumber) {
        setVehicleNumber(state.vehicleNumber);
        setVehicleNumberDraft(state.vehicleNumber);
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [sessionRunning]);

  useEffect(() => {
    if (passwordChangeRequired || showInquiryModal) {
      return;
    }

    const interval = setInterval(() => {
      void loadSettlements({ silent: true });
    }, 3000);

    return () => clearInterval(interval);
  }, [loadSettlements, passwordChangeRequired, showInquiryModal]);

  useEffect(() => {
    const subscription = AppState.addEventListener("change", (state) => {
      if (state === "active" && !passwordChangeRequired && !showInquiryModal) {
        void loadSettlements({ silent: true });
      }
    });

    return () => subscription.remove();
  }, [loadSettlements, passwordChangeRequired, showInquiryModal]);

  const updateInquiryBadge = (date: string, inquiryStatus: SettlementDay["inquiry_status"]) => {
    setSettlements((prev) => prev.map((item) => (item.date === date ? { ...item, inquiry_status: inquiryStatus } : item)));
  };

  const ensureProfileIdentity = () => {
    if (profileName.trim() && profileTeamCode.trim()) return true;
    Alert.alert("알림", "사용자 정보를 다시 불러온 뒤 시도해 주세요.");
    return false;
  };

  const handleLogout = () => {
    if (sessionRunning) {
      Alert.alert("알림", "근무 종료 후 로그아웃해 주세요.");
      return;
    }
    Alert.alert("로그아웃", "로그아웃 하시겠습니까?", [
      { text: "취소", style: "cancel" },
      { text: "로그아웃", style: "destructive", onPress: async () => { await clearTokens(); navigation.replace("Login"); } },
    ]);
  };

  const handleForceLogout = async () => {
    await clearTokens();
    navigation.replace("Login");
  };

  const handlePinInput = (setter: React.Dispatch<React.SetStateAction<string>>) => (value: string) => {
    setter(value.replace(/\D/g, "").slice(0, 4));
  };

  const handleChangePassword = async () => {
    if (newPassword.length !== 4 || newPasswordConfirm.length !== 4) return Alert.alert("알림", "비밀번호는 4자리 숫자로 입력해 주세요.");
    if (passwordChangeRequired && newPassword === "0000") return Alert.alert("알림", "초기 비밀번호 0000과 다른 4자리 숫자를 입력해 주세요.");
    if (newPassword !== newPasswordConfirm) return Alert.alert("알림", "비밀번호 확인이 일치하지 않습니다.");
    const trimmedVehicleNumber = vehicleNumberDraft.trim();
    if (passwordChangeRequired && !trimmedVehicleNumber) return Alert.alert("알림", "차량번호를 입력해 주세요.");
    if (passwordChangeRequired && !ensureProfileIdentity()) return;
    setPasswordSaving(true);
    const { data, error } = await api.changePassword(newPassword, newPasswordConfirm);
    if (!error && passwordChangeRequired) {
      await saveVehicleNumber(profileName, profileTeamCode, trimmedVehicleNumber);
      setVehicleNumber(trimmedVehicleNumber);
      setVehicleNumberDraft(trimmedVehicleNumber);
    }
    setPasswordSaving(false);
    if (error) {
      if (error.includes("세션") || error.includes("?몄뀡")) {
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

  const handleSaveVehicleNumber = async () => {
    const trimmedVehicleNumber = vehicleNumberDraft.trim();
    if (!trimmedVehicleNumber) return Alert.alert("알림", "차량번호를 입력해 주세요.");
    if (!ensureProfileIdentity()) return;
    setVehicleSaving(true);
    await saveVehicleNumber(profileName, profileTeamCode, trimmedVehicleNumber);
    setVehicleNumber(trimmedVehicleNumber);
    setVehicleNumberDraft(trimmedVehicleNumber);
    setVehicleSaving(false);
    setShowVehicleModal(false);
    Alert.alert("완료", "차량번호가 저장되었습니다.");
  };

  const openInquiry = async (date: string) => {
    setInquiryLoading(true);
    setShowInquiryModal(true);
    setInquiryMessage("");
    setSelectedInquiry(null);
    const { data, error } = await api.getSettlementInquiry(date);
    setInquiryLoading(false);
    if (error || !data) {
      setShowInquiryModal(false);
      Alert.alert("오류", error || "문의 정보를 불러올 수 없습니다.");
      return;
    }

    if (
      data.badge_status === "answered" &&
      data.updated_at &&
      profileName.trim() &&
      profileTeamCode.trim()
    ) {
      await saveInquirySeenVersion(
        profileName,
        profileTeamCode,
        data.date,
        data.updated_at
      );
      updateInquiryBadge(date, null);
    }

    setSelectedInquiry(data);
  };

  const handleSubmitInquiry = async () => {
    if (!selectedInquiry) return;
    const content = inquiryMessage.trim();
    if (!content) return Alert.alert("알림", "문의 내용을 입력해 주세요.");
    setInquirySubmitting(true);
    const { data, error } = await api.commentSettlementInquiry(selectedInquiry.date, content);
    setInquirySubmitting(false);
    if (error || !data) return Alert.alert("오류", error || "문의 등록에 실패했습니다.");
    setSelectedInquiry(data);
    setInquiryMessage("");
    updateInquiryBadge(data.date, "pending");
  };

  const handleStartSession = async () => {
    const trimmedVehicleNumber = vehicleNumber.trim();
    if (!trimmedVehicleNumber) return Alert.alert("알림", "차량번호 변경에서 차량번호를 먼저 등록해 주세요.");
    setSessionBusy(true);
    try {
      const permissionResult = await requestWorkSessionPermissions();
      if (!permissionResult.granted) return Alert.alert("권한 필요", "위치, 블루투스, 알림, 이미지 접근 권한이 있어야 근무 기록을 시작할 수 있습니다.");
      if (!permissionResult.backgroundLocationGranted) Alert.alert("안내", "백그라운드 위치 권한이 없어 앱이 백그라운드로 가면 위치 기록이 제한될 수 있습니다.");
      await startWorkSession(profileName, trimmedVehicleNumber);
      setSessionRunning(true);
      Alert.alert("시작", "근무 기록을 시작했습니다.");
    } catch (error: any) {
      Alert.alert("오류", error?.message || "근무 기록을 시작할 수 없습니다.");
    } finally {
      setSessionBusy(false);
    }
  };

  const handleStopSession = async () => {
    Alert.alert("근무 종료", "근무 기록을 종료하고 CSV를 공유하시겠습니까?", [
      { text: "취소", style: "cancel" },
      { text: "근무 종료", style: "destructive", onPress: async () => { setSessionBusy(true); try { await stopWorkSession(); setSessionRunning(false); } catch (error: any) { Alert.alert("오류", error?.message || "근무 기록을 종료할 수 없습니다."); } finally { setSessionBusy(false); } } },
    ]);
  };

  const calendarWeeks = useMemo(() => buildCalendarWeeks(year, month, settlements), [year, month, settlements]);
  const today = new Date();
  const isCurrentMonth = today.getFullYear() === year && today.getMonth() + 1 === month;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}><View style={styles.monthSelector}>
        <TouchableOpacity onPress={() => (month === 1 ? (setYear((v) => v - 1), setMonth(12)) : setMonth((v) => v - 1))} hitSlop={HIT_SLOP}><Ionicons name="chevron-back" size={24} color={colors.textPrimary} /></TouchableOpacity>
        <Text style={styles.monthTitle}>{year}년 {month}월</Text>
        <TouchableOpacity onPress={() => (month === 12 ? (setYear((v) => v + 1), setMonth(1)) : setMonth((v) => v + 1))} hitSlop={HIT_SLOP}><Ionicons name="chevron-forward" size={24} color={colors.textPrimary} /></TouchableOpacity>
      </View></View>

      <View style={styles.profileRow}>
        <View style={styles.profilePill}><Ionicons name="person-outline" size={18} color={colors.textSecondary} /><Text style={styles.profileName}>{profileName}</Text><Text style={styles.profileVehicle}>{vehicleNumber ? `· ${vehicleNumber}` : "· 차량 미등록"}</Text></View>
        <TouchableOpacity style={[styles.toolButton, styles.logoutButton]} onPress={handleLogout}><Text style={styles.toolButtonText}>로그아웃</Text></TouchableOpacity>
      </View>

      <View style={styles.actionRow}>
        <TouchableOpacity style={styles.toolButton} onPress={() => setShowPasswordModal(true)}><Text style={styles.toolButtonText}>비밀번호 변경</Text></TouchableOpacity>
        <TouchableOpacity style={[styles.toolButton, (sessionRunning || sessionBusy) && styles.buttonDisabled]} onPress={() => setShowVehicleModal(true)} disabled={sessionRunning || sessionBusy}><Text style={styles.toolButtonText}>차량번호 변경</Text></TouchableOpacity>
      </View>

      <View style={styles.dayHeaderRow}>{DAY_LABELS.map((label, index) => <Text key={label} style={[styles.dayHeaderText, index === 5 && { color: colors.saturdayBlue }, index === 6 && { color: colors.sundayRed }]}>{label}</Text>)}</View>

      <View style={styles.calendarGrid}>
        {loading ? <View style={styles.loadingCenter}><ActivityIndicator size="large" color={colors.accentLight} /></View> : calendarWeeks.map((week, weekIndex) => (
          <View key={weekIndex} style={styles.weekRow}>
            {week.map((cell, dayIndex) => {
              const isToday = isCurrentMonth && cell.day === today.getDate();
              const isSaturday = dayIndex === 5;
              const isSunday = dayIndex === 6;
              const hasData = cell.day > 0 && cell.boxCount !== undefined;
              const Comp = hasData && cell.date ? TouchableOpacity : View;
              return (
                <Comp
                  key={dayIndex}
                  style={[styles.cell, (cell.day === 0 || (!hasData && (isSaturday || isSunday))) && styles.cellEmpty, isToday && styles.cellToday]}
                  {...(Comp === TouchableOpacity ? { activeOpacity: 0.75, onPress: () => openInquiry(cell.date!) } : {})}
                >
                  {cell.day > 0 ? <>
                    <Text style={[styles.cellDate, isSaturday && { color: colors.saturdayBlue }, isSunday && { color: colors.sundayRed }, isToday && { color: colors.textInverse }]}>{cell.day}</Text>
                    {cell.inquiryStatus ? <View style={[styles.cellBadge, cell.inquiryStatus === "answered" ? styles.badgeAnswered : styles.badgePending]} /> : null}
                    {hasData ? <>
                      <Text style={[styles.cellBox, isToday && { color: colors.whiteAlpha60 }]}>{cell.boxCount}</Text>
                      <Text style={[styles.cellAmount, isToday && { color: colors.whiteAlpha60 }]}>{formatManWon(cell.amount ?? 0)}</Text>
                    </> : null}
                  </> : null}
                </Comp>
              );
            })}
          </View>
        ))}
      </View>

      <View style={styles.workButtonWrap}>
        <TouchableOpacity style={[styles.workButton, sessionRunning ? styles.workStopButton : styles.workStartButton, sessionBusy && styles.buttonDisabled]} disabled={sessionBusy} onPress={sessionRunning ? handleStopSession : handleStartSession}>
          {sessionBusy ? <ActivityIndicator color={colors.textInverse} /> : <Text style={styles.workButtonText}>{sessionRunning ? "근무종료" : "근무시작"}</Text>}
        </TouchableOpacity>
      </View>

      <View style={styles.summary}>
        <View style={styles.summaryHalf}><Text style={styles.summaryLabel}>이번 달 총 박스</Text><Text style={styles.summaryValue}>{totalBoxes.toLocaleString()} 박스</Text></View>
        <View style={styles.summaryDivider} />
        <View style={styles.summaryHalf}><Text style={styles.summaryLabel}>이번 달 총 금액</Text><Text style={styles.summaryValue}>{Number(totalAmount).toLocaleString()}원</Text></View>
      </View>

      {passwordChangeRequired ? <View style={styles.lockedOverlay} /> : null}

      <InquiryModal visible={showInquiryModal} loading={inquiryLoading} detail={selectedInquiry} message={inquiryMessage} setMessage={setInquiryMessage} submitting={inquirySubmitting} onClose={() => { if (!inquirySubmitting) { setShowInquiryModal(false); setSelectedInquiry(null); setInquiryMessage(""); void loadSettlements({ silent: true }); } }} onSubmit={handleSubmitInquiry} />

      <Modal visible={showPasswordModal} transparent animationType="fade" onRequestClose={() => (!passwordSaving && !passwordChangeRequired ? setShowPasswordModal(false) : null)}>
        <View style={styles.modalBackdrop}><KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.modalCenter}><View style={styles.modalCard}>
          <Text style={styles.modalTitle}>{passwordChangeRequired ? "비밀번호를 변경해 주세요" : "비밀번호 변경"}</Text>
          <Text style={styles.modalSubtitle}>{passwordChangeRequired ? "초기 비밀번호로 로그인했습니다. 계속하려면 비밀번호와 차량번호를 먼저 등록해야 합니다." : "새 비밀번호 4자리를 입력해 주세요."}</Text>
          <Field label="새 비밀번호"><TextInput style={styles.modalInput} value={newPassword} onChangeText={handlePinInput(setNewPassword)} placeholder="4자리 숫자" placeholderTextColor={colors.textMuted} keyboardType="number-pad" secureTextEntry maxLength={4} /></Field>
          <Field label="비밀번호 확인"><TextInput style={styles.modalInput} value={newPasswordConfirm} onChangeText={handlePinInput(setNewPasswordConfirm)} placeholder="4자리 숫자" placeholderTextColor={colors.textMuted} keyboardType="number-pad" secureTextEntry maxLength={4} /></Field>
          {passwordChangeRequired ? <Field label="차량번호"><TextInput style={styles.modalInput} value={vehicleNumberDraft} onChangeText={setVehicleNumberDraft} placeholder="서울12배1234" placeholderTextColor={colors.textMuted} autoCapitalize="characters" autoCorrect={false} /></Field> : null}
          <View style={styles.modalButtonRow}>
            <TouchableOpacity style={[styles.modalButton, styles.modalCancelButton]} onPress={passwordChangeRequired ? handleForceLogout : () => setShowPasswordModal(false)} disabled={passwordSaving}><Text style={styles.modalCancelButtonText}>{passwordChangeRequired ? "로그아웃" : "취소"}</Text></TouchableOpacity>
            <TouchableOpacity style={[styles.modalButton, passwordSaving && styles.buttonDisabled]} onPress={handleChangePassword} disabled={passwordSaving}>{passwordSaving ? <ActivityIndicator color={colors.textInverse} /> : <Text style={styles.modalButtonText}>적용</Text>}</TouchableOpacity>
          </View>
        </View></KeyboardAvoidingView></View>
      </Modal>

      <Modal visible={showVehicleModal} transparent animationType="fade" onRequestClose={() => (!vehicleSaving ? setShowVehicleModal(false) : null)}>
        <View style={styles.modalBackdrop}><KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.modalCenter}><View style={styles.modalCard}>
          <Text style={styles.modalTitle}>차량번호 변경</Text>
          <Text style={styles.modalSubtitle}>근무 기록에 사용할 차량번호를 저장합니다.</Text>
          <Field label="차량번호"><TextInput style={styles.modalInput} value={vehicleNumberDraft} onChangeText={setVehicleNumberDraft} placeholder="서울12배1234" placeholderTextColor={colors.textMuted} autoCapitalize="characters" autoCorrect={false} /></Field>
          <View style={styles.modalButtonRow}>
            <TouchableOpacity style={[styles.modalButton, styles.modalCancelButton]} onPress={() => setShowVehicleModal(false)} disabled={vehicleSaving}><Text style={styles.modalCancelButtonText}>취소</Text></TouchableOpacity>
            <TouchableOpacity style={[styles.modalButton, vehicleSaving && styles.buttonDisabled]} onPress={handleSaveVehicleNumber} disabled={vehicleSaving}>{vehicleSaving ? <ActivityIndicator color={colors.textInverse} /> : <Text style={styles.modalButtonText}>저장</Text>}</TouchableOpacity>
          </View>
        </View></KeyboardAvoidingView></View>
      </Modal>
    </SafeAreaView>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <View style={styles.modalField}><Text style={styles.modalLabel}>{label}</Text>{children}</View>;
}

function InquiryModal({
  visible, loading, detail, message, setMessage, submitting, onClose, onSubmit,
}: {
  visible: boolean; loading: boolean; detail: SettlementInquiryDetailResponse | null; message: string; setMessage: (value: string) => void; submitting: boolean; onClose: () => void; onSubmit: () => void;
}) {
  const [keyboardHeight, setKeyboardHeight] = useState(0);

  useEffect(() => {
    if (Platform.OS !== "android") {
      return;
    }

    const showSubscription = Keyboard.addListener("keyboardDidShow", (event) => {
      setKeyboardHeight(event.endCoordinates.height);
    });
    const hideSubscription = Keyboard.addListener("keyboardDidHide", () => {
      setKeyboardHeight(0);
    });

    return () => {
      showSubscription.remove();
      hideSubscription.remove();
    };
  }, []);

  useEffect(() => {
    if (!visible) {
      setKeyboardHeight(0);
    }
  }, [visible]);

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={styles.modalBackdrop}><KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.flexFill}><View style={[styles.inquiryModalCenter, Platform.OS === "android" && keyboardHeight > 0 ? { paddingBottom: keyboardHeight + 12 } : null]}>
        <View style={[styles.modalCard, styles.inquiryCard]}>
        {loading || !detail ? <View style={styles.loadingCenter}><ActivityIndicator size="large" color={colors.accentBlue} /></View> : <>
          <View style={styles.inquiryHeader}><Text style={styles.modalTitle}>정산 문의</Text><TouchableOpacity onPress={onClose} hitSlop={HIT_SLOP}><Ionicons name="close" size={22} color={colors.textSecondary} /></TouchableOpacity></View>
          <View style={styles.inquirySummaryRow}>
            <SummaryChip label="날짜" value={formatDateLabel(detail.date)} />
            <SummaryChip label="박스수" value={`${detail.box_count}개`} />
            {detail.adjustment_amount !== 0 ? <SummaryChip label="조정비용" value={`${detail.adjustment_amount.toLocaleString()}원`} /> : null}
            <SummaryChip label="정산금액" value={`${detail.amount.toLocaleString()}원`} />
          </View>
          <ScrollView style={styles.messageScroll} contentContainerStyle={styles.messageList} keyboardShouldPersistTaps="handled">
            {detail.messages.length === 0 ? <View style={styles.emptyMessageBox}><Text style={styles.emptyMessageText}>박스수나 정산금액이 이상하면 아래에 내용을 남겨 주세요.</Text></View> : detail.messages.map((item) => <MessageBubble key={item.id} message={item} />)}
          </ScrollView>
          <View style={styles.inquiryComposer}>
            <TextInput style={styles.inquiryInput} value={message} onChangeText={setMessage} placeholder="문의 내용을 입력해 주세요." placeholderTextColor={colors.textMuted} multiline />
            <TouchableOpacity style={[styles.modalButton, styles.inquirySubmitButton, submitting && styles.buttonDisabled]} onPress={onSubmit} disabled={submitting}>{submitting ? <ActivityIndicator color={colors.textInverse} /> : <Text style={styles.modalButtonText}>등록</Text>}</TouchableOpacity>
          </View>
        </>}
      </View></View></KeyboardAvoidingView></View>
    </Modal>
  );
}

function SummaryChip({ label, value }: { label: string; value: string }) {
  return <View style={styles.summaryChip}><Text style={styles.summaryChipLabel}>{label}</Text><Text style={styles.summaryChipValue}>{value}</Text></View>;
}

function MessageBubble({ message }: { message: SettlementInquiryMessage }) {
  const mine = message.author_type === "crew";
  return <View style={[styles.messageRow, mine ? styles.rowEnd : styles.rowStart]}><View style={[styles.messageBubble, mine ? styles.bubbleMine : styles.bubbleOther]}><Text style={[styles.messageAuthor, mine && styles.messageAuthorMine]}>{mine ? "나" : message.author_name || "관리자"}</Text><Text style={[styles.messageContent, mine && styles.messageContentMine]}>{message.content}</Text><Text style={[styles.messageTime, mine && styles.messageTimeMine]}>{formatTimeLabel(message.created_at)}</Text></View></View>;
}

function formatManWon(amount: number) {
  const man = Number(amount || 0) / 10000;
  return Number.isInteger(man) ? `${man.toFixed(0)}만` : `${man.toFixed(1)}만`;
}

function formatDateLabel(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function formatTimeLabel(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}

function buildCalendarWeeks(year: number, month: number, settlements: SettlementDay[]): CalendarCell[][] {
  const firstDay = new Date(year, month - 1, 1);
  const daysInMonth = new Date(year, month, 0).getDate();
  let startDayOfWeek = firstDay.getDay() - 1;
  if (startDayOfWeek < 0) startDayOfWeek = 6;
  const lookup = new Map<number, SettlementDay>();
  settlements.forEach((settlement) => lookup.set(Number.parseInt(settlement.date.split("-")[2], 10), settlement));
  const weeks: CalendarCell[][] = [];
  let currentDay = 1;
  for (let week = 0; week < 6; week += 1) {
    if (currentDay > daysInMonth) break;
    const cells: CalendarCell[] = [];
    for (let day = 0; day < 7; day += 1) {
      if ((week === 0 && day < startDayOfWeek) || currentDay > daysInMonth) cells.push({ day: 0 });
      else {
        const settlement = lookup.get(currentDay);
        cells.push({ day: currentDay, date: settlement?.date, boxCount: settlement?.box_count, amount: settlement?.amount, adjustmentAmount: settlement?.adjustment_amount, inquiryStatus: settlement?.inquiry_status ?? null });
        currentDay += 1;
      }
    }
    weeks.push(cells);
  }
  return weeks;
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bgPrimary },
  header: { justifyContent: "center", alignItems: "center", paddingHorizontal: 16, height: 56 },
  monthSelector: { flexDirection: "row", alignItems: "center", gap: 8 },
  monthTitle: { fontFamily: typography.fontFamily, fontSize: 18, fontWeight: "700", color: colors.textPrimary },
  profileRow: { flexDirection: "row", alignItems: "center", gap: 8, paddingHorizontal: 16, paddingBottom: 8 },
  profilePill: { flexDirection: "row", alignItems: "center", gap: 6, flex: 1, paddingVertical: 8, paddingHorizontal: 12, borderRadius: 999, backgroundColor: colors.bgSecondary },
  profileName: { ...typography.caption, color: colors.textPrimary },
  profileVehicle: { ...typography.captionSmall, color: colors.textSecondary, flexShrink: 1 },
  actionRow: { flexDirection: "row", gap: 8, paddingHorizontal: 16, paddingBottom: 8 },
  toolButton: { flex: 1, height: 36, paddingHorizontal: 12, borderRadius: 8, borderWidth: 1, borderColor: colors.borderLight, alignItems: "center", justifyContent: "center", backgroundColor: colors.bgPrimary },
  logoutButton: { flex: 0, backgroundColor: colors.bgSecondary },
  toolButtonText: { ...typography.captionSmall, color: colors.textPrimary },
  dayHeaderRow: { flexDirection: "row", height: 28, alignItems: "center" },
  dayHeaderText: { flex: 1, textAlign: "center", ...typography.captionSmall, color: colors.textMuted },
  calendarGrid: { flex: 1 },
  loadingCenter: { flex: 1, alignItems: "center", justifyContent: "center" },
  weekRow: { flex: 1, flexDirection: "row" },
  cell: { flex: 1, alignItems: "center", justifyContent: "center", paddingVertical: 3, paddingHorizontal: 2, gap: 1, backgroundColor: colors.bgPrimary, position: "relative" },
  cellEmpty: { backgroundColor: colors.cellEmpty },
  cellToday: { backgroundColor: colors.accentLight },
  cellDate: { ...typography.calendarDate, color: colors.textPrimary },
  cellBadge: { position: "absolute", top: 6, right: 7, width: 8, height: 8, borderRadius: 4 },
  badgePending: { backgroundColor: "#9CA3AF" },
  badgeAnswered: { backgroundColor: colors.successGreen },
  cellBox: { ...typography.calendarBox, color: colors.textSecondary },
  cellAmount: { ...typography.calendarAmount, color: colors.accentBlue },
  workButtonWrap: { marginHorizontal: 16, marginBottom: 12 },
  workButton: { width: "100%", height: 52, borderRadius: 8, alignItems: "center", justifyContent: "center" },
  workStartButton: { backgroundColor: colors.accentBlue },
  workStopButton: { backgroundColor: colors.sundayRed },
  workButtonText: { ...typography.label, color: colors.textInverse },
  summary: { flexDirection: "row", alignItems: "center", backgroundColor: colors.accentBlue, height: 72, paddingHorizontal: 20 },
  summaryHalf: { flex: 1, alignItems: "center", gap: 2 },
  summaryDivider: { width: 1, height: 40, backgroundColor: colors.whiteAlpha20 },
  summaryLabel: { ...typography.summaryLabel, color: colors.whiteAlpha60 },
  summaryValue: { ...typography.summaryValue, color: colors.textInverse },
  lockedOverlay: { ...StyleSheet.absoluteFillObject, backgroundColor: colors.bgPrimary },
  buttonDisabled: { opacity: 0.7 },
  modalBackdrop: { flex: 1, backgroundColor: "rgba(15, 23, 42, 0.55)" },
  flexFill: { flex: 1 },
  modalCenter: { flex: 1, justifyContent: "center", paddingHorizontal: 24, paddingVertical: 20 },
  inquiryModalCenter: { flex: 1, justifyContent: "flex-end", paddingHorizontal: 16, paddingVertical: 12 },
  modalCard: { borderRadius: 8, backgroundColor: colors.bgPrimary, padding: 20, gap: 16 },
  inquiryCard: { maxHeight: 680, minHeight: 420 },
  modalTitle: { ...typography.sectionTitle, color: colors.textPrimary },
  modalSubtitle: { ...typography.bodySmall, color: colors.textSecondary },
  modalField: { gap: 8 },
  modalLabel: { ...typography.label, color: colors.textPrimary },
  modalInput: { height: 52, borderRadius: 8, borderWidth: 1, borderColor: colors.borderLight, paddingHorizontal: 16, ...typography.body, color: colors.textPrimary },
  modalButtonRow: { flexDirection: "row", gap: 10 },
  modalButton: { flex: 1, height: 48, borderRadius: 8, backgroundColor: colors.accentBlue, alignItems: "center", justifyContent: "center" },
  modalCancelButton: { backgroundColor: colors.bgSecondary },
  modalButtonText: { ...typography.label, color: colors.textInverse },
  modalCancelButtonText: { ...typography.label, color: colors.textPrimary },
  inquiryHeader: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  inquirySummaryRow: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  summaryChip: { minWidth: 96, paddingHorizontal: 12, paddingVertical: 10, borderRadius: 8, backgroundColor: colors.bgSecondary, borderWidth: 1, borderColor: colors.borderLight, gap: 4 },
  summaryChipLabel: { ...typography.captionSmall, color: colors.textMuted },
  summaryChipValue: { ...typography.label, color: colors.textPrimary },
  messageScroll: { flex: 1 },
  messageList: { gap: 10, paddingVertical: 4 },
  emptyMessageBox: { paddingVertical: 24, alignItems: "center", justifyContent: "center" },
  emptyMessageText: { ...typography.bodySmall, color: colors.textSecondary, textAlign: "center" },
  messageRow: { flexDirection: "row" },
  rowEnd: { justifyContent: "flex-end" },
  rowStart: { justifyContent: "flex-start" },
  messageBubble: { maxWidth: "84%", borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10, gap: 4 },
  bubbleMine: { backgroundColor: colors.accentBlue },
  bubbleOther: { backgroundColor: colors.bgSecondary, borderWidth: 1, borderColor: colors.borderLight },
  messageAuthor: { ...typography.captionSmall, color: colors.textSecondary },
  messageAuthorMine: { color: colors.whiteAlpha60 },
  messageContent: { ...typography.bodySmall, color: colors.textPrimary },
  messageContentMine: { color: colors.textInverse },
  messageTime: { ...typography.captionSmall, color: colors.textMuted },
  messageTimeMine: { color: colors.whiteAlpha60 },
  inquiryComposer: { gap: 10, paddingTop: 4 },
  inquiryInput: { minHeight: 92, maxHeight: 140, borderRadius: 8, borderWidth: 1, borderColor: colors.borderLight, paddingHorizontal: 14, paddingVertical: 12, ...typography.body, color: colors.textPrimary, textAlignVertical: "top" },
  inquirySubmitButton: { flex: 0, width: "100%" },
});
