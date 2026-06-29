import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { api, type MobileAppConfigResponse } from "./api";

export type AppMessageMap = Record<string, string>;

type AppMessagesContextValue = {
  messages: AppMessageMap;
  reload: () => Promise<void>;
  message: (
    key: string,
    fallback: string,
    variables?: Record<string, string | number | undefined>
  ) => string;
};

const AppMessagesContext = createContext<AppMessagesContextValue>({
  messages: {},
  reload: async () => undefined,
  message: (
    key: string,
    fallback: string,
    variables: Record<string, string | number | undefined> = {}
  ) => resolveAppMessage({}, key, fallback, variables),
});

export function fillMessageTemplate(
  template: string,
  variables: Record<string, string | number | undefined> = {}
) {
  return String(template || "").replace(/\{([a-zA-Z0-9_]+)\}/g, (_match, key) => {
    const value = variables[key];
    return value === undefined || value === null ? "" : String(value);
  });
}

export function resolveAppMessage(
  messages: AppMessageMap | null | undefined,
  key: string,
  fallback: string,
  variables: Record<string, string | number | undefined> = {}
) {
  const rawValue = String(messages?.[key] || fallback || "").trim();
  return fillMessageTemplate(rawValue || fallback, variables);
}

export function AppMessagesProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<AppMessageMap>({});

  const reload = useCallback(async () => {
    const response = await api.getAppConfig();
    const data: MobileAppConfigResponse | undefined = response.data;
    if (data?.messages) {
      setMessages(data.messages);
    }
  }, []);

  useEffect(() => {
    void reload().catch(() => undefined);
  }, [reload]);

  const message = useCallback(
    (
      key: string,
      fallback: string,
      variables: Record<string, string | number | undefined> = {}
    ) => resolveAppMessage(messages, key, fallback, variables),
    [messages]
  );

  const value = useMemo(
    () => ({ messages, reload, message }),
    [message, messages, reload]
  );

  return React.createElement(AppMessagesContext.Provider, { value }, children);
}

export function useAppMessages() {
  return useContext(AppMessagesContext);
}
