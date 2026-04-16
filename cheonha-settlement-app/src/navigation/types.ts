export type RootStackParamList = {
  Login: undefined;
  Calendar:
    | {
        profileName?: string;
        profileTeamCode?: string;
        requiresPasswordChange?: boolean;
      }
    | undefined;
};

declare global {
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}
