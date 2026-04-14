import { ExpoConfig, ConfigContext } from "expo/config";

const appVariant = (process.env.APP_VARIANT || "test").toLowerCase();
const isProduction = appVariant === "production";
const defaultApiBaseUrl = isProduction
  ? "http://3.34.125.138"
  : "http://3.35.218.152";

const config = ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: isProduction ? "천하정산" : "천하정산 DEV",
  slug: "cheonha-settlement-app",
  version: "1.0.1",
  orientation: "portrait",
  icon: "./assets/icon.png",
  userInterfaceStyle: "light",
  newArchEnabled: false,
  splash: {
    image: "./assets/splash-icon.png",
    resizeMode: "contain",
    backgroundColor: "#1B3A5C",
  },
  ios: {
    supportsTablet: false,
    bundleIdentifier: isProduction
      ? "com.cheonha.settlement"
      : "com.cheonha.settlement.dev",
  },
  android: {
    adaptiveIcon: {
      foregroundImage: "./assets/adaptive-icon.png",
      backgroundColor: "#1B3A5C",
    },
    package: isProduction
      ? "com.cheonha.settlement"
      : "com.cheonha.settlement.dev",
  },
  extra: {
    appEnv: isProduction ? "production" : "test",
    apiBaseUrl: process.env.APP_API_BASE_URL || defaultApiBaseUrl,
    eas: {
      projectId: "e31f7563-6819-45ec-a42a-102dc0ffe268",
    },
  },
  plugins: [
    "expo-secure-store",
    "expo-font",
    "./plugins/withNetworkSecurityConfig",
    "./plugins/withCleartextTraffic",
    "./plugins/withWebViewPackageQueries",
    "./plugins/withAndroidNetworkTuning",
  ],
});

export default config;
