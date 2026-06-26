import { Alert, type AlertButton } from "react-native";

import { resolveAppMessage, type AppMessageMap } from "./appMessages";

type AlertRule = {
  title?: string;
  message?: string;
  titleKey?: string;
  messageKey?: string;
  buttonKeyMap?: Record<string, string>;
  transform?: (
    payload: { title: string; message: string; buttons?: AlertButton[] },
    messages: AppMessageMap
  ) => { title?: string; message?: string; buttons?: AlertButton[] } | null;
};

let installed = false;
let currentMessageProvider: (() => AppMessageMap) | null = null;
let originalAlert = Alert.alert.bind(Alert);

const ALERT_RULES: AlertRule[] = [
  {
    title: "안내",
    message: "차량번호를 먼저 등록해 주세요.",
    titleKey: "generic_notice_title",
    messageKey: "start_vehicle_required_message",
  },
  {
    title: "권한 필요",
    message: "위치, 블루투스, 알림 권한이 있어야 근무 기록을 시작할 수 있습니다.",
    titleKey: "generic_notice_title",
    messageKey: "start_permission_required_message",
  },
  {
    title: "안내",
    message: "차량에 꽂은 USB 번호와 입력하신 차량번호가 일치하는지 확인해주세요",
    titleKey: "generic_notice_title",
    messageKey: "start_signal_mismatch_message",
  },
  {
    title: "위치 권한 필요",
    message:
      "위치 권한은 항상 허용으로 설정되어야 합니다. 앱 설정으로 이동해 위치 권한을 변경해 주세요.",
    titleKey: "location_permission_title",
    messageKey: "location_permission_body",
    buttonKeyMap: {
      취소: "generic_cancel_label",
      "설정 열기": "location_permission_settings_label",
    },
  },
  {
    title: "로그아웃",
    message: "로그아웃 하시겠습니까?",
    titleKey: "logout_confirm_title",
    messageKey: "logout_confirm_body",
    buttonKeyMap: {
      취소: "generic_cancel_label",
      로그아웃: "logout_confirm_button_label",
    },
  },
  {
    title: "안내",
    message: "근무 종료 후 로그아웃해 주세요.",
    titleKey: "generic_notice_title",
    messageKey: "logout_block_running_message",
  },
  {
    title: "안내",
    message: "사용자 정보를 다시 불러온 후 시도해 주세요.",
    titleKey: "generic_notice_title",
    messageKey: "profile_reload_required_message",
  },
  {
    title: "안내",
    message: "비밀번호는 4자리 숫자로 입력해 주세요.",
    titleKey: "generic_notice_title",
    messageKey: "password_invalid_pin_message",
  },
  {
    title: "안내",
    message: "초기 비밀번호 0000과 다른 4자리 숫자를 입력해 주세요.",
    titleKey: "generic_notice_title",
    messageKey: "password_same_as_default_message",
  },
  {
    title: "안내",
    message: "비밀번호 확인이 일치하지 않습니다.",
    titleKey: "generic_notice_title",
    messageKey: "password_confirm_mismatch_message",
  },
  {
    title: "안내",
    message: "차량번호 변경에서 먼저 차량번호를 입력해 주세요.",
    titleKey: "generic_notice_title",
    messageKey: "password_vehicle_required_message",
  },
  {
    title: "완료",
    message: "비밀번호가 변경되었습니다.",
    titleKey: "generic_complete_title",
    messageKey: "password_success_message",
  },
  {
    title: "안내",
    message: "차량번호를 입력해 주세요.",
    titleKey: "generic_notice_title",
    messageKey: "vehicle_number_required_before_save_message",
  },
  {
    title: "완료",
    message: "차량번호가 저장되었습니다.",
    titleKey: "generic_complete_title",
    messageKey: "vehicle_number_success_message",
  },
  {
    title: "안내",
    message: "은행명을 입력해 주세요.",
    titleKey: "generic_notice_title",
    messageKey: "payroll_bank_required_message",
  },
  {
    title: "안내",
    message: "계좌번호를 입력해 주세요.",
    titleKey: "generic_notice_title",
    messageKey: "payroll_account_required_message",
  },
  {
    title: "완료",
    message: "급여계좌가 저장되었습니다.",
    titleKey: "generic_complete_title",
    messageKey: "payroll_success_message",
  },
  {
    title: "안내",
    message: "검사일자를 선택해 주세요.",
    titleKey: "generic_notice_title",
    messageKey: "inspection_date_required_message",
  },
  {
    title: "안내",
    message: "검사일자는 YYYY-MM-DD 형식으로 입력해 주세요.",
    titleKey: "generic_notice_title",
    messageKey: "inspection_date_invalid_format_message",
  },
  {
    title: "완료",
    message: "검사일자가 저장되었습니다.",
    titleKey: "generic_complete_title",
    messageKey: "inspection_date_success_message",
  },
  {
    title: "완료",
    message: "관리자 확인 대기 목록에 등록되었습니다.",
    titleKey: "generic_complete_title",
    messageKey: "point_redeem_success_message",
  },
  {
    title: "오류",
    message: "문의 정보를 불러올 수 없습니다.",
    titleKey: "generic_error_title",
    messageKey: "inquiry_fetch_failed_message",
  },
  {
    title: "안내",
    message: "문의 내용을 입력해 주세요.",
    titleKey: "generic_notice_title",
    messageKey: "inquiry_content_required_message",
  },
  {
    title: "오류",
    message: "문의 등록에 실패했습니다.",
    titleKey: "generic_error_title",
    messageKey: "inquiry_submit_failed_message",
  },
  {
    title: "포인트 부족",
    message: "사용 가능한 포인트가 부족합니다.",
    titleKey: "point_insufficient_title",
    messageKey: "point_insufficient_message",
  },
  {
    title: "포인트 미획득",
    message:
      "포인트를 획득하지 못했습니다. 정상적으로 근무를 종료하셨다면, 위치 정보가 항상 허용으로 되어있는지 확인해주세요",
    titleKey: "point_not_awarded_title",
    messageKey: "point_not_awarded_body",
    buttonKeyMap: {
      "권한 확인": "point_not_awarded_settings_label",
      닫기: "generic_close_label",
    },
  },
  {
    title: "시작",
    message: "근무를 시작합니다. 안전 운행하세요!",
    titleKey: "generic_notice_title",
    messageKey: "start_success_message",
  },
  {
    title: "오류",
    message: "근무 기록을 시작할 수 없습니다.",
    titleKey: "generic_error_title",
    messageKey: "start_failed_message",
  },
  {
    title: "오류",
    message: "근무 기록 모듈을 불러올 수 없습니다.",
    titleKey: "generic_error_title",
    messageKey: "work_session_module_missing_message",
  },
  {
    title: "근무 종료",
    message: "근무를 종료하시겠습니까?",
    titleKey: "stop_confirm_title",
    messageKey: "stop_confirm_body",
    buttonKeyMap: {
      취소: "generic_cancel_label",
      확인: "generic_confirm_label",
    },
  },
  {
    title: "오류",
    message: "업로드할 근무 기록을 만들 수 없습니다.",
    titleKey: "generic_error_title",
    messageKey: "stop_upload_missing_message",
  },
  {
    title: "오류",
    message: "근무 기록을 종료할 수 없습니다.",
    titleKey: "generic_error_title",
    messageKey: "stop_failed_message",
  },
  {
    title: "포인트 획득",
    message: "포인트를 획득했습니다!",
    titleKey: "point_awarded_title",
    messageKey: "point_awarded_simple_body",
  },
  {
    title: "오류",
    message: "포인트 교환 신청에 실패했습니다.",
    titleKey: "generic_error_title",
    messageKey: "point_redeem_failed_message",
  },
  {
    title: "근무 기록 안내",
    message: "회차별 마지막 배송이 끝나면 반드시 근무종료 버튼을 눌러주세요.",
    titleKey: "work_guide_title",
    messageKey: "work_guide_body",
    buttonKeyMap: {
      "다시 보지 않기": "work_guide_hide_label",
      확인: "generic_confirm_label",
    },
  },
  {
    title: "알림",
    message: "개인정보처리방침 페이지를 열 수 없습니다.",
    titleKey: "generic_notice_title",
    messageKey: "privacy_open_failed_message",
  },
  {
    title: "오류",
    message: "앱 설정 화면을 열 수 없습니다.",
    titleKey: "generic_error_title",
    messageKey: "open_settings_failed_message",
  },
  {
    transform: ({ title, message, buttons }, messages) => {
      const inspectionMatch = /^검사 일자 (\d+)일 전입니다! 일정에 참고해주세요!$/.exec(
        message
      );
      if (title === "알림" && inspectionMatch) {
        return {
          title: resolveAppMessage(messages, "inspection_reminder_title", "알림"),
          message: resolveAppMessage(
            messages,
            "inspection_reminder_body_template",
            "검사 일자 {days_left}일 전입니다! 일정에 참고해주세요!",
            { days_left: inspectionMatch[1] }
          ),
          buttons: (buttons || []).map((button) => ({
            ...button,
            text:
              button.text === "오늘 하루 보지 않기"
                ? resolveAppMessage(
                    messages,
                    "inspection_reminder_hide_label",
                    "오늘 하루 보지 않기"
                  )
                : button.text === "확인"
                  ? resolveAppMessage(messages, "generic_confirm_label", "확인")
                  : button.text,
          })),
        };
      }

      const pointConfirmMatch = /^(.*) ([\d,]+)P를 신청할까요\?$/.exec(message);
      if (title === "포인트 교환" && pointConfirmMatch) {
        return {
          title: resolveAppMessage(messages, "point_redeem_confirm_title", "포인트 교환"),
          message: resolveAppMessage(
            messages,
            "point_redeem_confirm_template",
            "{item_name} {cost_points}P를 신청할까요?",
            {
              item_name: pointConfirmMatch[1],
              cost_points: pointConfirmMatch[2],
            }
          ),
          buttons: (buttons || []).map((button) => ({
            ...button,
            text:
              button.text === "취소"
                ? resolveAppMessage(messages, "generic_cancel_label", "취소")
                : button.text === "신청"
                  ? resolveAppMessage(messages, "point_redeem_request_label", "신청")
                  : button.text,
          })),
        };
      }

      const pointAwardedMatch = /^포인트를 획득했습니다!\n([\d,]+)P가 적립되었습니다\.$/.exec(
        message
      );
      if (title === "포인트 획득" && pointAwardedMatch) {
        return {
          title: resolveAppMessage(messages, "point_awarded_title", "포인트 획득"),
          message: resolveAppMessage(
            messages,
            "point_awarded_body_template",
            "포인트를 획득했습니다!\n{points}P가 적립되었습니다.",
            { points: pointAwardedMatch[1] }
          ),
        };
      }

      const liveSyncMatch = /^실시간 근무 현황 연동에 실패했습니다\.\n(.+)$/.exec(message);
      if (title === "안내" && liveSyncMatch) {
        return {
          title: resolveAppMessage(messages, "generic_notice_title", "안내"),
          message: resolveAppMessage(
            messages,
            "start_live_sync_failed_template",
            "실시간 근무 현황 연동에 실패했습니다.\n{error}",
            { error: liveSyncMatch[1] }
          ),
        };
      }

      return null;
    },
  },
];

function replaceButtons(buttons: AlertButton[] | undefined, messages: AppMessageMap, buttonKeyMap?: Record<string, string>) {
  if (!buttons?.length || !buttonKeyMap) {
    return buttons;
  }
  return buttons.map((button) => {
    const nextKey = buttonKeyMap[String(button.text || "")];
    if (!nextKey) {
      return button;
    }
    return {
      ...button,
      text: resolveAppMessage(messages, nextKey, String(button.text || "")),
    };
  });
}

function applyRule(
  title: string,
  message: string,
  buttons: AlertButton[] | undefined,
  messages: AppMessageMap
) {
  for (const rule of ALERT_RULES) {
    if (rule.transform) {
      const transformed = rule.transform({ title, message, buttons }, messages);
      if (transformed) {
        return {
          title: transformed.title ?? title,
          message: transformed.message ?? message,
          buttons: transformed.buttons ?? buttons,
        };
      }
      continue;
    }

    if (rule.title === title && rule.message === message) {
      return {
        title: rule.titleKey
          ? resolveAppMessage(messages, rule.titleKey, title)
          : title,
        message: rule.messageKey
          ? resolveAppMessage(messages, rule.messageKey, message)
          : message,
        buttons: replaceButtons(buttons, messages, rule.buttonKeyMap),
      };
    }
  }

  const genericTitleMap: Record<string, string> = {
    안내: "generic_notice_title",
    오류: "generic_error_title",
    완료: "generic_complete_title",
  };
  const genericKey = genericTitleMap[title];
  return {
    title: genericKey ? resolveAppMessage(messages, genericKey, title) : title,
    message,
    buttons,
  };
}

export function installAppAlertTransform(messageProvider: () => AppMessageMap) {
  currentMessageProvider = messageProvider;
  if (installed) {
    return;
  }

  installed = true;
  Alert.alert = ((title, message, buttons, options) => {
    const messages = currentMessageProvider?.() || {};
    const transformed = applyRule(
      String(title || ""),
      String(message || ""),
      buttons,
      messages
    );
    return originalAlert(
      transformed.title,
      transformed.message,
      transformed.buttons,
      options
    );
  }) as typeof Alert.alert;
}
