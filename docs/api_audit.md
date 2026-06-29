# API 문서화/권한/중복 Endpoint 감사

이 문서는 `scripts/api_audit.py`가 Django URL resolver를 기준으로 생성한 API 감사 결과입니다.

## 요약

- 업무 API endpoint pattern: **168개**
- 업무 API method-route: **256개**
- 보조 endpoint(schema/docs/router root): **14개 path / 14 method-route**
- DRF format suffix 중복 route: **214개 method-route**

## 권한 노출 분류

| 분류 | 개수 | 의미 |
|---|---:|---|
| `custom-field-manager-token` | 5 | `AllowAny`로 열어두고 함수 내부에서 현장관리자 Bearer token 검사 |
| `custom-mobile-token` | 16 | `AllowAny`로 열어두고 함수 내부에서 모바일 Bearer token 검사 |
| `jwt-authenticated` | 219 | 일반 관리자 JWT 필요 |
| `public` | 16 | 토큰 없이 호출 가능하도록 공개 |

## 도메인별 규모

| 도메인 | endpoint pattern | method-route | 주 역할 |
|---|---:|---:|---|
| `accounts` | 13 | 21 | 사용자/팀/가입/토큰 |
| `auth` | 6 | 6 | 웹/통합관리 인증 |
| `crew` | 14 | 22 | 배송원, 용차, 단가, 연장 |
| `dashboard` | 7 | 7 | KPI, 홈 overview, workflow monitor |
| `dispatch` | 15 | 23 | 배차 업로드, 운영현황, 정산 생성 |
| `field-manager` | 6 | 6 | 현장관리자 앱 차량 요청 |
| `inquiry` | 5 | 9 | 정산 문의 |
| `manpower` | 8 | 12 | 인력풀, 지오코딩, 시트 |
| `mobile` | 26 | 27 | 정산 앱 전용 API |
| `partner` | 2 | 6 | 파트너 |
| `points` | 7 | 10 | 포인트/상품/교환 |
| `region` | 7 | 15 | 지역/단가/단가 이력 |
| `settlement` | 12 | 20 | 정산/상세/확정/재계산 |
| `territory` | 7 | 11 | 권역 polygon/권역별 박스 |
| `tracking` | 11 | 15 | 근무 추적/GPS/CSV |
| `vehicle` | 22 | 46 | 차량/피트/구독/반납/A/S |

## 중복 Endpoint 판단

- 실제 업무 중복이라기보다 DRF `DefaultRouter`가 자동 제공하는 `.json` 등 format suffix route가 중복의 대부분입니다.
- `api/v1/<domain>/` router root도 사람이 직접 쓰는 업무 API라기보다 DRF 보조 endpoint입니다.
- 현재 프론트/앱은 대부분 trailing slash 없이도 Nginx/Django가 처리 가능한 경로를 호출하지만, 공식 문서에서는 trailing slash 포함 경로를 표준으로 둡니다.

## 권한 정리 기준

- 관리자 웹 API는 기본적으로 `IsAuthenticated`를 유지합니다.
- 모바일 앱 API는 일반 User JWT가 아니라 `crew_member_id` claim을 넣은 별도 토큰을 쓰므로 `custom-mobile-token`으로 분류합니다.
- 현장관리자 앱은 `kind=field_manager` HMAC/JWT를 자체 검증하므로 `custom-field-manager-token`으로 분류합니다.
- 다음 단계에서 코드 정리를 한다면 모바일/현장관리자 토큰 검사를 DRF permission class로 빼서 `AllowAny` 오해를 줄이는 것이 가장 안전한 방향입니다.

## Endpoint Inventory

| Domain | Method | Endpoint | Permission | Exposure | View.action |
|---|---|---|---|---|---|
| `accounts` | `POST` | `api/v1/accounts/signup/` | `AllowAny` | `public` | `SignupView.post` |
| `accounts` | `GET` | `api/v1/accounts/teams/` | `IsAuthenticated` | `jwt-authenticated` | `TeamViewSet.list` |
| `accounts` | `POST` | `api/v1/accounts/teams/` | `IsAuthenticated` | `jwt-authenticated` | `TeamViewSet.create` |
| `accounts` | `GET` | `api/v1/accounts/teams/teams_list/` | `AllowAny` | `public` | `TeamViewSet.teams_list` |
| `accounts` | `DELETE` | `api/v1/accounts/teams/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `TeamViewSet.destroy` |
| `accounts` | `GET` | `api/v1/accounts/teams/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `TeamViewSet.retrieve` |
| `accounts` | `PATCH` | `api/v1/accounts/teams/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `TeamViewSet.partial_update` |
| `accounts` | `PUT` | `api/v1/accounts/teams/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `TeamViewSet.update` |
| `accounts` | `POST` | `api/v1/accounts/teams/{id}/recalc_settlements/` | `IsAuthenticated` | `jwt-authenticated` | `TeamViewSet.recalc_settlements` |
| `accounts` | `POST` | `api/v1/accounts/token/` | `AllowAny` | `public` | `CustomTokenObtainPairView.post` |
| `accounts` | `POST` | `api/v1/accounts/token/refresh/` | `AllowAny` | `public` | `TokenRefreshView.post` |
| `accounts` | `GET` | `api/v1/accounts/users/` | `IsAuthenticated` | `jwt-authenticated` | `UserViewSet.list` |
| `accounts` | `POST` | `api/v1/accounts/users/` | `IsAuthenticated` | `jwt-authenticated` | `UserViewSet.create` |
| `accounts` | `POST` | `api/v1/accounts/users/change_password/` | `IsAuthenticated` | `jwt-authenticated` | `UserViewSet.change_password` |
| `accounts` | `POST` | `api/v1/accounts/users/logout/` | `IsAuthenticated` | `jwt-authenticated` | `UserViewSet.logout` |
| `accounts` | `GET` | `api/v1/accounts/users/me/` | `IsAuthenticated` | `jwt-authenticated` | `UserViewSet.me` |
| `accounts` | `GET` | `api/v1/accounts/users/roles/` | `AllowAny` | `public` | `UserViewSet.roles` |
| `accounts` | `DELETE` | `api/v1/accounts/users/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `UserViewSet.destroy` |
| `accounts` | `GET` | `api/v1/accounts/users/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `UserViewSet.retrieve` |
| `accounts` | `PATCH` | `api/v1/accounts/users/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `UserViewSet.partial_update` |
| `accounts` | `PUT` | `api/v1/accounts/users/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `UserViewSet.update` |
| `auth` | `POST` | `api/v1/auth/clever-login/` | `AllowAny` | `public` | `CleverLoginView.post` |
| `auth` | `POST` | `api/v1/auth/login/` | `AllowAny` | `public` | `LoginView.post` |
| `auth` | `POST` | `api/v1/auth/logout/` | `AllowAny` | `public` | `LogoutView.post` |
| `auth` | `GET` | `api/v1/auth/profile/` | `IsAuthenticated` | `jwt-authenticated` | `ProfileView.get` |
| `auth` | `POST` | `api/v1/auth/refresh/` | `AllowAny` | `public` | `RefreshTokenView.post` |
| `auth` | `POST` | `api/v1/auth/signup/` | `AllowAny` | `public` | `SignupView.post` |
| `crew` | `GET` | `api/v1/crew/members/` | `IsAuthenticated` | `jwt-authenticated` | `CrewMemberViewSet.list` |
| `crew` | `POST` | `api/v1/crew/members/` | `IsAuthenticated` | `jwt-authenticated` | `CrewMemberViewSet.create` |
| `crew` | `POST` | `api/v1/crew/members/bulk_yongcha_pay_price/` | `IsAuthenticated` | `jwt-authenticated` | `CrewMemberViewSet.bulk_yongcha_pay_price` |
| `crew` | `GET` | `api/v1/crew/members/new_members/` | `IsAuthenticated` | `jwt-authenticated` | `CrewMemberViewSet.new_members` |
| `crew` | `GET` | `api/v1/crew/members/yongcha_summary/` | `IsAuthenticated` | `jwt-authenticated` | `CrewMemberViewSet.yongcha_summary` |
| `crew` | `DELETE` | `api/v1/crew/members/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `CrewMemberViewSet.destroy` |
| `crew` | `GET` | `api/v1/crew/members/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `CrewMemberViewSet.retrieve` |
| `crew` | `PATCH` | `api/v1/crew/members/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `CrewMemberViewSet.partial_update` |
| `crew` | `PUT` | `api/v1/crew/members/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `CrewMemberViewSet.update` |
| `crew` | `POST` | `api/v1/crew/members/{id}/convert_to_regular/` | `IsAuthenticated` | `jwt-authenticated` | `CrewMemberViewSet.convert_to_regular` |
| `crew` | `POST` | `api/v1/crew/members/{id}/convert_to_yongcha/` | `IsAuthenticated` | `jwt-authenticated` | `CrewMemberViewSet.convert_to_yongcha` |
| `crew` | `POST` | `api/v1/crew/members/{id}/mark_registered/` | `IsAuthenticated` | `jwt-authenticated` | `CrewMemberViewSet.mark_registered` |
| `crew` | `POST` | `api/v1/crew/members/{id}/recalc_settlements/` | `IsAuthenticated` | `jwt-authenticated` | `CrewMemberViewSet.recalc_settlements` |
| `crew` | `POST` | `api/v1/crew/members/{id}/set_round_yongcha/` | `IsAuthenticated` | `jwt-authenticated` | `CrewMemberViewSet.set_round_yongcha` |
| `crew` | `GET` | `api/v1/crew/members/{id}/settlement_history/` | `IsAuthenticated` | `jwt-authenticated` | `CrewMemberViewSet.settlement_history` |
| `crew` | `GET` | `api/v1/crew/members/{id}/yongcha_daily/` | `IsAuthenticated` | `jwt-authenticated` | `CrewMemberViewSet.yongcha_daily` |
| `crew` | `GET` | `api/v1/crew/overtime/` | `IsAuthenticated` | `jwt-authenticated` | `OvertimeSettingViewSet.list` |
| `crew` | `POST` | `api/v1/crew/overtime/` | `IsAuthenticated` | `jwt-authenticated` | `OvertimeSettingViewSet.create` |
| `crew` | `DELETE` | `api/v1/crew/overtime/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `OvertimeSettingViewSet.destroy` |
| `crew` | `GET` | `api/v1/crew/overtime/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `OvertimeSettingViewSet.retrieve` |
| `crew` | `PATCH` | `api/v1/crew/overtime/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `OvertimeSettingViewSet.partial_update` |
| `crew` | `PUT` | `api/v1/crew/overtime/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `OvertimeSettingViewSet.update` |
| `dashboard` | `GET` | `api/v1/dashboard/dashboard/crew_statistics/` | `IsAuthenticated` | `jwt-authenticated` | `DashboardViewSet.crew_statistics` |
| `dashboard` | `GET` | `api/v1/dashboard/dashboard/home_overview/` | `IsAuthenticated` | `jwt-authenticated` | `DashboardViewSet.home_overview` |
| `dashboard` | `GET` | `api/v1/dashboard/dashboard/kpi/` | `IsAuthenticated` | `jwt-authenticated` | `DashboardViewSet.kpi` |
| `dashboard` | `GET` | `api/v1/dashboard/dashboard/monthly_trend/` | `IsAuthenticated` | `jwt-authenticated` | `DashboardViewSet.monthly_trend` |
| `dashboard` | `GET` | `api/v1/dashboard/dashboard/revenue_by_region/` | `IsAuthenticated` | `jwt-authenticated` | `DashboardViewSet.revenue_by_region` |
| `dashboard` | `GET` | `api/v1/dashboard/dashboard/settlement_summary/` | `IsAuthenticated` | `jwt-authenticated` | `DashboardViewSet.settlement_summary` |
| `dashboard` | `GET` | `api/v1/dashboard/workflow-monitor/` | `IsAuthenticated` | `jwt-authenticated` | `WorkflowMonitorViewSet.list` |
| `dispatch` | `GET` | `api/v1/dispatch/records/` | `IsAuthenticated` | `jwt-authenticated` | `DispatchRecordViewSet.list` |
| `dispatch` | `POST` | `api/v1/dispatch/records/` | `IsAuthenticated` | `jwt-authenticated` | `DispatchRecordViewSet.create` |
| `dispatch` | `DELETE` | `api/v1/dispatch/records/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `DispatchRecordViewSet.destroy` |
| `dispatch` | `GET` | `api/v1/dispatch/records/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `DispatchRecordViewSet.retrieve` |
| `dispatch` | `PATCH` | `api/v1/dispatch/records/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `DispatchRecordViewSet.partial_update` |
| `dispatch` | `PUT` | `api/v1/dispatch/records/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `DispatchRecordViewSet.update` |
| `dispatch` | `GET` | `api/v1/dispatch/uploads/` | `IsAuthenticated` | `jwt-authenticated` | `DispatchUploadViewSet.list` |
| `dispatch` | `POST` | `api/v1/dispatch/uploads/` | `IsAuthenticated` | `jwt-authenticated` | `DispatchUploadViewSet.create` |
| `dispatch` | `GET` | `api/v1/dispatch/uploads/check_date/` | `IsAuthenticated` | `jwt-authenticated` | `DispatchUploadViewSet.check_date` |
| `dispatch` | `GET` | `api/v1/dispatch/uploads/operation-report-csv/` | `IsAuthenticated` | `jwt-authenticated` | `DispatchUploadViewSet.operation_report_csv` |
| `dispatch` | `GET` | `api/v1/dispatch/uploads/operation-report-territories/` | `IsAuthenticated` | `jwt-authenticated` | `DispatchUploadViewSet.operation_report_territories` |
| `dispatch` | `GET` | `api/v1/dispatch/uploads/operation-report-yongcha-map/` | `IsAuthenticated` | `jwt-authenticated` | `DispatchUploadViewSet.operation_report_yongcha_map` |
| `dispatch` | `GET` | `api/v1/dispatch/uploads/operation-report/` | `IsAuthenticated` | `jwt-authenticated` | `DispatchUploadViewSet.operation_report` |
| `dispatch` | `POST` | `api/v1/dispatch/uploads/reset_data/` | `IsAuthenticated` | `jwt-authenticated` | `DispatchUploadViewSet.reset_data` |
| `dispatch` | `DELETE` | `api/v1/dispatch/uploads/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `DispatchUploadViewSet.destroy` |
| `dispatch` | `GET` | `api/v1/dispatch/uploads/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `DispatchUploadViewSet.retrieve` |
| `dispatch` | `PATCH` | `api/v1/dispatch/uploads/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `DispatchUploadViewSet.partial_update` |
| `dispatch` | `PUT` | `api/v1/dispatch/uploads/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `DispatchUploadViewSet.update` |
| `dispatch` | `POST` | `api/v1/dispatch/uploads/{id}/configure/` | `IsAuthenticated` | `jwt-authenticated` | `DispatchUploadViewSet.configure` |
| `dispatch` | `GET` | `api/v1/dispatch/uploads/{id}/detected_info/` | `IsAuthenticated` | `jwt-authenticated` | `DispatchUploadViewSet.detected_info` |
| `dispatch` | `GET` | `api/v1/dispatch/uploads/{id}/download-file/` | `IsAuthenticated` | `jwt-authenticated` | `DispatchUploadViewSet.download_file` |
| `dispatch` | `POST` | `api/v1/dispatch/uploads/{id}/finalize/` | `IsAuthenticated` | `jwt-authenticated` | `DispatchUploadViewSet.finalize` |
| `dispatch` | `POST` | `api/v1/dispatch/uploads/{id}/set_overtime/` | `IsAuthenticated` | `jwt-authenticated` | `DispatchUploadViewSet.set_overtime` |
| `field-manager` | `POST` | `api/v1/field-manager/as-requests/` | `AllowAny` | `custom-field-manager-token` | `fm_as_request.post` |
| `field-manager` | `GET` | `api/v1/field-manager/blocked-dates/` | `AllowAny` | `custom-field-manager-token` | `fm_blocked_dates.get` |
| `field-manager` | `POST` | `api/v1/field-manager/login/` | `AllowAny` | `public` | `fm_login.post` |
| `field-manager` | `GET` | `api/v1/field-manager/request-history/` | `AllowAny` | `custom-field-manager-token` | `fm_request_history.get` |
| `field-manager` | `POST` | `api/v1/field-manager/return-requests/` | `AllowAny` | `custom-field-manager-token` | `fm_return_request.post` |
| `field-manager` | `POST` | `api/v1/field-manager/subscription-requests/` | `AllowAny` | `custom-field-manager-token` | `fm_subscription_request.post` |
| `inquiry` | `GET` | `api/v1/inquiry/inquiries/` | `IsAuthenticated` | `jwt-authenticated` | `SettlementInquiryViewSet.list` |
| `inquiry` | `POST` | `api/v1/inquiry/inquiries/` | `IsAuthenticated` | `jwt-authenticated` | `SettlementInquiryViewSet.create` |
| `inquiry` | `GET` | `api/v1/inquiry/inquiries/counts/` | `IsAuthenticated` | `jwt-authenticated` | `SettlementInquiryViewSet.counts` |
| `inquiry` | `DELETE` | `api/v1/inquiry/inquiries/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `SettlementInquiryViewSet.destroy` |
| `inquiry` | `GET` | `api/v1/inquiry/inquiries/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `SettlementInquiryViewSet.retrieve` |
| `inquiry` | `PATCH` | `api/v1/inquiry/inquiries/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `SettlementInquiryViewSet.partial_update` |
| `inquiry` | `PUT` | `api/v1/inquiry/inquiries/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `SettlementInquiryViewSet.update` |
| `inquiry` | `POST` | `api/v1/inquiry/inquiries/{id}/mark_read/` | `IsAuthenticated` | `jwt-authenticated` | `SettlementInquiryViewSet.mark_read` |
| `inquiry` | `POST` | `api/v1/inquiry/inquiries/{id}/messages/` | `IsAuthenticated` | `jwt-authenticated` | `SettlementInquiryViewSet.add_message` |
| `manpower` | `GET` | `api/v1/manpower/people/` | `IsAuthenticated` | `jwt-authenticated` | `ManpowerViewSet.list` |
| `manpower` | `POST` | `api/v1/manpower/people/` | `IsAuthenticated` | `jwt-authenticated` | `ManpowerViewSet.create` |
| `manpower` | `POST` | `api/v1/manpower/people/geocode_all/` | `IsAuthenticated` | `jwt-authenticated` | `ManpowerViewSet.geocode_all` |
| `manpower` | `POST` | `api/v1/manpower/people/import_xlsx/` | `IsAuthenticated` | `jwt-authenticated` | `ManpowerViewSet.import_xlsx` |
| `manpower` | `GET` | `api/v1/manpower/people/nearby/` | `IsAuthenticated` | `jwt-authenticated` | `ManpowerViewSet.nearby` |
| `manpower` | `GET` | `api/v1/manpower/people/sheet/` | `IsAuthenticated` | `jwt-authenticated` | `ManpowerViewSet.sheet` |
| `manpower` | `POST` | `api/v1/manpower/people/sync_sheet/` | `IsAuthenticated` | `jwt-authenticated` | `ManpowerViewSet.sync_sheet` |
| `manpower` | `DELETE` | `api/v1/manpower/people/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `ManpowerViewSet.destroy` |
| `manpower` | `GET` | `api/v1/manpower/people/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `ManpowerViewSet.retrieve` |
| `manpower` | `PATCH` | `api/v1/manpower/people/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `ManpowerViewSet.partial_update` |
| `manpower` | `PUT` | `api/v1/manpower/people/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `ManpowerViewSet.update` |
| `manpower` | `POST` | `api/v1/manpower/people/{id}/geocode/` | `IsAuthenticated` | `jwt-authenticated` | `ManpowerViewSet.geocode` |
| `mobile` | `GET` | `api/v1/mobile/admin/app-config/` | `IsAuthenticated` | `jwt-authenticated` | `admin_mobile_app_config.get` |
| `mobile` | `PUT` | `api/v1/mobile/admin/app-config/` | `IsAuthenticated` | `jwt-authenticated` | `admin_mobile_app_config.put` |
| `mobile` | `GET` | `api/v1/mobile/admin/approvals/` | `IsAuthenticated` | `jwt-authenticated` | `admin_mobile_approvals.get` |
| `mobile` | `PUT` | `api/v1/mobile/admin/approvals/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `admin_mobile_approval_action.put` |
| `mobile` | `GET` | `api/v1/mobile/admin/users/` | `IsAuthenticated` | `jwt-authenticated` | `admin_mobile_users.get` |
| `mobile` | `DELETE` | `api/v1/mobile/admin/users/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `admin_mobile_user_deactivate.delete` |
| `mobile` | `GET` | `api/v1/mobile/app-config/` | `AllowAny` | `public` | `mobile_app_config.get` |
| `mobile` | `POST` | `api/v1/mobile/login/` | `AllowAny` | `public` | `mobile_login.post` |
| `mobile` | `POST` | `api/v1/mobile/password/` | `AllowAny` | `custom-mobile-token` | `mobile_change_password.post` |
| `mobile` | `POST` | `api/v1/mobile/payroll-account/` | `AllowAny` | `custom-mobile-token` | `mobile_update_payroll_account.post` |
| `mobile` | `GET` | `api/v1/mobile/points/` | `AllowAny` | `custom-mobile-token` | `mobile_points.get` |
| `mobile` | `POST` | `api/v1/mobile/points/redeem/` | `AllowAny` | `custom-mobile-token` | `mobile_redeem_points.post` |
| `mobile` | `GET` | `api/v1/mobile/profile/` | `AllowAny` | `custom-mobile-token` | `mobile_profile.get` |
| `mobile` | `POST` | `api/v1/mobile/refresh/` | `AllowAny` | `public` | `mobile_refresh.post` |
| `mobile` | `POST` | `api/v1/mobile/register/` | `AllowAny` | `public` | `mobile_register.post` |
| `mobile` | `GET` | `api/v1/mobile/settlement-inquiry/` | `AllowAny` | `custom-mobile-token` | `mobile_settlement_inquiry.get` |
| `mobile` | `POST` | `api/v1/mobile/settlement-inquiry/comment/` | `AllowAny` | `custom-mobile-token` | `mobile_settlement_inquiry_comment.post` |
| `mobile` | `POST` | `api/v1/mobile/settlement-inquiry/read/` | `AllowAny` | `custom-mobile-token` | `mobile_settlement_inquiry_read.post` |
| `mobile` | `GET` | `api/v1/mobile/settlements/` | `AllowAny` | `custom-mobile-token` | `mobile_settlements.get` |
| `mobile` | `POST` | `api/v1/mobile/signup/complete/` | `AllowAny` | `custom-mobile-token` | `mobile_complete_signup.post` |
| `mobile` | `GET` | `api/v1/mobile/status/` | `AllowAny` | `public` | `mobile_status.get` |
| `mobile` | `POST` | `api/v1/mobile/vehicle-inspection-date/` | `AllowAny` | `custom-mobile-token` | `mobile_update_vehicle_inspection_date.post` |
| `mobile` | `POST` | `api/v1/mobile/vehicle-number/` | `AllowAny` | `custom-mobile-token` | `mobile_update_vehicle_number.post` |
| `mobile` | `POST` | `api/v1/mobile/work-session/heartbeat/` | `AllowAny` | `custom-mobile-token` | `mobile_work_session_heartbeat.post` |
| `mobile` | `POST` | `api/v1/mobile/work-session/start/` | `AllowAny` | `custom-mobile-token` | `mobile_work_session_start.post` |
| `mobile` | `POST` | `api/v1/mobile/work-session/stop/` | `AllowAny` | `custom-mobile-token` | `mobile_work_session_stop.post` |
| `mobile` | `POST` | `api/v1/mobile/work-session/upload/` | `AllowAny` | `custom-mobile-token` | `mobile_work_session_upload.post` |
| `partner` | `GET` | `api/v1/partner/partners/` | `IsAuthenticated` | `jwt-authenticated` | `PartnerViewSet.list` |
| `partner` | `POST` | `api/v1/partner/partners/` | `IsAuthenticated` | `jwt-authenticated` | `PartnerViewSet.create` |
| `partner` | `DELETE` | `api/v1/partner/partners/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `PartnerViewSet.destroy` |
| `partner` | `GET` | `api/v1/partner/partners/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `PartnerViewSet.retrieve` |
| `partner` | `PATCH` | `api/v1/partner/partners/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `PartnerViewSet.partial_update` |
| `partner` | `PUT` | `api/v1/partner/partners/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `PartnerViewSet.update` |
| `points` | `GET` | `api/v1/points/crew/{crew_id}/` | `IsAuthenticated` | `jwt-authenticated` | `crew_point_detail.get` |
| `points` | `POST` | `api/v1/points/crew/{crew_id}/set-balance/` | `IsAuthenticated` | `jwt-authenticated` | `set_crew_point_balance.post` |
| `points` | `GET` | `api/v1/points/items/` | `IsAuthenticated` | `jwt-authenticated` | `point_items.get` |
| `points` | `POST` | `api/v1/points/items/` | `IsAuthenticated` | `jwt-authenticated` | `point_items.post` |
| `points` | `DELETE` | `api/v1/points/items/{item_id}/` | `IsAuthenticated` | `jwt-authenticated` | `point_item_detail.delete` |
| `points` | `PATCH` | `api/v1/points/items/{item_id}/` | `IsAuthenticated` | `jwt-authenticated` | `point_item_detail.patch` |
| `points` | `PUT` | `api/v1/points/items/{item_id}/` | `IsAuthenticated` | `jwt-authenticated` | `point_item_detail.put` |
| `points` | `POST` | `api/v1/points/redemptions/{redemption_id}/cancel/` | `IsAuthenticated` | `jwt-authenticated` | `cancel_redemption.post` |
| `points` | `POST` | `api/v1/points/redemptions/{redemption_id}/confirm/` | `IsAuthenticated` | `jwt-authenticated` | `confirm_redemption.post` |
| `points` | `GET` | `api/v1/points/summaries/` | `IsAuthenticated` | `jwt-authenticated` | `crew_point_summaries.get` |
| `region` | `GET` | `api/v1/region/price-history/` | `IsAuthenticated` | `jwt-authenticated` | `PriceHistoryViewSet.list` |
| `region` | `GET` | `api/v1/region/price-history/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `PriceHistoryViewSet.retrieve` |
| `region` | `GET` | `api/v1/region/prices/` | `IsAuthenticated` | `jwt-authenticated` | `RegionPriceViewSet.list` |
| `region` | `POST` | `api/v1/region/prices/` | `IsAuthenticated` | `jwt-authenticated` | `RegionPriceViewSet.create` |
| `region` | `DELETE` | `api/v1/region/prices/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `RegionPriceViewSet.destroy` |
| `region` | `GET` | `api/v1/region/prices/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `RegionPriceViewSet.retrieve` |
| `region` | `PATCH` | `api/v1/region/prices/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `RegionPriceViewSet.partial_update` |
| `region` | `PUT` | `api/v1/region/prices/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `RegionPriceViewSet.update` |
| `region` | `GET` | `api/v1/region/prices/{id}/price_history/` | `IsAuthenticated` | `jwt-authenticated` | `RegionPriceViewSet.price_history` |
| `region` | `GET` | `api/v1/region/regions/` | `IsAuthenticated` | `jwt-authenticated` | `RegionViewSet.list` |
| `region` | `POST` | `api/v1/region/regions/` | `IsAuthenticated` | `jwt-authenticated` | `RegionViewSet.create` |
| `region` | `DELETE` | `api/v1/region/regions/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `RegionViewSet.destroy` |
| `region` | `GET` | `api/v1/region/regions/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `RegionViewSet.retrieve` |
| `region` | `PATCH` | `api/v1/region/regions/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `RegionViewSet.partial_update` |
| `region` | `PUT` | `api/v1/region/regions/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `RegionViewSet.update` |
| `settlement` | `GET` | `api/v1/settlement/details/` | `IsAuthenticated` | `jwt-authenticated` | `SettlementDetailViewSet.list` |
| `settlement` | `POST` | `api/v1/settlement/details/` | `IsAuthenticated` | `jwt-authenticated` | `SettlementDetailViewSet.create` |
| `settlement` | `DELETE` | `api/v1/settlement/details/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `SettlementDetailViewSet.destroy` |
| `settlement` | `GET` | `api/v1/settlement/details/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `SettlementDetailViewSet.retrieve` |
| `settlement` | `PATCH` | `api/v1/settlement/details/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `SettlementDetailViewSet.partial_update` |
| `settlement` | `PUT` | `api/v1/settlement/details/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `SettlementDetailViewSet.update` |
| `settlement` | `GET` | `api/v1/settlement/settlements/` | `IsAuthenticated` | `jwt-authenticated` | `SettlementViewSet.list` |
| `settlement` | `POST` | `api/v1/settlement/settlements/` | `IsAuthenticated` | `jwt-authenticated` | `SettlementViewSet.create` |
| `settlement` | `POST` | `api/v1/settlement/settlements/generate/` | `IsAuthenticated` | `jwt-authenticated` | `SettlementViewSet.generate` |
| `settlement` | `GET` | `api/v1/settlement/settlements/web-crew-history/` | `IsAuthenticated` | `jwt-authenticated` | `SettlementViewSet.web_crew_history` |
| `settlement` | `GET` | `api/v1/settlement/settlements/web_overview/` | `IsAuthenticated` | `jwt-authenticated` | `SettlementViewSet.web_overview` |
| `settlement` | `DELETE` | `api/v1/settlement/settlements/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `SettlementViewSet.destroy` |
| `settlement` | `GET` | `api/v1/settlement/settlements/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `SettlementViewSet.retrieve` |
| `settlement` | `PATCH` | `api/v1/settlement/settlements/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `SettlementViewSet.partial_update` |
| `settlement` | `PUT` | `api/v1/settlement/settlements/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `SettlementViewSet.update` |
| `settlement` | `POST` | `api/v1/settlement/settlements/{id}/confirm/` | `IsAuthenticated` | `jwt-authenticated` | `SettlementViewSet.confirm` |
| `settlement` | `GET` | `api/v1/settlement/settlements/{id}/export/` | `IsAuthenticated` | `jwt-authenticated` | `SettlementViewSet.export` |
| `settlement` | `POST` | `api/v1/settlement/settlements/{id}/mark_paid/` | `IsAuthenticated` | `jwt-authenticated` | `SettlementViewSet.mark_paid` |
| `settlement` | `POST` | `api/v1/settlement/settlements/{id}/recalc/` | `IsAuthenticated` | `jwt-authenticated` | `SettlementViewSet.recalc` |
| `settlement` | `GET` | `api/v1/settlement/settlements/{id}/web-detail-groups/` | `IsAuthenticated` | `jwt-authenticated` | `SettlementViewSet.web_detail_groups` |
| `territory` | `GET` | `api/v1/territory/territories/` | `IsAuthenticated` | `jwt-authenticated` | `TerritoryViewSet.list` |
| `territory` | `POST` | `api/v1/territory/territories/` | `IsAuthenticated` | `jwt-authenticated` | `TerritoryViewSet.create` |
| `territory` | `POST` | `api/v1/territory/territories/import_geojson/` | `IsAuthenticated` | `jwt-authenticated` | `TerritoryViewSet.import_geojson` |
| `territory` | `DELETE` | `api/v1/territory/territories/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `TerritoryViewSet.destroy` |
| `territory` | `GET` | `api/v1/territory/territories/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `TerritoryViewSet.retrieve` |
| `territory` | `PATCH` | `api/v1/territory/territories/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `TerritoryViewSet.partial_update` |
| `territory` | `PUT` | `api/v1/territory/territories/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `TerritoryViewSet.update` |
| `territory` | `GET` | `api/v1/territory/territories/{id}/box_series/` | `IsAuthenticated` | `jwt-authenticated` | `TerritoryViewSet.box_series` |
| `territory` | `POST` | `api/v1/territory/territories/{id}/box_set/` | `IsAuthenticated` | `jwt-authenticated` | `TerritoryViewSet.box_set` |
| `territory` | `GET` | `api/v1/territory/territories/{id}/cycles_inside/` | `IsAuthenticated` | `jwt-authenticated` | `TerritoryViewSet.cycles_inside` |
| `territory` | `GET` | `api/v1/territory/territories/{id}/nearby_manpower/` | `IsAuthenticated` | `jwt-authenticated` | `TerritoryViewSet.nearby_manpower` |
| `tracking` | `GET` | `api/v1/tracking/live-status/` | `IsAuthenticated` | `jwt-authenticated` | `live_work_statuses.get` |
| `tracking` | `GET` | `api/v1/tracking/sessions/` | `IsAuthenticated` | `jwt-authenticated` | `TrackingSessionViewSet.list` |
| `tracking` | `POST` | `api/v1/tracking/sessions/` | `IsAuthenticated` | `jwt-authenticated` | `TrackingSessionViewSet.create` |
| `tracking` | `GET` | `api/v1/tracking/sessions/available_dates/` | `IsAuthenticated` | `jwt-authenticated` | `TrackingSessionViewSet.available_dates` |
| `tracking` | `DELETE` | `api/v1/tracking/sessions/bulk_delete/` | `IsAuthenticated` | `jwt-authenticated` | `TrackingSessionViewSet.bulk_delete` |
| `tracking` | `DELETE` | `api/v1/tracking/sessions/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `TrackingSessionViewSet.destroy` |
| `tracking` | `GET` | `api/v1/tracking/sessions/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `TrackingSessionViewSet.retrieve` |
| `tracking` | `PATCH` | `api/v1/tracking/sessions/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `TrackingSessionViewSet.partial_update` |
| `tracking` | `PUT` | `api/v1/tracking/sessions/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `TrackingSessionViewSet.update` |
| `tracking` | `GET` | `api/v1/tracking/sessions/{id}/ble/` | `IsAuthenticated` | `jwt-authenticated` | `TrackingSessionViewSet.ble` |
| `tracking` | `GET` | `api/v1/tracking/sessions/{id}/captures/` | `IsAuthenticated` | `jwt-authenticated` | `TrackingSessionViewSet.captures` |
| `tracking` | `GET` | `api/v1/tracking/sessions/{id}/cycles/` | `IsAuthenticated` | `jwt-authenticated` | `TrackingSessionViewSet.cycles` |
| `tracking` | `GET` | `api/v1/tracking/sessions/{id}/download_csv/` | `IsAuthenticated` | `jwt-authenticated` | `TrackingSessionViewSet.download_csv` |
| `tracking` | `GET` | `api/v1/tracking/sessions/{id}/points/` | `IsAuthenticated` | `jwt-authenticated` | `TrackingSessionViewSet.points` |
| `tracking` | `GET` | `api/v1/tracking/usage-overview/` | `IsAuthenticated` | `jwt-authenticated` | `tracking_usage_overview.get` |
| `vehicle` | `GET` | `api/v1/vehicle/as-requests/` | `IsAuthenticated` | `jwt-authenticated` | `ASRequestViewSet.list` |
| `vehicle` | `POST` | `api/v1/vehicle/as-requests/` | `IsAuthenticated` | `jwt-authenticated` | `ASRequestViewSet.create` |
| `vehicle` | `DELETE` | `api/v1/vehicle/as-requests/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `ASRequestViewSet.destroy` |
| `vehicle` | `GET` | `api/v1/vehicle/as-requests/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `ASRequestViewSet.retrieve` |
| `vehicle` | `PATCH` | `api/v1/vehicle/as-requests/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `ASRequestViewSet.partial_update` |
| `vehicle` | `PUT` | `api/v1/vehicle/as-requests/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `ASRequestViewSet.update` |
| `vehicle` | `POST` | `api/v1/vehicle/as-requests/{id}/complete/` | `IsAuthenticated` | `jwt-authenticated` | `ASRequestViewSet.complete` |
| `vehicle` | `GET` | `api/v1/vehicle/calendar/` | `IsAuthenticated` | `jwt-authenticated` | `CalendarEventViewSet.list` |
| `vehicle` | `POST` | `api/v1/vehicle/calendar/` | `IsAuthenticated` | `jwt-authenticated` | `CalendarEventViewSet.create` |
| `vehicle` | `DELETE` | `api/v1/vehicle/calendar/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `CalendarEventViewSet.destroy` |
| `vehicle` | `GET` | `api/v1/vehicle/calendar/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `CalendarEventViewSet.retrieve` |
| `vehicle` | `PATCH` | `api/v1/vehicle/calendar/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `CalendarEventViewSet.partial_update` |
| `vehicle` | `PUT` | `api/v1/vehicle/calendar/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `CalendarEventViewSet.update` |
| `vehicle` | `GET` | `api/v1/vehicle/companies/` | `IsAuthenticated` | `jwt-authenticated` | `CompanyViewSet.list` |
| `vehicle` | `GET` | `api/v1/vehicle/companies/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `CompanyViewSet.retrieve` |
| `vehicle` | `GET` | `api/v1/vehicle/pit-records/` | `IsAuthenticated` | `jwt-authenticated` | `PitRecordViewSet.list` |
| `vehicle` | `POST` | `api/v1/vehicle/pit-records/` | `IsAuthenticated` | `jwt-authenticated` | `PitRecordViewSet.create` |
| `vehicle` | `DELETE` | `api/v1/vehicle/pit-records/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `PitRecordViewSet.destroy` |
| `vehicle` | `GET` | `api/v1/vehicle/pit-records/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `PitRecordViewSet.retrieve` |
| `vehicle` | `PATCH` | `api/v1/vehicle/pit-records/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `PitRecordViewSet.partial_update` |
| `vehicle` | `PUT` | `api/v1/vehicle/pit-records/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `PitRecordViewSet.update` |
| `vehicle` | `GET` | `api/v1/vehicle/returns/` | `IsAuthenticated` | `jwt-authenticated` | `ReturnRequestViewSet.list` |
| `vehicle` | `POST` | `api/v1/vehicle/returns/` | `IsAuthenticated` | `jwt-authenticated` | `ReturnRequestViewSet.create` |
| `vehicle` | `DELETE` | `api/v1/vehicle/returns/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `ReturnRequestViewSet.destroy` |
| `vehicle` | `GET` | `api/v1/vehicle/returns/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `ReturnRequestViewSet.retrieve` |
| `vehicle` | `PATCH` | `api/v1/vehicle/returns/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `ReturnRequestViewSet.partial_update` |
| `vehicle` | `PUT` | `api/v1/vehicle/returns/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `ReturnRequestViewSet.update` |
| `vehicle` | `POST` | `api/v1/vehicle/returns/{id}/adjust/` | `IsAuthenticated` | `jwt-authenticated` | `ReturnRequestViewSet.adjust` |
| `vehicle` | `POST` | `api/v1/vehicle/returns/{id}/confirm/` | `IsAuthenticated` | `jwt-authenticated` | `ReturnRequestViewSet.confirm` |
| `vehicle` | `GET` | `api/v1/vehicle/subscriptions/` | `IsAuthenticated` | `jwt-authenticated` | `SubscriptionRequestViewSet.list` |
| `vehicle` | `POST` | `api/v1/vehicle/subscriptions/` | `IsAuthenticated` | `jwt-authenticated` | `SubscriptionRequestViewSet.create` |
| `vehicle` | `DELETE` | `api/v1/vehicle/subscriptions/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `SubscriptionRequestViewSet.destroy` |
| `vehicle` | `GET` | `api/v1/vehicle/subscriptions/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `SubscriptionRequestViewSet.retrieve` |
| `vehicle` | `PATCH` | `api/v1/vehicle/subscriptions/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `SubscriptionRequestViewSet.partial_update` |
| `vehicle` | `PUT` | `api/v1/vehicle/subscriptions/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `SubscriptionRequestViewSet.update` |
| `vehicle` | `POST` | `api/v1/vehicle/subscriptions/{id}/approve/` | `IsAuthenticated` | `jwt-authenticated` | `SubscriptionRequestViewSet.approve` |
| `vehicle` | `POST` | `api/v1/vehicle/subscriptions/{id}/assign/` | `IsAuthenticated` | `jwt-authenticated` | `SubscriptionRequestViewSet.assign` |
| `vehicle` | `POST` | `api/v1/vehicle/subscriptions/{id}/complete/` | `IsAuthenticated` | `jwt-authenticated` | `SubscriptionRequestViewSet.complete` |
| `vehicle` | `POST` | `api/v1/vehicle/subscriptions/{id}/reject/` | `IsAuthenticated` | `jwt-authenticated` | `SubscriptionRequestViewSet.reject` |
| `vehicle` | `GET` | `api/v1/vehicle/vehicles/` | `IsAuthenticated` | `jwt-authenticated` | `VehicleViewSet.list` |
| `vehicle` | `POST` | `api/v1/vehicle/vehicles/` | `IsAuthenticated` | `jwt-authenticated` | `VehicleViewSet.create` |
| `vehicle` | `GET` | `api/v1/vehicle/vehicles/stats/` | `IsAuthenticated` | `jwt-authenticated` | `VehicleViewSet.stats` |
| `vehicle` | `DELETE` | `api/v1/vehicle/vehicles/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `VehicleViewSet.destroy` |
| `vehicle` | `GET` | `api/v1/vehicle/vehicles/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `VehicleViewSet.retrieve` |
| `vehicle` | `PATCH` | `api/v1/vehicle/vehicles/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `VehicleViewSet.partial_update` |
| `vehicle` | `PUT` | `api/v1/vehicle/vehicles/{id}/` | `IsAuthenticated` | `jwt-authenticated` | `VehicleViewSet.update` |
