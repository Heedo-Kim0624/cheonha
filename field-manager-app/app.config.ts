import { ExpoConfig } from 'expo/config'

const config: ExpoConfig = {
  name: 'CLEVER \uD604\uC7A5\uAD00\uB9AC\uC790',
  slug: 'clever-field-manager',
  version: '1.0.10',
  orientation: 'portrait',
  scheme: 'cleverfm',
  userInterfaceStyle: 'light',
  android: {
    package: 'com.clever.fieldmanager',
    versionCode: 11,
    permissions: ['INTERNET'],
  },
  ios: {
    bundleIdentifier: 'com.clever.fieldmanager',
    buildNumber: '11',
    supportsTablet: false,
  },
  extra: {
    apiBaseUrl:
      process.env.EXPO_PUBLIC_API_BASE_URL ||
      'http://43.201.160.163/api/v1',
    eas: { projectId: '' },
  },
  plugins: [],
}

export default config
