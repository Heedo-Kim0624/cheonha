import Constants from "expo-constants";
import * as SecureStore from "expo-secure-store";

const envApiBaseUrl = process.env.EXPO_PUBLIC_API_BASE_URL;
const expoExtra =
  (Constants.expoConfig?.extra as
    | { apiBaseUrl?: string; appEnv?: string }
    | undefined) ?? {};
const fallbackApiBaseUrl =
  expoExtra.appEnv === "production"
    ? "http://43.201.160.163"
    : "http://13.124.120.147";
const API_BASE_URL = (
  envApiBaseUrl ||
  expoExtra.apiBaseUrl ||
  fallbackApiBaseUrl
).replace(/\/+$/, "");
export const PRIVACY_POLICY_URL = `${API_BASE_URL}/privacy`;

interface ApiResponse<T> {
  data?: T;
  error?: string;
}

async function getAccessToken(): Promise<string | null> {
  try { return await SecureStore.getItemAsync("accessToken"); } catch { return null; }
}

async function getRefreshToken(): Promise<string | null> {
  try { return await SecureStore.getItemAsync("refreshToken"); } catch { return null; }
}

function normalizeIdentityPart(value: string): string {
  return value.trim().toUpperCase().replace(/\s+/g, "_");
}

function getInquirySeenKey(name: string, teamCode: string, date: string): string {
  return `inquirySeen.${normalizeIdentityPart(teamCode)}.${normalizeIdentityPart(
    name
  )}.${date}`;
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
  const token = await getAccessToken();
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
    return data.access;
  } catch { return null; }
}

export interface LoginResponse { access: string; refresh: string; crew_member_id: number; name: string; team_code: string; requires_password_change: boolean; }
export interface ProfileResponse { name: string; team_code: string; team_name: string; requires_password_change: boolean; }
export type InquiryBadgeStatus = "pending" | "answered" | null;
export interface SettlementDay {
  date: string;
  box_count: number;
  adjustment_amount?: number;
  amount: number;
  inquiry_updated_at?: string | null;
  inquiry_status?: InquiryBadgeStatus;
}
export interface SettlementsResponse { days: SettlementDay[]; total_boxes: number; total_amount: number; }
export interface PasswordChangeResponse { detail: string; }
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
  login(name: string, teamCode: string, password: string) {
    return request<LoginResponse>("/api/v1/mobile/login/", {
      method: "POST",
      body: JSON.stringify({
        name,
        team_code: teamCode.toUpperCase(),
        password,
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
  changePassword(password: string, passwordConfirm: string) {
    return request<PasswordChangeResponse>("/api/v1/mobile/password/", {
      method: "POST",
      body: JSON.stringify({
        password,
        password_confirm: passwordConfirm,
      }),
    });
  },
};
