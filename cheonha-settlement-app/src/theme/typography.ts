import { Platform } from "react-native";

const fontFamily = Platform.select({
  ios: "System",
  android: "sans-serif",
  default: "System",
});

const monoFamily = Platform.select({
  ios: "Menlo",
  android: "monospace",
  default: "monospace",
});

export const typography = {
  fontFamily,
  monoFamily,

  appTitle: {
    fontFamily,
    fontSize: 28,
    fontWeight: "700" as const,
  },
  screenTitle: {
    fontFamily,
    fontSize: 20,
    fontWeight: "700" as const,
  },
  sectionTitle: {
    fontFamily,
    fontSize: 18,
    fontWeight: "600" as const,
  },
  body: {
    fontFamily,
    fontSize: 16,
    fontWeight: "400" as const,
  },
  bodySmall: {
    fontFamily,
    fontSize: 15,
    fontWeight: "400" as const,
  },
  label: {
    fontFamily,
    fontSize: 14,
    fontWeight: "600" as const,
  },
  caption: {
    fontFamily,
    fontSize: 13,
    fontWeight: "500" as const,
  },
  captionSmall: {
    fontFamily,
    fontSize: 12,
    fontWeight: "600" as const,
  },

  // Calendar-specific (monospace for aligned numbers)
  calendarDate: {
    fontFamily,
    fontSize: 12,
    fontWeight: "600" as const,
  },
  calendarBox: {
    fontFamily: monoFamily,
    fontSize: 9,
    fontWeight: "400" as const,
  },
  calendarAmount: {
    fontFamily: monoFamily,
    fontSize: 9,
    fontWeight: "700" as const,
  },
  summaryValue: {
    fontFamily: monoFamily,
    fontSize: 15,
    fontWeight: "700" as const,
  },
  summaryLabel: {
    fontFamily,
    fontSize: 10,
    fontWeight: "500" as const,
  },
} as const;
