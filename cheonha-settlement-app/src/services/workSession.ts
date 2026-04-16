import * as SecureStore from "expo-secure-store";
import {
  NativeModules,
  PermissionsAndroid,
  Platform,
  type Permission,
} from "react-native";

type NativeWorkSessionModule = {
  startSession(name: string, vehicleNumber: string): Promise<void>;
  stopSession(): Promise<{
    running: boolean;
    sampleCount: number;
    vehicleNumber: string;
    exportedUri: string | null;
    exportedFileName: string | null;
  }>;
  getSessionState(): Promise<{
    running: boolean;
    sampleCount: number;
    vehicleNumber: string;
    exportedUri: string | null;
    exportedFileName: string | null;
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

function normalizeProfilePart(value: string): string {
  return value.trim().toUpperCase().replace(/\s+/g, "_");
}

function getVehicleNumberKey(name: string, teamCode: string): string {
  return `workSession.vehicleNumber.${normalizeProfilePart(
    teamCode
  )}.${normalizeProfilePart(name)}`;
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
    return { granted: true, backgroundLocationGranted: true };
  }

  const permissions: Permission[] = [
    PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
  ];

  if (Platform.Version >= 31) {
    permissions.push(
      PermissionsAndroid.PERMISSIONS.BLUETOOTH_SCAN,
      PermissionsAndroid.PERMISSIONS.BLUETOOTH_CONNECT
    );
  }

  if (Platform.Version >= 33) {
    permissions.push(
      PermissionsAndroid.PERMISSIONS.POST_NOTIFICATIONS,
      PermissionsAndroid.PERMISSIONS.READ_MEDIA_IMAGES
    );
  } else {
    permissions.push(PermissionsAndroid.PERMISSIONS.READ_EXTERNAL_STORAGE);
  }

  const results = await PermissionsAndroid.requestMultiple(permissions);
  const granted = permissions.every(
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

export async function getWorkSessionState() {
  return getNativeModule().getSessionState();
}

export async function startWorkSession(name: string, vehicleNumber: string) {
  await getNativeModule().startSession(name, vehicleNumber);
}

export async function stopWorkSession() {
  return getNativeModule().stopSession();
}
