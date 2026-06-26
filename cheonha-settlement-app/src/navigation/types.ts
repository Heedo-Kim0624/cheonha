export type RootStackParamList = {
  Login: undefined;
  Signup:
    | {
        mode?: "new" | "migration";
        initialName?: string;
        initialTeamCode?: string;
        initialVehicleNumber?: string;
        initialPassword?: string;
      }
    | undefined;
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
