# 회귀 방지 게이트

이 문서는 운영 중인 기능을 유지한 채 내부 구조를 개선할 때 반드시 통과해야 하는 기준입니다. 리팩터링은 사용자에게 보이는 URL, 응답 필드, 버튼 동작을 바꾸지 않는 것을 기본값으로 둡니다.

장기 리팩터링 순서와 작업 단위 기준은 `docs/maintenance_refactor_roadmap.md`를 따릅니다.

## 배포 전 필수 명령

```powershell
python scripts/api_audit.py --no-write
python scripts/regression_gate.py
python scripts/prod_smoke_check.py
cd backend; $env:DEBUG='True'; python manage.py check
cd ..; cd backend; $env:DEBUG='True'; python manage.py test apps.dispatch.tests
cd ..; npm --prefix frontend run build
```

테스트 DB는 PostgreSQL 설정으로 실행하는 것을 기준으로 합니다. 로컬 기본 SQLite 설정에서는 schema-qualified table(`field_mgr`, `vehicle_mgmt`) 때문에 Django test DB 생성이 실패할 수 있습니다.

## 기능 보존 기준

- 웹 ERP: 로그인/로그아웃, 대시보드 조회, 배송원 수정/전환/삭제, 배차 업로드/설정/확정, 운영현황 조회/CSV/지도, 정산 상세/수정내역, 권역 저장/삭제, 포인트/차량/근무기록 관리가 유지되어야 합니다.
- 정산 앱: 로그인, 회원가입 약관 동의, 프로필 조회, 비밀번호/차량번호/계좌/검사일 저장, 정산 조회, 정산 문의, 근무 시작/종료/업로드가 유지되어야 합니다.
- API: `/api/v1/...` URL, request 파라미터, response 필드명, 권한 방식은 변경하지 않습니다.
- 실패 응답: 앱과 웹이 HTML 오류 페이지를 받지 않도록 JSON 오류 응답을 유지합니다.

## 정적 게이트

`scripts/regression_gate.py`는 Django URL resolver를 직접 읽어 핵심 버튼/앱 기능이 의존하는 endpoint가 남아 있는지 확인합니다.

- endpoint 삭제 여부
- `jwt-authenticated`, `public`, `custom-mobile-token`, `custom-field-manager-token` 노출 분류 변경 여부
- `BUTTON_API_MAP.md`에 핵심 기능 흐름 참조가 남아 있는지

이 스크립트가 실패하면 리팩터링은 배포 대상이 아닙니다. endpoint를 의도적으로 바꾸는 작업은 별도 계획과 프론트/앱 동시 수정, 운영 확인 절차가 필요합니다.

## 운영서버 Smoke

`scripts/prod_smoke_check.py`는 운영 서버에 읽기 전용 GET 요청만 보냅니다.

```powershell
python scripts/prod_smoke_check.py
$env:ADMIN_ACCESS_TOKEN='<운영 관리자 access token>'; python scripts/prod_smoke_check.py --start 2026-05-01 --end 2026-05-15
```

- 토큰이 없으면 웹 루트, 개인정보처리방침, 앱 설정 공개 API만 확인합니다.
- 토큰이 있으면 팀 목록, 대시보드 KPI, 운영현황, 운영현황 CSV, 용차 지도, 정산 목록까지 확인합니다.
- API가 HTML 오류 페이지를 반환하면 실패합니다. 앱에서 `Unexpected character: <`가 뜨는 상황을 배포 직후 잡기 위한 검사입니다.
- 이 스크립트는 데이터를 생성/수정/삭제하지 않습니다.

## 리팩터링 작업 규칙

- 한 배포에는 하나의 내부 리팩터링 주제만 포함합니다.
- DB schema 변경, API 정리, 성능 개선, UI 변경을 같은 배포에 섞지 않습니다.
- View/ViewSet은 public interface를 유지하고, 계산/집계/판정 로직만 서비스 함수로 옮깁니다.
- 서비스 함수는 먼저 단위 테스트를 붙이고, 기존 API 테스트가 같은 응답을 반환하는지 확인합니다.

## 운영 확인

배포 후 최근 운영 기간으로 아래를 확인합니다.

- 운영현황 숫자, 총계, CSV, 용차 지도
- 정산 상세 금액과 배송원별 금액
- 앱 로그인 후 프로필/정산 조회/근무 기록 화면
- Nginx/Django 로그의 4xx/5xx 증가 여부

문제가 확인되면 즉시 이전 배포본으로 되돌리고, 리팩터링 변경분은 별도 브랜치에서 재검증합니다.
