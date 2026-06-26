import * as SecureStore from "expo-secure-store";
import {
  NativeModules,
  PermissionsAndroid,
  Platform,
  type Permission,
} from "react-native";
import { normalizeSecureStoreKeyPart } from "../utils/secureStoreKey";

type NativeWorkSessionModule = {
  configureServerSync(
    apiBaseUrl: string,
    accessToken: string,
    appVersion: string,
    backgroundLocationGranted: boolean
  ): Promise<void>;
  startSession(name: string, vehicleNumber: string): Promise<void>;
  startSessionWithSignalCheck(
    name: string,
    vehicleNumber: string,
    waitMs: number
  ): Promise<boolean>;
  stopSession(): Promise<{
    running: boolean;
    sampleCount: number;
    vehicleNumber: string;
    csvContent: string | null;
    fileName: string | null;
  }>;
  getSessionState(): Promise<{
    running: boolean;
    sampleCount: number;
    vehicleNumber: string;
    exportedUri: string | null;
    exportedFileName: string | null;
  }>;
  getSessionSummary(): Promise<{
    running: boolean;
    sampleCount: number;
    vehicleNumber: string;
    hasRssiSignal: boolean;
    cameraCaptureCount: number;
    cameraEndCount: number;
  }>;
};

const nativeModule = NativeModules.WorkSessionModule as
  | NativeWorkSessionModule
  | undefined;

function getNativeModule(): NativeWorkSessionModule {
  if (!nativeModule) {
    throw new Error("근무 기록 모듈을 불러올 수 없습니다.");
  }
  return nativeModule;
}

function getVehicleNumberKey(name: string, teamCode: string): string {
  return `workSession.vehicleNumber.${normalizeSecureStoreKeyPart(
    teamCode
  )}.${normalizeSecureStoreKeyPart(name)}`;
}

export async function getStoredVehicleNumber(
  name: string,
  teamCode: string
): Promise<string> {
  if (!name.trim() || !teamCode.trim()) {
    return "";
  }

  try {
    return (await SecureStore.getItemAsync(getVehicleNumberKey(name, teamCode))) ?? "";
  } catch {
    return "";
  }
}

export async function saveVehicleNumber(
  name: string,
  teamCode: string,
  vehicleNumber: string
): Promise<void> {
  if (!name.trim() || !teamCode.trim()) {
    return;
  }

  try {
    await SecureStore.setItemAsync(
      getVehicleNumberKey(name, teamCode),
      vehicleNumber.trim()
    );
  } catch {
    // Ignore local persistence failures.
  }
}

export async function requestWorkSessionPermissions(): Promise<{
  granted: boolean;
  backgroundLocationGranted: boolean;
}> {
  if (Platform.OS !== "android") {
    return {
      granted: true,
      backgroundLocationGranted: true,
    };
  }

  const requiredPermissions: Permission[] = [
    PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
  ];
  if (Platform.Version >= 31) {
    requiredPermissions.push(
      PermissionsAndroid.PERMISSIONS.BLUETOOTH_SCAN,
      PermissionsAndroid.PERMISSIONS.BLUETOOTH_CONNECT
    );
  }

  if (Platform.Version >= 33) {
    requiredPermissions.push(PermissionsAndroid.PERMISSIONS.POST_NOTIFICATIONS);
  }

  const results = await PermissionsAndroid.requestMultiple(requiredPermissions);
  const granted = requiredPermissions.every(
    (permission) => results[permission] === PermissionsAndroid.RESULTS.GRANTED
  );

  let backgroundLocationGranted = true;
  if (Platform.Version >= 29) {
    const backgroundResult = await PermissionsAndroid.request(
      PermissionsAndroid.PERMISSIONS.ACCESS_BACKGROUND_LOCATION
    );
    backgroundLocationGranted =
      backgroundResult === PermissionsAndroid.RESULTS.GRANTED;
  }

  return { granted, backgroundLocationGranted };
}

export interface AppPermissionItem {
  key:
    | "fine_location"
    | "background_location"
    | "bluetooth_scan"
    | "bluetooth_connect"
    | "notifications";
  label: string;
  description: string;
  granted: boolean;
  requiredMode: "always" | "allow";
}

async function checkPermission(permission: Permission): Promise<boolean> {
  return PermissionsAndroid.check(permission);
}

export async function getAppEntryPermissionStatus(): Promise<{
  allGranted: boolean;
  items: AppPermissionItem[];
}> {
  if (Platform.OS !== "android") {
    return { allGranted: true, items: [] };
  }

  const items: AppPermissionItem[] = [
    {
      key: "fine_location",
      label: "정확한 위치",
      description: "근무 이동 경로와 근무 기록 수집",
      granted: await checkPermission(
        PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION
      ),
      requiredMode: "allow",
    },
    {
      key: "background_location",
      label: "백그라운드 위치",
      description: "앱을 닫거나 다른 앱 사용 중에도 근무 기록 유지",
      granted:
        Platform.Version < 29
          ? true
          : await checkPermission(
              PermissionsAndroid.PERMISSIONS.ACCESS_BACKGROUND_LOCATION
            ),
      requiredMode: "always",
    },
  ];

  if (Platform.Version >= 31) {
    items.push(
      {
        key: "bluetooth_scan",
        label: "블루투스 스캔",
        description: "차량 BLE 신호 확인",
        granted: await checkPermission(
          PermissionsAndroid.PERMISSIONS.BLUETOOTH_SCAN
        ),
        requiredMode: "allow",
      },
      {
        key: "bluetooth_connect",
        label: "블루투스 연결",
        description: "차량 주변 장치 연결 상태 확인",
        granted: await checkPermission(
          PermissionsAndroid.PERMISSIONS.BLUETOOTH_CONNECT
        ),
        requiredMode: "allow",
      }
    );
  }

  if (Platform.Version >= 33) {
    items.push({
      key: "notifications",
      label: "알림",
      description: "근무 중 포그라운드 서비스 알림 유지",
      granted: await checkPermission(
        PermissionsAndroid.PERMISSIONS.POST_NOTIFICATIONS
      ),
      requiredMode: "allow",
    });
  }

  return {
    allGranted: items.every((item) => item.granted),
    items,
  };
}

export async function requestAppEntryPermissions(): Promise<{
  allGranted: boolean;
  items: AppPermissionItem[];
}> {
  await requestWorkSessionPermissions();
  return getAppEntryPermissionStatus();
}

export async function hasBackgroundLocationPermission(): Promise<boolean> {
  if (Platform.OS !== "android" || Platform.Version < 29) {
    return true;
  }
  return PermissionsAndroid.check(
    PermissionsAndroid.PERMISSIONS.ACCESS_BACKGROUND_LOCATION
  );
}

export async function getWorkSessionState() {
  return getNativeModule().getSessionState();
}

export async function getWorkSessionSummary() {
  return getNativeModule().getSessionSummary();
}

export async function configureWorkSessionServerSync(
  apiBaseUrl: string,
  accessToken: string,
  appVersion: string,
  backgroundLocationGranted: boolean
) {
  return getNativeModule().configureServerSync(
    apiBaseUrl,
    accessToken,
    appVersion,
    backgroundLocationGranted
  );
}

export async function startWorkSession(name: string, vehicleNumber: string) {
  await getNativeModule().startSession(name, vehicleNumber);
}

export async function startWorkSessionWithSignalCheck(
  name: string,
  vehicleNumber: string,
  waitMs = 2000
) {
  return getNativeModule().startSessionWithSignalCheck(
    name,
    vehicleNumber,
    waitMs
  );
}

export async function stopWorkSession() {
  return getNativeModule().stopSession();
}
