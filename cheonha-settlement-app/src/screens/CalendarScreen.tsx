import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  AppState,
  Keyboard,
  KeyboardAvoidingView,
  Linking,
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
import * as SecureStore from "expo-secure-store";
import { colors, typography } from "../theme";
import {
  API_BASE_URL,
  api,
  clearTokens,
  getClientAppVersion,
  getInquirySeenVersion,
  getStoredAccessToken,
  PointRedemption,
  PointRedemptionItem,
  PointSummaryResponse,
  saveInquirySeenVersion,
  SettlementDay,
  SettlementRoundSummary,
  SettlementInquiryDetailResponse,
  SettlementInquiryMessage,
} from "../services/api";
import { useAppMessages } from "../services/appMessages";
import {
  configureWorkSessionServerSync,
  getStoredVehicleNumber,
  hasBackgroundLocationPermission,
  getWorkSessionState,
  getWorkSessionSummary,
  requestWorkSessionPermissions,
  saveVehicleNumber,
  startWorkSessionWithSignalCheck,
  stopWorkSession,
} from "../services/workSession";
import { RootStackParamList } from "../navigation/types";
import { normalizeSecureStoreKeyPart } from "../utils/secureStoreKey";

type Nav = NativeStackNavigationProp<RootStackParamList, "Calendar">;
type CalendarRoute = RouteProp<RootStackParamList, "Calendar">;

const HIT_SLOP = { top: 12, bottom: 12, left: 12, right: 12 };
const EMPTY_SESSION_STATE = { running: false, sampleCount: 0, vehicleNumber: "", exportedUri: null, exportedFileName: null };
const INSPECTION_REMINDER_HIDE_PREFIX = "inspectionReminderHidden";
const WORK_GUIDE_HIDE_PREFIX = "workGuideHidden";
const WORK_GUIDE_GLOBAL_HIDE_KEY = `${WORK_GUIDE_HIDE_PREFIX}.global`;
const BASE_WORK_POINT_REWARD = 5;
const DOUBLE_EVENT_WORK_POINT_REWARD = 10;
const WORK_POINT_MIN_CAMERA_END_COUNT = 10;
const DOUBLE_EVENT_END_DATE = "2026-05-31";

interface CalendarCell {
  day: number;
  date?: string;
  boxCount?: number;
  regularBoxCount?: number;
  yongchaHouseholdCount?: number;
  amount?: number;
  adjustmentAmount?: number;
  inquiryStatus?: SettlementDay["inquiry_status"];
}

interface InquirySummary {
  boxCount: number;
  adjustmentAmount: number;
  amount: number;
}

function summarizeRoundDisplay(rounds: SettlementRoundSummary[] = []) {
  if (!rounds.length) {
    return { regularBoxCount: 0, yongchaHouseholdCount: 0, hasMixedYongcha: false };
  }

  const regularBoxCount = rounds
    .filter((item) => !item.is_yongcha)
    .reduce((sum, item) => sum + Number(item.box_count || 0), 0);
  const yongchaHouseholdCount = rounds
    .filter((item) => item.is_yongcha)
    .reduce((sum, item) => sum + Number(item.household_count || 0), 0);
  const hasMixedYongcha =
    rounds.some((item) => item.is_yongcha) &&
    rounds.some((item) => !item.is_yongcha);

  return { regularBoxCount, yongchaHouseholdCount, hasMixedYongcha };
}

function normalizeVehicleNumberInput(value: string) {
  return String(value || "").toUpperCase().replace(/[\s-]/g, "");
}

function formatDateKey(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(
    date.getDate()
  ).padStart(2, "0")}`;
}

function getInspectionReminderDaysLeft(value: string): number | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value.trim());
  if (!match) return null;

  const [, year, month, day] = match;
  const target = new Date(Number(year), Number(month) - 1, Number(day));
  const today = new Date();
  target.setHours(0, 0, 0, 0);
  today.setHours(0, 0, 0, 0);

  return Math.round((target.getTime() - today.getTime()) / 86400000);
}

function getInspectionReminderHideKey(inspectionDate: string, todayKey: string) {
  return `${INSPECTION_REMINDER_HIDE_PREFIX}.${inspectionDate}.${todayKey}`;
}

function getWorkGuideHideKey(name: string, teamCode: string) {
  return `${WORK_GUIDE_HIDE_PREFIX}.${normalizeSecureStoreKeyPart(
    teamCode
  )}.${normalizeSecureStoreKeyPart(name)}`;
}

function isDoublePointEventActive(now = new Date()) {
  const eventEnd = new Date(`${DOUBLE_EVENT_END_DATE}T23:59:59`);
  return now.getTime() <= eventEnd.getTime();
}

function getCurrentWorkPointReward(now = new Date()) {
  return isDoublePointEventActive(now)
    ? DOUBLE_EVENT_WORK_POINT_REWARD
    : BASE_WORK_POINT_REWARD;
}

function getWorkPointGuideText(now = new Date()) {
  if (isDoublePointEventActive(now)) {
    return `근무 기록 조건 충족 시 기본 ${BASE_WORK_POINT_REWARD}P, 5월 31일까지 2배 이벤트로 ${DOUBLE_EVENT_WORK_POINT_REWARD}P가 적립됩니다.`;
  }
  return `근무 기록 조건 충족 시 기본 ${BASE_WORK_POINT_REWARD}P가 적립됩니다.`;
}

function getWorkPointGuideTitle(now = new Date()) {
  return isDoublePointEventActive(now) ? "5월 31일까지 2배 이벤트" : "근무 기록 포인트 안내";
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
  const [showPayrollModal, setShowPayrollModal] = useState(false);
  const [showInspectionModal, setShowInspectionModal] = useState(false);
  const [showToolActions, setShowToolActions] = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [newPasswordConfirm, setNewPasswordConfirm] = useState("");
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [vehicleSaving, setVehicleSaving] = useState(false);
  const [payrollSaving, setPayrollSaving] = useState(false);
  const [inspectionSaving, setInspectionSaving] = useState(false);
  const [vehicleNumber, setVehicleNumber] = useState("");
  const [vehicleNumberDraft, setVehicleNumberDraft] = useState("");
  const [serverVehicleNumber, setServerVehicleNumber] = useState("");
  const [bankName, setBankName] = useState("");
  const [bankNameDraft, setBankNameDraft] = useState("");
  const [bankAccountNumber, setBankAccountNumber] = useState("");
  const [bankAccountNumberDraft, setBankAccountNumberDraft] = useState("");
  const [vehicleInspectionDate, setVehicleInspectionDate] = useState("");
  const [vehicleInspectionDateDraft, setVehicleInspectionDateDraft] = useState("");
  const [sessionRunning, setSessionRunning] = useState(false);
  const [sessionBusy, setSessionBusy] = useState(false);
  const [sessionSignalChecking, setSessionSignalChecking] = useState(false);
  const [showInquiryModal, setShowInquiryModal] = useState(false);
  const [selectedInquiry, setSelectedInquiry] = useState<SettlementInquiryDetailResponse | null>(null);
  const [inquiryLoading, setInquiryLoading] = useState(false);
  const [inquirySubmitting, setInquirySubmitting] = useState(false);
  const [inquiryMessage, setInquiryMessage] = useState("");
  const [showPointModal, setShowPointModal] = useState(false);
  const [pointBalance, setPointBalance] = useState(0);
  const [pointAvailable, setPointAvailable] = useState(0);
  const [pointItems, setPointItems] = useState<PointRedemptionItem[]>([]);
  const [pendingRedemptions, setPendingRedemptions] = useState<PointRedemption[]>([]);
  const [recentRedemptions, setRecentRedemptions] = useState<PointRedemption[]>([]);
  const [pointLoading, setPointLoading] = useState(false);
  const [pointRedeemingKey, setPointRedeemingKey] = useState<string | null>(null);
  const { message, reload: reloadAppMessages } = useAppMessages();
  const inspectionReminderShownKeyRef = useRef<string | null>(null);
  const workGuideShownKeyRef = useRef<string | null>(null);

  const monthStr = `${year}-${String(month).padStart(2, "0")}`;
  const doublePointEventActive = isDoublePointEventActive();
  const workPointGuideTitle = doublePointEventActive
    ? message("work_point_double_event_title", getWorkPointGuideTitle())
    : message("work_point_guide_title", getWorkPointGuideTitle());
  const workPointGuideText = doublePointEventActive
    ? message("work_point_double_event_body_template", getWorkPointGuideText(), {
        base_points: BASE_WORK_POINT_REWARD,
        event_points: DOUBLE_EVENT_WORK_POINT_REWARD,
        event_end: "5월 31일",
      })
    : message("work_point_guide_body_template", getWorkPointGuideText(), {
        base_points: BASE_WORK_POINT_REWARD,
      });
  const cancelLabel = message("generic_cancel_label", "취소");
  const dayLabels = useMemo(
    () => [
      message("weekday_monday_short", "월"),
      message("weekday_tuesday_short", "화"),
      message("weekday_wednesday_short", "수"),
      message("weekday_thursday_short", "목"),
      message("weekday_friday_short", "금"),
      message("weekday_saturday_short", "토"),
      message("weekday_sunday_short", "일"),
    ],
    [message]
  );

  const loadAppMessageConfig = useCallback(async () => {
    await reloadAppMessages();
  }, [reloadAppMessages]);

  const showConfirmAlert = useCallback(
    (
      title: string,
      body: string,
      confirmText: string,
      cancelText: string = cancelLabel
    ) =>
      new Promise<boolean>((resolve) => {
        Alert.alert(title, body, [
          {
            text: cancelText,
            style: "cancel",
            onPress: () => resolve(false),
          },
          {
            text: confirmText,
            onPress: () => resolve(true),
          },
        ]);
      }),
    [cancelLabel]
  );

  const configureNativeWorkSessionSync = useCallback(
    async (backgroundLocationGranted?: boolean) => {
      try {
        let accessToken = await getStoredAccessToken();
        if (!accessToken) {
          accessToken = await api.refreshToken();
        }
        if (!accessToken) {
          return;
        }
        const resolvedBackgroundLocationGranted =
          backgroundLocationGranted ??
          (await hasBackgroundLocationPermission().catch(() => false));
        await configureWorkSessionServerSync(
          API_BASE_URL,
          accessToken,
          getClientAppVersion(),
          resolvedBackgroundLocationGranted
        );
      } catch {
        // Native checkpoint sync is a recovery layer; foreground recording must continue.
      }
    },
    []
  );

  const maybeShowInspectionReminder = useCallback(async (inspectionDate: string) => {
    const normalizedDate = inspectionDate.trim();
    if (!normalizedDate) return;

    const daysLeft = getInspectionReminderDaysLeft(normalizedDate);
    if (daysLeft === null || daysLeft < 0 || daysLeft > 3) return;

    const todayKey = formatDateKey(new Date());
    const reminderKey = getInspectionReminderHideKey(normalizedDate, todayKey);
    if (inspectionReminderShownKeyRef.current === reminderKey) {
      return;
    }

    try {
      const hiddenToday = await SecureStore.getItemAsync(reminderKey);
      if (hiddenToday === "1") {
        inspectionReminderShownKeyRef.current = reminderKey;
        return;
      }
    } catch {}

    inspectionReminderShownKeyRef.current = reminderKey;
    Alert.alert(
      "알림",
      `검사 일자 ${daysLeft}일 전입니다! 일정에 참고해주세요!`,
      [
        {
          text: "오늘 하루 보지 않기",
          onPress: () => {
            inspectionReminderShownKeyRef.current = reminderKey;
            void SecureStore.setItemAsync(reminderKey, "1").catch(() => undefined);
          },
        },
        { text: "확인" },
      ]
    );
  }, []);

  const maybeShowWorkGuide = useCallback(
    async (
      nextProfileName = profileName,
      nextProfileTeamCode = profileTeamCode
    ) => {
      const normalizedName = nextProfileName.trim();
      const normalizedTeamCode = nextProfileTeamCode.trim();
      if (!normalizedName || !normalizedTeamCode) return;

      const guideKey = getWorkGuideHideKey(normalizedName, normalizedTeamCode);
      if (workGuideShownKeyRef.current === guideKey) {
        return;
      }

      try {
        const hiddenGlobally = await SecureStore.getItemAsync(WORK_GUIDE_GLOBAL_HIDE_KEY);
        if (hiddenGlobally === "1") {
          workGuideShownKeyRef.current = guideKey;
          return;
        }
        const hidden = await SecureStore.getItemAsync(guideKey);
        if (hidden === "1") {
          workGuideShownKeyRef.current = guideKey;
          return;
        }
      } catch {}

      workGuideShownKeyRef.current = guideKey;
      Alert.alert(
        "근무 기록 안내",
        [
          "회차별 마지막 배송이 끝나면 반드시 근무종료 버튼을 눌러주세요.",
        ].join("\n"),
        [
          {
            text: "다시 보지 않기",
            onPress: () => {
              workGuideShownKeyRef.current = guideKey;
              void SecureStore.setItemAsync(WORK_GUIDE_GLOBAL_HIDE_KEY, "1").catch(() => undefined);
              void SecureStore.setItemAsync(guideKey, "1").catch(() => undefined);
            },
          },
          { text: "확인" },
        ]
      );
    },
    [profileName, profileTeamCode]
  );

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

  const applyPointSummary = useCallback((summary: PointSummaryResponse) => {
    setPointBalance(summary.balance || 0);
    setPointAvailable(summary.available_points || 0);
    setPointItems(summary.items || []);
    setPendingRedemptions(summary.pending_redemptions || []);
    setRecentRedemptions(summary.recent_redemptions || []);
  }, []);

  const loadPoints = useCallback(
    async (options: { silent?: boolean } = {}) => {
      const { silent = false } = options;
      if (!silent) {
        setPointLoading(true);
      }
      const pointRes = await api.getPoints();
      if (pointRes.data) {
        applyPointSummary(pointRes.data);
      } else if (pointRes.error && !silent) {
        Alert.alert("오류", pointRes.error);
      }
      setPointLoading(false);
    },
    [applyPointSummary]
  );

  const fetchData = useCallback(async () => {
    setLoading(true);
    await loadAppMessageConfig().catch(() => undefined);
    const profileRes = await api.getProfile();
    if (profileRes.data) {
      setProfileName(profileRes.data.name);
      setProfileTeamCode(profileRes.data.team_code);
      setServerVehicleNumber((profileRes.data.vehicle_number || "").trim());
      const nextBankName = (profileRes.data.bank_name || "").trim();
      const nextBankAccountNumber = (profileRes.data.bank_account_number || "").trim();
      const nextInspectionDate = profileRes.data.vehicle_inspection_date || "";
      setBankName(nextBankName);
      setBankNameDraft(nextBankName);
      setBankAccountNumber(nextBankAccountNumber);
      setBankAccountNumberDraft(nextBankAccountNumber);
      setVehicleInspectionDate(nextInspectionDate);
      setVehicleInspectionDateDraft(nextInspectionDate);
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
    } else if (profileRes.error?.includes("세션") || profileRes.error?.includes("만료")) {
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
    await loadPoints({ silent: true });
    await maybeShowWorkGuide(
      profileRes.data?.name || profileName,
      profileRes.data?.team_code || profileTeamCode
    );
    if (profileRes.data?.vehicle_inspection_date) {
      void maybeShowInspectionReminder(profileRes.data.vehicle_inspection_date);
    }
    setLoading(false);
  }, [loadAppMessageConfig, loadPoints, loadSettlements, maybeShowInspectionReminder, maybeShowWorkGuide, navigation, passwordChangeRequired, profileName, profileTeamCode]);

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
      const resolvedVehicle =
        sessionState.running && sessionState.vehicleNumber
          ? sessionState.vehicleNumber
          : serverVehicleNumber || storedVehicle;
      setVehicleNumber(resolvedVehicle);
      setVehicleNumberDraft(resolvedVehicle);
      setSessionRunning(sessionState.running);
    })();
    return () => {
      mounted = false;
    };
  }, [profileName, profileTeamCode, serverVehicleNumber]);

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
    if (!sessionRunning || !vehicleNumber.trim()) {
      return;
    }

    const syncHeartbeat = async () => {
      const backgroundLocationGranted =
        await hasBackgroundLocationPermission().catch(() => false);
      await configureNativeWorkSessionSync(backgroundLocationGranted);
      await api.heartbeatWorkSessionLive(
        vehicleNumber.trim(),
        backgroundLocationGranted
      );
    };

    void syncHeartbeat();
    const interval = setInterval(() => {
      void syncHeartbeat();
    }, 60000);

    return () => clearInterval(interval);
  }, [configureNativeWorkSessionSync, sessionRunning, vehicleNumber]);

  useEffect(() => {
    if (passwordChangeRequired || showInquiryModal) {
      return;
    }

    const interval = setInterval(() => {
      void loadSettlements({ silent: true });
      void loadPoints({ silent: true });
    }, 3000);

    return () => clearInterval(interval);
  }, [loadPoints, loadSettlements, passwordChangeRequired, showInquiryModal]);

  useEffect(() => {
    if (passwordChangeRequired) {
      return;
    }

    const interval = setInterval(() => {
      void loadAppMessageConfig();
    }, 15000);

    return () => clearInterval(interval);
  }, [loadAppMessageConfig, passwordChangeRequired]);

  useEffect(() => {
    const subscription = AppState.addEventListener("change", (state) => {
      if (state === "active" && !passwordChangeRequired && !showInquiryModal) {
        void loadAppMessageConfig();
        void loadSettlements({ silent: true });
        void loadPoints({ silent: true });
      }
    });

    return () => subscription.remove();
  }, [loadAppMessageConfig, loadPoints, loadSettlements, passwordChangeRequired, showInquiryModal]);

  const updateInquiryBadge = (date: string, inquiryStatus: SettlementDay["inquiry_status"]) => {
    setSettlements((prev) => prev.map((item) => (item.date === date ? { ...item, inquiry_status: inquiryStatus } : item)));
  };

  const ensureProfileIdentity = () => {
    if (profileName.trim() && profileTeamCode.trim()) return true;
    Alert.alert("알림", "사용자 정보를 다시 불러온 후 시도해 주세요.");
    return false;
  };

  const isSessionExpiredError = (error?: string) =>
    Boolean(
      error &&
        (error.includes("?몄뀡") ||
          error.includes("留뚮즺") ||
          error.includes("세션") ||
          error.includes("만료"))
    );

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
    const trimmedVehicleNumber = normalizeVehicleNumberInput(vehicleNumberDraft);
    if (passwordChangeRequired && !trimmedVehicleNumber) return Alert.alert("알림", "차량번호를 입력해 주세요.");
    if (passwordChangeRequired && !ensureProfileIdentity()) return;
    setPasswordSaving(true);
    const { data, error } = await api.changePassword(
      newPassword,
      newPasswordConfirm,
      passwordChangeRequired ? trimmedVehicleNumber : undefined
    );
    if (!error && passwordChangeRequired) {
      await saveVehicleNumber(profileName, profileTeamCode, trimmedVehicleNumber);
      setServerVehicleNumber(trimmedVehicleNumber);
      setVehicleNumber(trimmedVehicleNumber);
      setVehicleNumberDraft(trimmedVehicleNumber);
    }
    setPasswordSaving(false);
    if (error) {
      if (error.includes("세션") || error.includes("만료")) {
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
    const trimmedVehicleNumber = normalizeVehicleNumberInput(vehicleNumberDraft);
    if (!trimmedVehicleNumber) return Alert.alert("알림", "차량번호를 입력해 주세요.");
    if (!ensureProfileIdentity()) return;
    setVehicleSaving(true);
    const { data, error } = await api.updateVehicleNumber(trimmedVehicleNumber);
    setVehicleSaving(false);
    if (error) {
      if (error.includes("세션") || error.includes("만료")) {
        await clearTokens();
        navigation.replace("Login");
        return;
      }
      Alert.alert("오류", error);
      return;
    }
    const normalizedVehicleNumber = data?.vehicle_number?.trim() || trimmedVehicleNumber;
    await saveVehicleNumber(profileName, profileTeamCode, normalizedVehicleNumber);
    setServerVehicleNumber(normalizedVehicleNumber);
    setVehicleNumber(normalizedVehicleNumber);
    setVehicleNumberDraft(normalizedVehicleNumber);
    setShowVehicleModal(false);
    Alert.alert("완료", "차량번호가 저장되었습니다.");
  };


  const handleSavePayrollAccount = async () => {
    const trimmedBankName = bankNameDraft.trim();
    const trimmedAccountNumber = bankAccountNumberDraft.trim();
    if (!trimmedBankName) return Alert.alert("알림", "은행명을 입력해 주세요.");
    if (!trimmedAccountNumber) return Alert.alert("알림", "계좌번호를 입력해 주세요.");
    if (!ensureProfileIdentity()) return;
    setPayrollSaving(true);
    const { data, error } = await api.updatePayrollAccount(
      trimmedBankName,
      trimmedAccountNumber
    );
    setPayrollSaving(false);
    if (error) {
      if (isSessionExpiredError(error)) {
        await clearTokens();
        navigation.replace("Login");
        return;
      }
      Alert.alert("오류", error);
      return;
    }
    const nextBankName = data?.bank_name?.trim() || trimmedBankName;
    const nextAccountNumber =
      data?.bank_account_number?.trim() || trimmedAccountNumber;
    setBankName(nextBankName);
    setBankNameDraft(nextBankName);
    setBankAccountNumber(nextAccountNumber);
    setBankAccountNumberDraft(nextAccountNumber);
    setShowPayrollModal(false);
    Alert.alert("완료", "급여계좌가 저장되었습니다.");
  };

  const handleSaveVehicleInspectionDate = async () => {
    const trimmedDate = vehicleInspectionDateDraft.trim();
    if (!trimmedDate) return Alert.alert("알림", "검사일자를 선택해 주세요.");
    if (!/^\d{4}-\d{2}-\d{2}$/.test(trimmedDate)) {
      return Alert.alert("알림", "검사일자는 YYYY-MM-DD 형식으로 입력해 주세요.");
    }
    if (!ensureProfileIdentity()) return;
    setInspectionSaving(true);
    const { data, error } = await api.updateVehicleInspectionDate(trimmedDate);
    setInspectionSaving(false);
    if (error) {
      if (isSessionExpiredError(error)) {
        await clearTokens();
        navigation.replace("Login");
        return;
      }
      Alert.alert("오류", error);
      return;
    }
    const nextDate = data?.vehicle_inspection_date || trimmedDate;
    setVehicleInspectionDate(nextDate);
    setVehicleInspectionDateDraft(nextDate);
    setShowInspectionModal(false);
    Alert.alert("완료", "검사일자가 저장되었습니다.");
  };

  const openInquiry = async (date: string) => {
    const currentDay = settlements.find((item) => item.date === date);
    const clearAnsweredBadge = currentDay?.inquiry_status === "answered";

    if (clearAnsweredBadge) {
      updateInquiryBadge(date, null);
    }

    setInquiryLoading(true);
    setShowInquiryModal(true);
    setInquiryMessage("");
    setSelectedInquiry(null);
    const { data, error } = await api.getSettlementInquiry(date);
    setInquiryLoading(false);
    if (error || !data) {
      if (clearAnsweredBadge) {
        updateInquiryBadge(date, "answered");
      }
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

  const openPointExchange = async () => {
    setShowPointModal(true);
    await loadPoints();
  };

  const handleRedeemPoint = async (item: PointRedemptionItem) => {
    if (pointAvailable < item.cost_points) {
      Alert.alert("포인트 부족", "사용 가능한 포인트가 부족합니다.");
      return;
    }

    Alert.alert("포인트 교환", `${item.name} ${item.cost_points.toLocaleString()}P를 신청할까요?`, [
      { text: "취소", style: "cancel" },
      {
        text: "신청",
        onPress: async () => {
          setPointRedeemingKey(item.key);
          const { data, error } = await api.redeemPoints(item.key);
          setPointRedeemingKey(null);
          if (error || !data) {
            Alert.alert("오류", error || "포인트 교환 신청에 실패했습니다.");
            return;
          }
          applyPointSummary(data);
          Alert.alert("완료", "관리자 확인 대기 목록에 등록되었습니다.");
        },
      },
    ]);
  };

  const openAppPermissionSettings = async () => {
    try {
      await Linking.openSettings();
    } catch {
      Alert.alert("오류", "앱 설정 화면을 열 수 없습니다.");
    }
  };

  const promptAlwaysAllowLocation = () => {
    Alert.alert(
      "위치 권한 필요",
      "위치 권한은 항상 허용으로 설정되어야 합니다. 앱 설정으로 이동해 위치 권한을 변경해 주세요.",
      [
        { text: "취소", style: "cancel" },
        {
          text: "설정 열기",
          onPress: () => {
            void openAppPermissionSettings();
          },
        },
      ]
    );
  };

  const handleStartSession = async () => {
    const trimmedVehicleNumber = vehicleNumber.trim();
    if (!trimmedVehicleNumber) {
      return Alert.alert("안내", "차량번호를 먼저 등록해 주세요.");
    }
    setSessionBusy(true);
    try {
      await loadAppMessageConfig().catch(() => undefined);
      const disclosureConfirmed = await showConfirmAlert(
        message("background_location_disclosure_title", "근무 기록 위치 안내"),
        message(
          "background_location_disclosure_body",
          "근무 시작 후 앱이 꺼져 있거나 다른 앱을 사용 중이어도 배송 이동 경로와 근무 기록을 저장하기 위해 위치 정보에 계속 액세스합니다.\n차량 근처에서 근무를 시작했는지 확인하기 위해 차량 BLE 신호도 함께 확인합니다."
        ),
        message("background_location_disclosure_confirm_label", "계속"),
        message("background_location_disclosure_cancel_label", "취소")
      );
      if (!disclosureConfirmed) {
        return;
      }
      const permissionResult = await requestWorkSessionPermissions();
      if (!permissionResult.granted) {
        return Alert.alert(
          "권한 필요",
          "위치, 블루투스, 알림 권한이 있어야 근무 기록을 시작할 수 있습니다."
        );
      }
      if (!permissionResult.backgroundLocationGranted) {
        promptAlwaysAllowLocation();
        return;
      }
      await configureNativeWorkSessionSync(permissionResult.backgroundLocationGranted);
      setSessionSignalChecking(true);
      const hasSignal = await startWorkSessionWithSignalCheck(
        profileName,
        trimmedVehicleNumber,
        2000
      );
      if (!hasSignal) {
        Alert.alert(
          "안내",
          "차량에 꽂은 USB 번호와 입력하신 차량번호가 일치하는지 확인해주세요"
        );
        return;
      }
      const { error: liveError } = await api.startWorkSessionLive(
        trimmedVehicleNumber,
        permissionResult.backgroundLocationGranted
      );
      setSessionRunning(true);
      if (liveError && !isSessionExpiredError(liveError)) {
        Alert.alert("안내", "실시간 근무 현황 연동에 실패했습니다.\n" + liveError);
      }
      Alert.alert("시작", "근무를 시작합니다. 안전 운행하세요!");
    } catch (error: any) {
      Alert.alert("오류", error?.message || "근무 기록을 시작할 수 없습니다.");
    } finally {
      setSessionSignalChecking(false);
      setSessionBusy(false);
    }
  };
  const handleStopSession = async () => {
    const sessionSummary = await getWorkSessionSummary().catch(() => null);
    const expectedRewardPoints =
      sessionSummary?.hasRssiSignal &&
      (sessionSummary.cameraEndCount ?? 0) >= WORK_POINT_MIN_CAMERA_END_COUNT
        ? getCurrentWorkPointReward()
        : 0;

    Alert.alert("근무 종료", "근무를 종료하시겠습니까?", [
      { text: "취소", style: "cancel" },
      {
        text: "확인",
        onPress: async () => {
          setSessionBusy(true);
          try {
            const result = await stopWorkSession();
            setSessionRunning(false);
            const backgroundLocationGranted =
              await hasBackgroundLocationPermission().catch(() => false);
            await api.stopWorkSessionLive(
              result.vehicleNumber || vehicleNumber,
              backgroundLocationGranted
            );

            if (!result.csvContent || !result.fileName) {
              throw new Error("업로드할 근무 기록을 만들 수 없습니다.");
            }

            const { data, error } = await api.uploadWorkSession(
              result.csvContent,
              result.fileName,
              result.vehicleNumber
            );
            if (error) {
              throw new Error(error);
            }

            if (data) {
              setPointBalance(data.point_balance || 0);
            }
            await loadPoints({ silent: true });
            const pointAwarded = Boolean(data?.point_awarded);
            const pointAwardPoints = Number(data?.point_award_points || expectedRewardPoints || 0);
            if (pointAwarded) {
              Alert.alert(
                "포인트 획득",
                pointAwardPoints > 0
                  ? `포인트를 획득했습니다!\n${pointAwardPoints.toLocaleString()}P가 적립되었습니다.`
                  : "포인트를 획득했습니다!"
              );
            } else {
              Alert.alert(
                "포인트 미획득",
                "포인트를 획득하지 못했습니다. 정상적으로 근무를 종료하셨다면, 위치 정보가 항상 허용으로 되어있는지 확인해주세요",
                [
                  {
                    text: "권한 확인",
                    onPress: () => {
                      void openAppPermissionSettings();
                    },
                  },
                  { text: "닫기", style: "cancel" },
                ]
              );
            }
          } catch (error: any) {
            Alert.alert("오류", error?.message || "근무 기록을 종료할 수 없습니다.");
          } finally {
            setSessionBusy(false);
          }
        },
      },
    ]);
  };

  const calendarWeeks = useMemo(() => buildCalendarWeeks(year, month, settlements), [year, month, settlements]);
  const selectedInquirySummary = useMemo<InquirySummary | null>(() => {
    if (!selectedInquiry) {
      return null;
    }

    const currentDay = settlements.find((item) => item.date === selectedInquiry.date);
    if (!currentDay) {
      return null;
    }

    return {
      boxCount: currentDay.box_count,
      adjustmentAmount: currentDay.adjustment_amount ?? 0,
      amount: currentDay.amount,
    };
  }, [selectedInquiry, settlements]);
  const today = new Date();
  const isCurrentMonth = today.getFullYear() === year && today.getMonth() + 1 === month;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}><View style={styles.monthSelector}>
        <TouchableOpacity onPress={() => (month === 1 ? (setYear((v) => v - 1), setMonth(12)) : setMonth((v) => v - 1))} hitSlop={HIT_SLOP}><Ionicons name="chevron-back" size={24} color={colors.textPrimary} /></TouchableOpacity>
        <Text style={styles.monthTitle}>{message("calendar_month_title_template", "{year}년 {month}월", { year, month })}</Text>
        <TouchableOpacity onPress={() => (month === 12 ? (setYear((v) => v + 1), setMonth(1)) : setMonth((v) => v + 1))} hitSlop={HIT_SLOP}><Ionicons name="chevron-forward" size={24} color={colors.textPrimary} /></TouchableOpacity>
      </View></View>

      <View style={styles.profileRow}>
        <View style={styles.profilePill}><Ionicons name="person-outline" size={18} color={colors.textSecondary} /><Text style={styles.profileName}>{profileName}</Text><Text style={styles.profileVehicle}>{vehicleNumber ? `· ${vehicleNumber}` : `· ${message("calendar_vehicle_missing_label", "차량 미등록")}`}</Text></View>
        <TouchableOpacity style={[styles.toolButton, styles.logoutButton]} onPress={handleLogout}><Text style={styles.toolButtonText}>{message("logout_confirm_button_label", "로그아웃")}</Text></TouchableOpacity>
      </View>

      <View style={styles.toolToggleRow}>
        <TouchableOpacity style={styles.toolToggleButton} onPress={() => setShowToolActions((prev) => !prev)}>
          <Ionicons name={showToolActions ? "chevron-up" : "chevron-down"} size={16} color={colors.textPrimary} />
          <Text style={styles.toolToggleText}>{showToolActions ? message("settings_collapse_label", "설정 접기") : message("settings_expand_label", "설정 펼치기")}</Text>
        </TouchableOpacity>
      </View>

      {showToolActions ? (
        <View style={styles.actionRow}>
          <TouchableOpacity style={[styles.toolButton, styles.actionButton]} onPress={() => setShowPasswordModal(true)}><Text style={styles.toolButtonText}>{message("password_change_button_label", "비밀번호 변경")}</Text></TouchableOpacity>
          <TouchableOpacity style={[styles.toolButton, styles.actionButton, (sessionRunning || sessionBusy) && styles.buttonDisabled]} onPress={() => setShowVehicleModal(true)} disabled={sessionRunning || sessionBusy}><Text style={styles.toolButtonText}>{message("vehicle_number_change_button_label", "차량번호 변경")}</Text></TouchableOpacity>
          <TouchableOpacity style={[styles.toolButton, styles.actionButton]} onPress={() => setShowPayrollModal(true)}><Text style={styles.toolButtonText}>{message("payroll_account_change_button_label", "급여계좌 변경")}</Text></TouchableOpacity>
          <TouchableOpacity style={[styles.toolButton, styles.actionButton]} onPress={() => setShowInspectionModal(true)}><Text style={styles.toolButtonText}>{message("inspection_date_register_button_label", "검사일자 등록")}</Text></TouchableOpacity>
        </View>
      ) : null}

      <View style={styles.dayHeaderRow}>{dayLabels.map((label, index) => <Text key={`${index}-${label}`} style={[styles.dayHeaderText, index === 5 && { color: colors.saturdayBlue }, index === 6 && { color: colors.sundayRed }]}>{label}</Text>)}</View>

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
                      {(cell.regularBoxCount ?? cell.boxCount ?? 0) > 0 ? (
                        <Text style={[styles.cellBox, isToday && { color: colors.whiteAlpha60 }]}>{cell.regularBoxCount ?? cell.boxCount}</Text>
                      ) : null}
                      {(cell.yongchaHouseholdCount ?? 0) > 0 ? (
                        <Text style={[styles.cellHousehold, isToday && { color: colors.whiteAlpha60 }]}>{cell.yongchaHouseholdCount}</Text>
                      ) : null}
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
          {sessionBusy ? <ActivityIndicator color={colors.textInverse} /> : <Text style={styles.workButtonText}>{sessionRunning ? message("work_stop_button_label", "근무종료") : message("work_start_button_label", "근무시작")}</Text>}
        </TouchableOpacity>
      </View>

      <Modal visible={sessionSignalChecking} transparent animationType="fade">
        <View style={styles.modalBackdrop}>
          <View style={styles.modalCenter}>
            <View style={[styles.modalCard, styles.signalCheckCard]}>
              <ActivityIndicator size="large" color={colors.accentBlue} />
              <Text style={styles.modalTitle}>{message("signal_check_title", "잠시 대기")}</Text>
              <Text style={[styles.modalSubtitle, styles.signalCheckText]}>
                {message("signal_check_body", "RSSI 신호를 확인하고 있습니다.")}
              </Text>
            </View>
          </View>
        </View>
      </Modal>

      {!passwordChangeRequired ? (
        <>
          <View style={styles.pointPanel}>
            <View style={styles.pointInfoBox}>
              <View style={styles.pointInfoIcon}>
                <Ionicons name="diamond-outline" size={18} color={colors.accentBlue} />
              </View>
              <View style={styles.pointInfoText}>
                <Text style={styles.pointInfoLabel}>{message("point_balance_label", "보유 포인트")}</Text>
                <Text style={styles.pointInfoValue}>{pointBalance.toLocaleString()}P</Text>
                <Text style={styles.pointInfoSub}>{message("point_available_label_template", "사용 가능 {points}P", { points: pointAvailable.toLocaleString() })}</Text>
              </View>
            </View>
            <TouchableOpacity style={styles.pointShopButton} activeOpacity={0.85} onPress={openPointExchange}>
              <Ionicons name="gift-outline" size={18} color={colors.textInverse} />
              <View style={styles.pointShopTextWrap}>
                <Text style={styles.pointShopTitle}>{message("point_shop_title", "포인트 상점")}</Text>
                <Text style={styles.pointShopSub}>{message("point_shop_subtitle", "교환 신청")}</Text>
              </View>
              <Ionicons name="chevron-forward" size={18} color={colors.whiteAlpha60} />
            </TouchableOpacity>
          </View>
          <View style={styles.pointEventBanner}>
            <View style={styles.pointEventIcon}>
              <Ionicons name="flash-outline" size={18} color={colors.accentBlue} />
            </View>
            <View style={styles.pointEventTextWrap}>
              <Text style={styles.pointEventTitle}>{workPointGuideTitle}</Text>
              <Text style={styles.pointEventBody}>{workPointGuideText}</Text>
            </View>
          </View>
        </>
      ) : null}

      <View style={styles.summary}>
        <View style={styles.summaryHalf}><Text style={styles.summaryLabel}>{message("calendar_total_boxes_label", "이번 달 총 박스")}</Text><Text style={styles.summaryValue}>{message("calendar_total_boxes_value_template", "{boxes} 박스", { boxes: totalBoxes.toLocaleString() })}</Text></View>
        <View style={styles.summaryDivider} />
        <View style={styles.summaryHalf}><Text style={styles.summaryLabel}>{message("calendar_total_amount_label", "이번 달 총 금액")}</Text><Text style={styles.summaryValue}>{message("amount_won_template", "{amount}원", { amount: Number(totalAmount).toLocaleString() })}</Text></View>
      </View>

      {passwordChangeRequired ? <View style={styles.lockedOverlay} /> : null}

      <InquiryModal visible={showInquiryModal} loading={inquiryLoading} detail={selectedInquiry} summary={selectedInquirySummary} message={inquiryMessage} setMessage={setInquiryMessage} submitting={inquirySubmitting} onClose={() => { if (!inquirySubmitting) { setShowInquiryModal(false); setSelectedInquiry(null); setInquiryMessage(""); void loadSettlements({ silent: true }); } }} onSubmit={handleSubmitInquiry} />
      <PointExchangeModal
        visible={showPointModal}
        loading={pointLoading}
        balance={pointBalance}
        available={pointAvailable}
        items={pointItems}
        pendingRedemptions={pendingRedemptions}
        recentRedemptions={recentRedemptions}
        redeemingKey={pointRedeemingKey}
        onClose={() => setShowPointModal(false)}
        onRedeem={handleRedeemPoint}
        onRefresh={() => loadPoints()}
      />

      <Modal visible={showPasswordModal} transparent animationType="fade" onRequestClose={() => (!passwordSaving && !passwordChangeRequired ? setShowPasswordModal(false) : null)}>
        <View style={styles.modalBackdrop}><KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.modalCenter}><View style={styles.modalCard}>
          <Text style={styles.modalTitle}>{passwordChangeRequired ? message("password_required_modal_title", "비밀번호를 변경해 주세요") : message("password_change_modal_title", "비밀번호 변경")}</Text>
          <Text style={styles.modalSubtitle}>{passwordChangeRequired ? message("password_required_modal_subtitle", "초기 비밀번호를 변경해 주세요. 차량번호도 함께 입력해야 합니다.") : message("password_change_modal_subtitle", "새 비밀번호 4자리를 입력해 주세요.")}</Text>
          <Field label={message("new_password_label", "새 비밀번호")}><TextInput style={styles.modalInput} value={newPassword} onChangeText={handlePinInput(setNewPassword)} placeholder={message("pin_placeholder", "4자리 숫자")} placeholderTextColor={colors.textMuted} keyboardType="number-pad" secureTextEntry maxLength={4} /></Field>
          <Field label={message("password_confirm_label", "비밀번호 확인")}><TextInput style={styles.modalInput} value={newPasswordConfirm} onChangeText={handlePinInput(setNewPasswordConfirm)} placeholder={message("pin_placeholder", "4자리 숫자")} placeholderTextColor={colors.textMuted} keyboardType="number-pad" secureTextEntry maxLength={4} /></Field>
          {passwordChangeRequired ? (
            <>
              <Field label={message("vehicle_number_label", "차량번호")}>
                <TextInput
                  style={styles.modalInput}
                  value={vehicleNumberDraft}
                  onChangeText={(value) =>
                    setVehicleNumberDraft(normalizeVehicleNumberInput(value))
                  }
                  placeholder={message("vehicle_number_placeholder", "예: 서울00배0000")}
                  placeholderTextColor={colors.textMuted}
                  autoCapitalize="characters"
                  autoCorrect={false}
                />
              </Field>
            </>
          ) : null}
          <View style={styles.modalButtonRow}>
            <TouchableOpacity style={[styles.modalButton, styles.modalCancelButton]} onPress={passwordChangeRequired ? handleForceLogout : () => setShowPasswordModal(false)} disabled={passwordSaving}><Text style={styles.modalCancelButtonText}>{passwordChangeRequired ? message("logout_confirm_button_label", "로그아웃") : message("generic_cancel_label", "취소")}</Text></TouchableOpacity>
            <TouchableOpacity style={[styles.modalButton, passwordSaving && styles.buttonDisabled]} onPress={handleChangePassword} disabled={passwordSaving}>{passwordSaving ? <ActivityIndicator color={colors.textInverse} /> : <Text style={styles.modalButtonText}>{message("generic_apply_label", "적용")}</Text>}</TouchableOpacity>
          </View>
        </View></KeyboardAvoidingView></View>
      </Modal>

      <Modal visible={showVehicleModal} transparent animationType="fade" onRequestClose={() => (!vehicleSaving ? setShowVehicleModal(false) : null)}>
        <View style={styles.modalBackdrop}><KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.modalCenter}><View style={styles.modalCard}>
          <Text style={styles.modalTitle}>{message("vehicle_number_modal_title", "차량번호 변경")}</Text>
          <Text style={styles.modalSubtitle}>{message("vehicle_number_modal_subtitle", "차량번호를 입력해 주세요.")}</Text>
          <Field label={message("vehicle_number_label", "차량번호")}>
            <TextInput
              style={styles.modalInput}
              value={vehicleNumberDraft}
              onChangeText={(value) =>
                setVehicleNumberDraft(normalizeVehicleNumberInput(value))
              }
              placeholder={message("vehicle_number_placeholder", "예: 서울00배0000")}
              placeholderTextColor={colors.textMuted}
              autoCapitalize="characters"
              autoCorrect={false}
            />
          </Field>
          <View style={styles.modalButtonRow}>
            <TouchableOpacity style={[styles.modalButton, styles.modalCancelButton]} onPress={() => setShowVehicleModal(false)} disabled={vehicleSaving}><Text style={styles.modalCancelButtonText}>{message("generic_cancel_label", "취소")}</Text></TouchableOpacity>
            <TouchableOpacity style={[styles.modalButton, vehicleSaving && styles.buttonDisabled]} onPress={handleSaveVehicleNumber} disabled={vehicleSaving}>{vehicleSaving ? <ActivityIndicator color={colors.textInverse} /> : <Text style={styles.modalButtonText}>{message("generic_save_label", "저장")}</Text>}</TouchableOpacity>
          </View>
        </View></KeyboardAvoidingView></View>
      </Modal>

      <Modal visible={showPayrollModal} transparent animationType="fade" onRequestClose={() => (!payrollSaving ? setShowPayrollModal(false) : null)}>
        <View style={styles.modalBackdrop}><KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.modalCenter}><View style={styles.modalCard}>
          <Text style={styles.modalTitle}>{message("payroll_account_modal_title", "급여계좌 변경")}</Text>
          <Text style={styles.modalSubtitle}>{message("payroll_account_modal_subtitle", "은행명과 계좌번호를 저장하면 배송원 관리에 바로 반영됩니다.")}</Text>
          <Field label={message("bank_name_label", "은행")}><TextInput style={styles.modalInput} value={bankNameDraft} onChangeText={setBankNameDraft} placeholder={message("bank_name_placeholder", "예: 국민은행")} placeholderTextColor={colors.textMuted} autoCorrect={false} /></Field>
          <Field label={message("bank_account_number_label", "계좌번호")}><TextInput style={styles.modalInput} value={bankAccountNumberDraft} onChangeText={setBankAccountNumberDraft} placeholder={message("bank_account_number_placeholder", "계좌번호")} placeholderTextColor={colors.textMuted} keyboardType="number-pad" autoCorrect={false} /></Field>
          <View style={styles.modalButtonRow}>
            <TouchableOpacity style={[styles.modalButton, styles.modalCancelButton]} onPress={() => setShowPayrollModal(false)} disabled={payrollSaving}><Text style={styles.modalCancelButtonText}>{message("generic_cancel_label", "취소")}</Text></TouchableOpacity>
            <TouchableOpacity style={[styles.modalButton, payrollSaving && styles.buttonDisabled]} onPress={handleSavePayrollAccount} disabled={payrollSaving}>{payrollSaving ? <ActivityIndicator color={colors.textInverse} /> : <Text style={styles.modalButtonText}>{message("generic_save_label", "저장")}</Text>}</TouchableOpacity>
          </View>
        </View></KeyboardAvoidingView></View>
      </Modal>

      <Modal visible={showInspectionModal} transparent animationType="fade" onRequestClose={() => (!inspectionSaving ? setShowInspectionModal(false) : null)}>
        <View style={styles.modalBackdrop}><KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.modalCenter}><View style={styles.modalCard}>
          <Text style={styles.modalTitle}>{message("inspection_date_modal_title", "검사일자 등록")}</Text>
          <Text style={styles.modalSubtitle}>{message("inspection_date_modal_subtitle", "자동차 검사일자를 YYYY-MM-DD 형식으로 저장합니다.")}</Text>
          <Field label={message("inspection_date_label", "검사일자")}><TextInput style={styles.modalInput} value={vehicleInspectionDateDraft} onChangeText={setVehicleInspectionDateDraft} placeholder={message("inspection_date_placeholder", "2026-04-22")} placeholderTextColor={colors.textMuted} autoCorrect={false} maxLength={10} /></Field>
          <View style={styles.modalButtonRow}>
            <TouchableOpacity style={[styles.modalButton, styles.modalCancelButton]} onPress={() => setShowInspectionModal(false)} disabled={inspectionSaving}><Text style={styles.modalCancelButtonText}>{message("generic_cancel_label", "취소")}</Text></TouchableOpacity>
            <TouchableOpacity style={[styles.modalButton, inspectionSaving && styles.buttonDisabled]} onPress={handleSaveVehicleInspectionDate} disabled={inspectionSaving}>{inspectionSaving ? <ActivityIndicator color={colors.textInverse} /> : <Text style={styles.modalButtonText}>{message("generic_save_label", "저장")}</Text>}</TouchableOpacity>
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
  visible, loading, detail, summary, message, setMessage, submitting, onClose, onSubmit,
}: {
  visible: boolean; loading: boolean; detail: SettlementInquiryDetailResponse | null; summary: InquirySummary | null; message: string; setMessage: (value: string) => void; submitting: boolean; onClose: () => void; onSubmit: () => void;
}) {
  const { message: appMessage } = useAppMessages();
  const [keyboardHeight, setKeyboardHeight] = useState(0);
  const messageScrollRef = useRef<ScrollView | null>(null);
  const displaySummary = summary ?? (detail ? {
    boxCount: detail.box_count,
    adjustmentAmount: detail.adjustment_amount,
    amount: detail.amount,
  } : null);

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

  useEffect(() => {
    if (!visible || !detail) {
      return;
    }

    requestAnimationFrame(() => {
      messageScrollRef.current?.scrollToEnd({ animated: false });
    });
  }, [detail, visible]);

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={styles.modalBackdrop}><KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.flexFill}><View style={[styles.inquiryModalCenter, Platform.OS === "android" && keyboardHeight > 0 ? { paddingBottom: keyboardHeight + 12 } : null]}>
        <View style={[styles.modalCard, styles.inquiryCard]}>
        {loading || !detail ? <View style={styles.loadingCenter}><ActivityIndicator size="large" color={colors.accentBlue} /></View> : <>
          <View style={styles.inquiryHeader}><Text style={styles.modalTitle}>{appMessage("inquiry_modal_title", "정산 문의")}</Text><TouchableOpacity onPress={onClose} hitSlop={HIT_SLOP}><Ionicons name="close" size={22} color={colors.textSecondary} /></TouchableOpacity></View>
          <View style={styles.inquirySummaryRow}>
            <SummaryChip label={appMessage("inquiry_date_label", "날짜")} value={formatDateLabel(detail.date)} />
            <SummaryChip label={appMessage("inquiry_box_count_label", "박스수")} value={appMessage("count_each_template", "{count}개", { count: displaySummary?.boxCount ?? 0 })} />
            {(displaySummary?.adjustmentAmount ?? 0) !== 0 ? <SummaryChip label={appMessage("inquiry_adjustment_amount_label", "조정비용")} value={appMessage("amount_won_template", "{amount}원", { amount: (displaySummary?.adjustmentAmount ?? 0).toLocaleString() })} /> : null}
            <SummaryChip label={appMessage("inquiry_settlement_amount_label", "정산금액")} value={appMessage("amount_won_template", "{amount}원", { amount: (displaySummary?.amount ?? 0).toLocaleString() })} />
          </View>
          <ScrollView ref={messageScrollRef} style={styles.messageScroll} contentContainerStyle={styles.messageList} keyboardShouldPersistTaps="handled" onContentSizeChange={() => messageScrollRef.current?.scrollToEnd({ animated: false })}>
            {detail.messages.length === 0 ? <View style={styles.emptyMessageBox}><Text style={styles.emptyMessageText}>{appMessage("inquiry_empty_message", "박스수나 정산금액이 이상하면 아래에 내용을 남겨 주세요.")}</Text></View> : detail.messages.map((item) => <MessageBubble key={item.id} message={item} />)}
          </ScrollView>
          <View style={styles.inquiryComposer}>
            <TextInput style={styles.inquiryInput} value={message} onChangeText={setMessage} placeholder={appMessage("inquiry_input_placeholder", "문의 내용을 입력해 주세요.")} placeholderTextColor={colors.textMuted} multiline />
            <TouchableOpacity style={[styles.modalButton, styles.inquirySubmitButton, submitting && styles.buttonDisabled]} onPress={onSubmit} disabled={submitting}>{submitting ? <ActivityIndicator color={colors.textInverse} /> : <Text style={styles.modalButtonText}>{appMessage("generic_register_label", "등록")}</Text>}</TouchableOpacity>
          </View>
        </>}
      </View></View></KeyboardAvoidingView></View>
    </Modal>
  );
}

function PointExchangeModal({
  visible,
  loading,
  balance,
  available,
  items,
  pendingRedemptions,
  recentRedemptions,
  redeemingKey,
  onClose,
  onRedeem,
  onRefresh,
}: {
  visible: boolean;
  loading: boolean;
  balance: number;
  available: number;
  items: PointRedemptionItem[];
  pendingRedemptions: PointRedemption[];
  recentRedemptions: PointRedemption[];
  redeemingKey: string | null;
  onClose: () => void;
  onRedeem: (item: PointRedemptionItem) => void;
  onRefresh: () => void;
}) {
  const { message: appMessage } = useAppMessages();
  const doublePointEventActive = isDoublePointEventActive();
  const pointGuideText = doublePointEventActive
    ? appMessage("work_point_double_event_body_template", getWorkPointGuideText(), {
        base_points: BASE_WORK_POINT_REWARD,
        event_points: DOUBLE_EVENT_WORK_POINT_REWARD,
        event_end: "5월 31일",
      })
    : appMessage("work_point_guide_body_template", getWorkPointGuideText(), {
        base_points: BASE_WORK_POINT_REWARD,
      });

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={styles.modalBackdrop}>
        <View style={styles.modalCenter}>
          <View style={[styles.modalCard, styles.pointCard]}>
            <View style={styles.pointHeader}>
              <View>
                <Text style={styles.modalTitle}>{appMessage("point_exchange_modal_title", "포인트 교환")}</Text>
                <Text style={styles.modalSubtitle}>{pointGuideText}</Text>
              </View>
              <TouchableOpacity onPress={onClose} hitSlop={HIT_SLOP}>
                <Ionicons name="close" size={22} color={colors.textSecondary} />
              </TouchableOpacity>
            </View>

            <View style={styles.pointBalanceRow}>
              <View style={styles.pointBalanceBox}>
                <Text style={styles.summaryChipLabel}>{appMessage("point_balance_label", "보유 포인트")}</Text>
                <Text style={styles.pointBalanceValue}>{balance.toLocaleString()}P</Text>
              </View>
              <View style={styles.pointBalanceBox}>
                <Text style={styles.summaryChipLabel}>{appMessage("point_available_short_label", "사용 가능")}</Text>
                <Text style={styles.pointBalanceValue}>{available.toLocaleString()}P</Text>
              </View>
            </View>

            <TouchableOpacity style={styles.pointRefreshButton} onPress={onRefresh} disabled={loading}>
              <Ionicons name="refresh" size={16} color={colors.textPrimary} />
              <Text style={styles.pointRefreshText}>{appMessage("generic_refresh_label", "새로고침")}</Text>
            </TouchableOpacity>

            {loading ? (
              <View style={styles.pointLoading}>
                <ActivityIndicator color={colors.accentBlue} />
              </View>
            ) : (
              <ScrollView style={styles.pointScroll} contentContainerStyle={styles.pointScrollContent}>
                {pendingRedemptions.length > 0 ? (
                  <View style={styles.pointSection}>
                    <Text style={styles.pointSectionTitle}>{appMessage("point_pending_section_title", "관리자 확인 대기")}</Text>
                    {pendingRedemptions.map((item) => (
                      <View key={item.id} style={[styles.pointHistoryItem, styles.pointPendingItem]}>
                        <Text style={styles.pointHistoryName}>{item.item_name}</Text>
                        <Text style={styles.pointHistoryMeta}>{appMessage("point_pending_history_template", "{points}P 대기", { points: item.cost_points.toLocaleString() })}</Text>
                      </View>
                    ))}
                  </View>
                ) : null}

                <View style={styles.pointSection}>
                  <Text style={styles.pointSectionTitle}>{appMessage("point_items_section_title", "교환 목록")}</Text>
                  {items.map((item) => {
                    const disabled = available < item.cost_points || redeemingKey === item.key;
                    return (
                      <TouchableOpacity
                        key={item.key}
                        style={[styles.pointItem, disabled && styles.pointItemDisabled]}
                        onPress={() => onRedeem(item)}
                        disabled={disabled}
                        activeOpacity={0.8}
                      >
                        <View style={styles.pointItemMain}>
                          <Text style={styles.pointItemName}>{item.name}</Text>
                          <Text style={styles.pointItemCost}>{item.cost_points.toLocaleString()}P</Text>
                        </View>
                        {redeemingKey === item.key ? (
                          <ActivityIndicator color={colors.accentBlue} />
                        ) : (
                          <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
                        )}
                      </TouchableOpacity>
                    );
                  })}
                </View>

                {recentRedemptions.length > 0 ? (
                  <View style={styles.pointSection}>
                    <Text style={styles.pointSectionTitle}>{appMessage("point_recent_section_title", "최근 신청")}</Text>
                    {recentRedemptions.slice(0, 5).map((item) => (
                      <View key={item.id} style={styles.pointHistoryItem}>
                        <Text style={styles.pointHistoryName}>{item.item_name}</Text>
                        <Text style={styles.pointHistoryMeta}>
                          {item.cost_points.toLocaleString()}P · {formatRedemptionStatus(item.status, appMessage)}
                        </Text>
                      </View>
                    ))}
                  </View>
                ) : null}
              </ScrollView>
            )}
          </View>
        </View>
      </View>
    </Modal>
  );
}

function SummaryChip({ label, value }: { label: string; value: string }) {
  return <View style={styles.summaryChip}><Text style={styles.summaryChipLabel}>{label}</Text><Text style={styles.summaryChipValue}>{value}</Text></View>;
}

function MessageBubble({ message }: { message: SettlementInquiryMessage }) {
  const { message: appMessage } = useAppMessages();
  const mine = message.author_type === "crew";
  return <View style={[styles.messageRow, mine ? styles.rowEnd : styles.rowStart]}><View style={[styles.messageBubble, mine ? styles.bubbleMine : styles.bubbleOther]}><Text style={[styles.messageAuthor, mine && styles.messageAuthorMine]}>{mine ? appMessage("inquiry_author_me_label", "나") : message.author_name || appMessage("inquiry_author_admin_label", "관리자")}</Text><Text style={[styles.messageContent, mine && styles.messageContentMine]}>{message.content}</Text><Text style={[styles.messageTime, mine && styles.messageTimeMine]}>{formatTimeLabel(message.created_at)}</Text></View></View>;
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

function formatRedemptionStatus(
  status: PointRedemption["status"],
  appMessage: (key: string, fallback: string) => string
) {
  if (status === "PENDING") return appMessage("point_status_pending", "확인 대기");
  if (status === "CONFIRMED") return appMessage("point_status_confirmed", "사용 완료");
  return appMessage("point_status_cancelled", "취소");
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
        const roundDisplay = summarizeRoundDisplay(settlement?.round_summaries || []);
        const hasAnyYongchaRound = roundDisplay.yongchaHouseholdCount > 0;
        cells.push({
          day: currentDay,
          date: settlement?.date,
          boxCount: settlement?.box_count,
          regularBoxCount: hasAnyYongchaRound
            ? roundDisplay.regularBoxCount
            : settlement?.box_count,
          yongchaHouseholdCount: roundDisplay.yongchaHouseholdCount,
          amount: settlement?.amount,
          adjustmentAmount: settlement?.adjustment_amount,
          inquiryStatus: settlement?.inquiry_status ?? null,
        });
        currentDay += 1;
      }
    }
    weeks.push(cells);
  }
  return weeks;
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bgPrimary },
  header: { justifyContent: "center", alignItems: "center", paddingHorizontal: 16, height: 52 },
  monthSelector: { flexDirection: "row", alignItems: "center", gap: 8 },
  monthTitle: { fontFamily: typography.fontFamily, fontSize: 18, fontWeight: "700", color: colors.textPrimary },
  profileRow: { flexDirection: "row", alignItems: "center", gap: 8, paddingHorizontal: 16, paddingBottom: 6 },
  profilePill: { flexDirection: "row", alignItems: "center", gap: 6, flex: 1, paddingVertical: 7, paddingHorizontal: 12, borderRadius: 999, backgroundColor: colors.bgSecondary },
  profileName: { ...typography.caption, color: colors.textPrimary },
  profileVehicle: { ...typography.captionSmall, color: colors.textSecondary, flexShrink: 1 },
  toolToggleRow: { paddingHorizontal: 16, paddingBottom: 6, alignItems: "flex-start" },
  toolToggleButton: { height: 32, borderRadius: 8, borderWidth: 1, borderColor: colors.borderLight, backgroundColor: colors.bgPrimary, flexDirection: "row", alignItems: "center", gap: 6, paddingHorizontal: 10 },
  toolToggleText: { ...typography.captionSmall, color: colors.textPrimary },
  actionRow: { flexDirection: "row", flexWrap: "wrap", gap: 8, paddingHorizontal: 16, paddingBottom: 6 },
  toolButton: { height: 34, paddingHorizontal: 12, borderRadius: 8, borderWidth: 1, borderColor: colors.borderLight, alignItems: "center", justifyContent: "center", backgroundColor: colors.bgPrimary },
  actionButton: { flexBasis: "47%", flexGrow: 1, flexShrink: 0 },
  logoutButton: { flex: 0, backgroundColor: colors.bgSecondary },
  toolButtonText: { ...typography.captionSmall, color: colors.textPrimary },
  dayHeaderRow: { flexDirection: "row", height: 24, alignItems: "center" },
  dayHeaderText: { flex: 1, textAlign: "center", ...typography.captionSmall, color: colors.textMuted },
  calendarGrid: { flex: 1 },
  loadingCenter: { flex: 1, alignItems: "center", justifyContent: "center" },
  weekRow: { flex: 1, flexDirection: "row" },
  cell: { flex: 1, alignItems: "center", justifyContent: "center", paddingVertical: 2, paddingHorizontal: 2, gap: 1, backgroundColor: colors.bgPrimary, position: "relative" },
  cellEmpty: { backgroundColor: colors.cellEmpty },
  cellToday: { backgroundColor: colors.accentLight },
  cellDate: { ...typography.calendarDate, color: colors.textPrimary },
  cellBadge: { position: "absolute", top: 6, right: 7, width: 8, height: 8, borderRadius: 4 },
  badgePending: { backgroundColor: "#9CA3AF" },
  badgeAnswered: { backgroundColor: colors.successGreen },
  cellBox: { ...typography.calendarBox, color: colors.textSecondary },
  cellHousehold: { ...typography.calendarBox, color: colors.sundayRed },
  cellAmount: { ...typography.calendarAmount, color: colors.accentBlue },
  workButtonWrap: { marginHorizontal: 16, marginBottom: 8 },
  workButton: { width: "100%", height: 48, borderRadius: 8, alignItems: "center", justifyContent: "center" },
  workStartButton: { backgroundColor: colors.accentBlue },
  workStopButton: { backgroundColor: colors.sundayRed },
  workButtonText: { ...typography.label, color: colors.textInverse },
  pointPanel: { flexDirection: "row", gap: 10, paddingHorizontal: 16, marginBottom: 8 },
  pointInfoBox: { flex: 1, minHeight: 60, borderRadius: 8, borderWidth: 1, borderColor: colors.borderLight, backgroundColor: colors.bgPrimary, flexDirection: "row", alignItems: "center", gap: 8, paddingHorizontal: 10, paddingVertical: 8 },
  pointInfoIcon: { width: 30, height: 30, borderRadius: 8, backgroundColor: colors.bgSecondary, alignItems: "center", justifyContent: "center" },
  pointInfoText: { flex: 1, gap: 2 },
  pointInfoLabel: { ...typography.summaryLabel, color: colors.textMuted },
  pointInfoValue: { ...typography.summaryValue, color: colors.textPrimary },
  pointInfoSub: { ...typography.summaryLabel, color: colors.textSecondary },
  pointShopButton: { flex: 1, minHeight: 60, borderRadius: 8, backgroundColor: colors.accentBlue, flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8, paddingHorizontal: 10, paddingVertical: 8 },
  pointShopTextWrap: { flex: 1, gap: 2 },
  pointShopTitle: { ...typography.label, color: colors.textInverse },
  pointShopSub: { ...typography.summaryLabel, color: colors.whiteAlpha60 },
  pointEventBanner: { flexDirection: "row", alignItems: "flex-start", gap: 8, marginHorizontal: 16, marginBottom: 8, paddingHorizontal: 10, paddingVertical: 10, borderRadius: 8, borderWidth: 1, borderColor: colors.borderLight, backgroundColor: colors.bgSecondary },
  pointEventIcon: { width: 30, height: 30, borderRadius: 8, backgroundColor: colors.bgPrimary, alignItems: "center", justifyContent: "center" },
  pointEventTextWrap: { flex: 1, gap: 4 },
  pointEventTitle: { ...typography.label, color: colors.textPrimary },
  pointEventBody: { ...typography.bodySmall, color: colors.textSecondary },
  summary: { flexDirection: "row", alignItems: "center", backgroundColor: colors.accentBlue, height: 60, paddingHorizontal: 18 },
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
  signalCheckCard: { alignItems: "center", gap: 12 },
  signalCheckText: { textAlign: "center" },
  inquiryCard: { maxHeight: 680, minHeight: 420 },
  modalTitle: { ...typography.sectionTitle, color: colors.textPrimary },
  modalSubtitle: { ...typography.bodySmall, color: colors.textSecondary },
  modalField: { gap: 8 },
  modalLabel: { ...typography.label, color: colors.textPrimary },
  modalInput: { height: 52, borderRadius: 8, borderWidth: 1, borderColor: colors.borderLight, paddingHorizontal: 16, ...typography.body, color: colors.textPrimary },
  modalUtilityButton: {
    minHeight: 48,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.borderLight,
    backgroundColor: colors.bgSecondary,
    paddingHorizontal: 14,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  modalUtilityButtonText: {
    ...typography.bodySmall,
    color: colors.textPrimary,
    fontWeight: "700",
  },
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
  pointCard: { maxHeight: "86%", paddingBottom: 14 },
  pointHeader: { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between", gap: 12 },
  pointBalanceRow: { flexDirection: "row", gap: 10 },
  pointBalanceBox: { flex: 1, borderRadius: 8, borderWidth: 1, borderColor: colors.borderLight, backgroundColor: colors.bgSecondary, padding: 12, gap: 4 },
  pointBalanceValue: { ...typography.sectionTitle, color: colors.textPrimary },
  pointRefreshButton: { alignSelf: "flex-start", height: 34, borderRadius: 8, borderWidth: 1, borderColor: colors.borderLight, flexDirection: "row", alignItems: "center", gap: 6, paddingHorizontal: 12, backgroundColor: colors.bgPrimary },
  pointRefreshText: { ...typography.captionSmall, color: colors.textPrimary },
  pointLoading: { minHeight: 220, alignItems: "center", justifyContent: "center" },
  pointScroll: { maxHeight: 480 },
  pointScrollContent: { gap: 16, paddingBottom: 6 },
  pointSection: { gap: 8 },
  pointSectionTitle: { ...typography.label, color: colors.textPrimary },
  pointItem: { minHeight: 58, borderRadius: 8, borderWidth: 1, borderColor: colors.borderLight, backgroundColor: colors.bgPrimary, flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 14, paddingVertical: 10, gap: 10 },
  pointItemDisabled: { opacity: 0.45 },
  pointItemMain: { flex: 1, gap: 4 },
  pointItemName: { ...typography.bodySmall, color: colors.textPrimary, fontWeight: "700" },
  pointItemCost: { ...typography.captionSmall, color: colors.accentBlue },
  pointHistoryItem: { borderRadius: 8, backgroundColor: colors.bgSecondary, paddingHorizontal: 12, paddingVertical: 10, gap: 3 },
  pointPendingItem: { borderWidth: 1, borderColor: "#F59E0B", backgroundColor: "#FFFBEB" },
  pointHistoryName: { ...typography.bodySmall, color: colors.textPrimary, fontWeight: "700" },
  pointHistoryMeta: { ...typography.captionSmall, color: colors.textSecondary },
});

