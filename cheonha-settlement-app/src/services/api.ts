import Constants from "expo-constants";
import * as SecureStore from "expo-secure-store";
import { normalizeSecureStoreKeyPart } from "../utils/secureStoreKey";

const envApiBaseUrl = process.env.EXPO_PUBLIC_API_BASE_URL;
const expoExtra =
  (Constants.expoConfig?.extra as
    | { apiBaseUrl?: string; appEnv?: string }
    | undefined) ?? {};
const fallbackApiBaseUrl =
  expoExtra.appEnv === "production"
    ? "http://43.201.160.163"
    : "http://13.124.120.147";
export const API_BASE_URL = (
  envApiBaseUrl ||
  expoExtra.apiBaseUrl ||
  fallbackApiBaseUrl
).replace(/\/+$/, "");

export function getClientAppBuildNumber(): number {
  const expoConfig = Constants.expoConfig as any;
  const manifest = Constants.manifest as any;
  const rawBuild =
    expoConfig?.android?.versionCode ??
    expoConfig?.ios?.buildNumber ??
    Constants.nativeBuildVersion ??
    manifest?.android?.versionCode ??
    0;
  const parsed = Number.parseInt(String(rawBuild || "0"), 10);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function getClientAppVersionName(): string {
  const expoConfig = Constants.expoConfig as any;
  const manifest = Constants.manifest as any;
  return String(
    expoConfig?.version ||
      manifest?.version ||
      Constants.nativeAppVersion ||
      ""
  );
}

export function getClientAppVersion(): string {
  const expoConfig = Constants.expoConfig as any;
  const manifest = Constants.manifest as any;
  const version =
    getClientAppVersionName() ||
    expoConfig?.version ||
    manifest?.version ||
    "";
  const build = getClientAppBuildNumber();
  const label = build ? `${version} (${build})` : version;
  return String(label || "").slice(0, 40);
}

export const PRIVACY_POLICY_URL = `${API_BASE_URL}/privacy/`;
export const TERMS_OF_SERVICE_URL = `${API_BASE_URL}/driver-terms/`;
export const THIRD_PARTY_INFORMATION_URL = `${API_BASE_URL}/data-processing/`;
export const LOCATION_TERMS_URL = `${API_BASE_URL}/location-terms/`;
export const DATA_PROCESSING_CONSENT_URL = `${API_BASE_URL}/data-processing/`;
export const MARKETING_CONSENT_URL = `${API_BASE_URL}/marketing-consent/`;
export const ACCOUNT_DELETION_URL = `${API_BASE_URL}/account-deletion/`;

interface ApiResponse<T> {
  data?: T;
  error?: string;
}

async function getAccessToken(): Promise<string | null> {
  try { return await SecureStore.getItemAsync("accessToken"); } catch { return null; }
}

export async function getStoredAccessToken(): Promise<string | null> {
  return getAccessToken();
}

async function getRefreshToken(): Promise<string | null> {
  try { return await SecureStore.getItemAsync("refreshToken"); } catch { return null; }
}

function getInquirySeenKey(name: string, teamCode: string, date: string): string {
  return `inquirySeen.${normalizeSecureStoreKeyPart(
    teamCode
  )}.${normalizeSecureStoreKeyPart(name)}.${date}`;
}

export async function saveTokens(access: string, refresh: string) {
  await SecureStore.setItemAsync("accessToken", access);
  await SecureStore.setItemAsync("refreshToken", refresh);
}

export async function clearTokens() {
  try {
    await SecureStore.deleteItemAsync("accessToken");
    await SecureStore.deleteItemAsync("refreshToken");
  } catch {}
}

export async function getInquirySeenVersion(
  name: string,
  teamCode: string,
  date: string
): Promise<string | null> {
  if (!name.trim() || !teamCode.trim() || !date.trim()) {
    return null;
  }
  try {
    return await SecureStore.getItemAsync(getInquirySeenKey(name, teamCode, date));
  } catch {
    return null;
  }
}

export async function saveInquirySeenVersion(
  name: string,
  teamCode: string,
  date: string,
  updatedAt: string
): Promise<void> {
  if (!name.trim() || !teamCode.trim() || !date.trim() || !updatedAt.trim()) {
    return;
  }
  try {
    await SecureStore.setItemAsync(
      getInquirySeenKey(name, teamCode, date),
      updatedAt
    );
  } catch {}
}

export async function hasStoredSession(): Promise<boolean> {
  const access = await getAccessToken();
  const refresh = await getRefreshToken();
  return Boolean(access || refresh);
}

export async function restoreStoredSession() {
  const access = await getAccessToken();
  const refresh = await getRefreshToken();

  if (!access && refresh) {
    const refreshed = await refreshAccessToken();
    if (!refreshed) {
      return { error: "세션이 만료되었습니다. 다시 로그인해 주세요." };
    }
  }

  if (!(await getAccessToken())) {
    return { error: "저장된 로그인 정보가 없습니다." };
  }

  return request<ProfileResponse>("/api/v1/mobile/profile/");
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const url = `${API_BASE_URL}${endpoint}`;
  let token = await getAccessToken();
  if (!token && (await getRefreshToken())) {
    token = await refreshAccessToken();
  }
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) ?? {}),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  try {
    console.log(`[API] ${options.method || "GET"} ${url}`);
    const response = await fetch(url, { ...options, headers, credentials: "omit" });
    console.log(`[API] Response: ${response.status}`);

    if (response.status === 401 && token) {
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        headers["Authorization"] = `Bearer ${refreshed}`;
        const retry = await fetch(url, { ...options, headers, credentials: "omit" });
        const data = await retry.json();
        if (!retry.ok) return { error: data.detail ?? "요청 실패" };
        return { data };
      }
      return { error: "세션이 만료되었습니다. 다시 로그인해 주세요." };
    }

    const data = await response.json();
    if (!response.ok) return { error: data.detail ?? "요청 실패" };
    return { data };
  } catch (e: any) {
    console.error(`[API] Error: ${url}`, e?.message);
    return { error: `서버 연결 실패 (${e?.message || "unknown"})` };
  }
}

async function refreshAccessToken(): Promise<string | null> {
  const refresh = await getRefreshToken();
  if (!refresh) return null;
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/mobile/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "omit",
      body: JSON.stringify({ refresh }),
    });
    if (!response.ok) { await clearTokens(); return null; }
    const data = await response.json();
    await SecureStore.setItemAsync("accessToken", data.access);
    if (data.refresh) {
      await SecureStore.setItemAsync("refreshToken", data.refresh);
    }
    return data.access;
  } catch { return null; }
}

export interface LoginResponse {
  access: string;
  refresh: string;
  crew_member_id: number;
  name: string;
  team_code: string;
  vehicle_number: string;
  requires_password_change: boolean;
  signup_completed?: boolean;
}
export interface SignupResponse extends LoginResponse {
  status: string;
  detail?: string;
}
export interface MobileAppConfigResponse {
  messages: Record<string, string>;
  updated_at?: string | null;
}
export interface ProfileResponse {
  name: string;
  team_code: string;
  team_name: string;
  vehicle_number: string;
  bank_name: string;
  bank_account_number: string;
  vehicle_inspection_date: string | null;
  requires_password_change: boolean;
  signup_completed?: boolean;
  privacy_policy_agreed_at?: string | null;
  terms_agreed_at?: string | null;
  third_party_information_agreed_at?: string | null;
  location_terms_agreed_at?: string | null;
  marketing_event_agreed_at?: string | null;
}
export type InquiryBadgeStatus = "pending" | "answered" | null;
export interface SettlementRoundSummary {
  round_no?: number | null;
  box_count?: number;
  household_count?: number;
  amount?: number;
  is_yongcha?: boolean;
}
export interface SettlementDay {
  date: string;
  box_count: number;
  adjustment_amount?: number;
  amount: number;
  round_summaries?: SettlementRoundSummary[];
  inquiry_updated_at?: string | null;
  inquiry_status?: InquiryBadgeStatus;
}
export interface SettlementsResponse { days: SettlementDay[]; total_boxes: number; total_amount: number; }
export interface PasswordChangeResponse { detail: string; }
export interface VehicleNumberResponse { vehicle_number: string; }
export interface PayrollAccountResponse { bank_name: string; bank_account_number: string; }
export interface VehicleInspectionDateResponse { vehicle_inspection_date: string | null; }
export interface WorkSessionUploadResponse {
  session_id: number;
  session_date: string;
  started_at: string;
  ended_at: string;
  cycle_count: number;
  point_awarded: boolean;
  point_award_points: number;
  point_award_reason: string;
  point_balance: number;
}
export interface LiveWorkSessionResponse {
  status: "STOPPED" | "RUNNING";
  vehicle_number: string;
  session_started_at?: string | null;
  session_ended_at?: string | null;
  last_seen_at?: string | null;
  background_location_granted: boolean;
  app_version?: string;
}
export interface PointRedemptionItem {
  key: string;
  name: string;
  cost_points: number;
}
export interface PointRedemption {
  id: number;
  item_key: string;
  item_name: string;
  cost_points: number;
  status: "PENDING" | "CONFIRMED" | "CANCELLED";
  requested_at: string;
  confirmed_at?: string | null;
  note?: string;
}
export interface PointTransaction {
  id: number;
  points: number;
  kind: "WORK_REWARD" | "MANUAL_ADJUST" | "REDEMPTION_DEDUCT";
  memo: string;
  work_date?: string | null;
  created_at: string;
}
export interface PointSummaryResponse {
  balance: number;
  pending_points: number;
  available_points: number;
  items: PointRedemptionItem[];
  pending_redemptions: PointRedemption[];
  recent_redemptions: PointRedemption[];
  recent_transactions: PointTransaction[];
  requested_redemption?: PointRedemption;
}
export interface SettlementInquiryMessage {
  id: number;
  author_type: "crew" | "admin";
  author_name: string;
  content: string;
  created_at: string;
}
export interface SettlementInquiryDetailResponse {
  inquiry_id: number | null;
  date: string;
  box_count: number;
  pay_price: number;
  adjustment_amount: number;
  amount: number;
  is_overtime: boolean;
  status: "OPEN" | "ANSWERED" | "READ" | null;
  last_by: "crew" | "admin" | null;
  badge_status: InquiryBadgeStatus;
  updated_at: string | null;
  messages: SettlementInquiryMessage[];
}
export interface SettlementInquiryReadResponse {
  id: number;
  status: "OPEN" | "ANSWERED" | "READ";
  badge_status: InquiryBadgeStatus;
}

export const api = {
  getAppConfig() {
    return request<MobileAppConfigResponse>("/api/v1/mobile/app-config/");
  },
  register(
    name: string,
    teamCode: string,
    password: string,
    passwordConfirm: string,
    vehicleNumber: string,
    agreePrivacyPolicy: boolean,
    agreeTerms: boolean,
    agreeDataProcessing: boolean,
    agreeLocationTerms: boolean,
    agreeMarketingEvent: boolean
  ) {
    return request<SignupResponse>("/api/v1/mobile/register/", {
      method: "POST",
      body: JSON.stringify({
        name,
        team_code: teamCode.toUpperCase(),
        password,
        password_confirm: passwordConfirm,
        vehicle_number: vehicleNumber,
        app_version: getClientAppVersion(),
        agree_privacy_policy: agreePrivacyPolicy,
        agree_terms: agreeTerms,
        agree_data_processing: agreeDataProcessing,
        agree_third_party_information: agreeDataProcessing,
        agree_location_terms: agreeLocationTerms,
        agree_marketing_event: agreeMarketingEvent,
      }),
    });
  },
  login(name: string, teamCode: string, password: string) {
    return request<LoginResponse>("/api/v1/mobile/login/", {
      method: "POST",
      body: JSON.stringify({
        name,
        team_code: teamCode.toUpperCase(),
        password,
        app_version: getClientAppVersion(),
      }),
    });
  },
  completeSignup(
    password: string,
    passwordConfirm: string,
    vehicleNumber: string,
    agreePrivacyPolicy: boolean,
    agreeTerms: boolean,
    agreeDataProcessing: boolean,
    agreeLocationTerms: boolean,
    agreeMarketingEvent: boolean
  ) {
    return request<ProfileResponse>("/api/v1/mobile/signup/complete/", {
      method: "POST",
      body: JSON.stringify({
        password,
        password_confirm: passwordConfirm,
        vehicle_number: vehicleNumber,
        app_version: getClientAppVersion(),
        agree_privacy_policy: agreePrivacyPolicy,
        agree_terms: agreeTerms,
        agree_data_processing: agreeDataProcessing,
        agree_third_party_information: agreeDataProcessing,
        agree_location_terms: agreeLocationTerms,
        agree_marketing_event: agreeMarketingEvent,
      }),
    });
  },
  refreshToken() { return refreshAccessToken(); },
  getProfile() { return request<ProfileResponse>("/api/v1/mobile/profile/"); },
  getSettlements(month: string) {
    return request<SettlementsResponse>(`/api/v1/mobile/settlements/?month=${month}`);
  },
  getSettlementInquiry(date: string) {
    return request<SettlementInquiryDetailResponse>(
      `/api/v1/mobile/settlement-inquiry/?date=${date}`
    );
  },
  commentSettlementInquiry(date: string, content: string) {
    return request<SettlementInquiryDetailResponse>(
      "/api/v1/mobile/settlement-inquiry/comment/",
      {
        method: "POST",
        body: JSON.stringify({
          date,
          content,
        }),
      }
    );
  },
  markSettlementInquiryRead(inquiryId: number) {
    return request<SettlementInquiryReadResponse>(
      "/api/v1/mobile/settlement-inquiry/read/",
      {
        method: "POST",
        body: JSON.stringify({
          inquiry_id: inquiryId,
        }),
      }
    );
  },
  changePassword(
    password: string,
    passwordConfirm: string,
    vehicleNumber?: string
  ) {
    return request<PasswordChangeResponse>("/api/v1/mobile/password/", {
      method: "POST",
      body: JSON.stringify({
        password,
        password_confirm: passwordConfirm,
        ...(vehicleNumber !== undefined
          ? { vehicle_number: vehicleNumber }
          : {}),
      }),
    });
  },
  updateVehicleNumber(vehicleNumber: string) {
    return request<VehicleNumberResponse>("/api/v1/mobile/vehicle-number/", {
      method: "POST",
      body: JSON.stringify({
        vehicle_number: vehicleNumber,
      }),
    });
  },
  updatePayrollAccount(bankName: string, bankAccountNumber: string) {
    return request<PayrollAccountResponse>("/api/v1/mobile/payroll-account/", {
      method: "POST",
      body: JSON.stringify({
        bank_name: bankName,
        bank_account_number: bankAccountNumber,
      }),
    });
  },
  updateVehicleInspectionDate(vehicleInspectionDate: string) {
    return request<VehicleInspectionDateResponse>(
      "/api/v1/mobile/vehicle-inspection-date/",
      {
        method: "POST",
        body: JSON.stringify({
          vehicle_inspection_date: vehicleInspectionDate,
        }),
      }
    );
  },
  uploadWorkSession(
    csvContent: string,
    fileName: string,
    vehicleNumber: string
  ) {
    return request<WorkSessionUploadResponse>("/api/v1/mobile/work-session/upload/", {
      method: "POST",
      body: JSON.stringify({
        csv_content: csvContent,
        file_name: fileName,
        vehicle_number: vehicleNumber,
        app_version: getClientAppVersion(),
      }),
    });
  },
  startWorkSessionLive(
    vehicleNumber: string,
    backgroundLocationGranted: boolean
  ) {
    return request<LiveWorkSessionResponse>("/api/v1/mobile/work-session/start/", {
      method: "POST",
      body: JSON.stringify({
        vehicle_number: vehicleNumber,
        background_location_granted: backgroundLocationGranted,
        app_version: getClientAppVersion(),
      }),
    });
  },
  heartbeatWorkSessionLive(
    vehicleNumber: string,
    backgroundLocationGranted: boolean
  ) {
    return request<LiveWorkSessionResponse>(
      "/api/v1/mobile/work-session/heartbeat/",
      {
        method: "POST",
        body: JSON.stringify({
          vehicle_number: vehicleNumber,
          background_location_granted: backgroundLocationGranted,
          app_version: getClientAppVersion(),
        }),
      }
    );
  },
  stopWorkSessionLive(
    vehicleNumber: string,
    backgroundLocationGranted: boolean
  ) {
    return request<LiveWorkSessionResponse>("/api/v1/mobile/work-session/stop/", {
      method: "POST",
      body: JSON.stringify({
        vehicle_number: vehicleNumber,
        background_location_granted: backgroundLocationGranted,
        app_version: getClientAppVersion(),
      }),
    });
  },
  getPoints() {
    return request<PointSummaryResponse>("/api/v1/mobile/points/");
  },
  redeemPoints(itemKey: string) {
    return request<PointSummaryResponse>("/api/v1/mobile/points/redeem/", {
      method: "POST",
      body: JSON.stringify({
        item_key: itemKey,
      }),
    });
  },
};
