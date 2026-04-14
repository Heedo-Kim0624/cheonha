export type RootStackParamList = {
  Login: undefined;
  Calendar:
    | {
        profileName?: string;
        requiresPasswordChange?: boolean;
      }
    | undefined;
};

declare global {
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}
