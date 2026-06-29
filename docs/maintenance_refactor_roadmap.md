# 유지보수 친화 구조 개선 로드맵

이 문서는 운영 중인 천하/CLEVER 시스템을 천천히 안전하게 리팩터링하기 위한 기준 문서입니다. 모든 변경은 이 문서와 `docs/regression_gate.md`를 기준으로 작게 나누어 진행합니다.

## 원칙

- 기존 버튼, 화면, 앱, API 동작을 우선 보존합니다.
- URL, request 파라미터, response 필드명, 권한 방식은 기본적으로 변경하지 않습니다.
- 한 번에 하나의 리팩터링 주제만 배포합니다.
- 기능 추가, UI 변경, DB schema 변경, endpoint 정리는 내부 구조 개선과 섞지 않습니다.
- 각 단계는 `문서 갱신 -> 코드 변경 -> 로컬 검증 -> 운영 배포 -> 운영 smoke` 순서로 진행합니다.
- 운영 smoke가 통과하지 않으면 다음 단계로 넘어가지 않습니다.

## 현재 완료된 안전장치

- API inventory/audit 문서화: `docs/api_audit.md`, `docs/api_inventory.csv`, `docs/openapi.yaml`
- API 운영 기준 문서화: `docs/api_policy.md`
- 회귀 게이트 문서화: `docs/regression_gate.md`
- 정적 회귀 게이트 스크립트: `scripts/regression_gate.py`
- 운영서버 smoke 스크립트: `scripts/prod_smoke_check.py`
- 운영현황 금액 집계 서비스화: `backend/apps/dispatch/operation_report_services.py`
- 운영현황 summary 계산 서비스화
- 운영현황 CSV 헤더/행 조립 서비스화

## 단계별 진행 계획

### 1. Dispatch: 운영현황/배차/정산 생성 안정화

목표: `backend/apps/dispatch/views.py`에 집중된 운영현황과 배차 확정 로직을 작은 서비스 함수로 분리합니다.

작업 순서:

1. 운영현황 용차 지도 집계 로직 분리
   - 대상: `operation-report-yongcha-map`
   - 보존: `summary`, `results`, `yongcha_dates`, `level`, `geometry` 응답 구조
   - 검증: 운영 smoke에서 지도 API JSON 200 및 HTML 미반환 확인

2. 운영현황 권역 목록 로직 분리
   - 대상: `operation-report-territories`
   - 보존: 권역 id/code/team/centroid/geometry 구조

3. 배차 업로드 파일명 날짜 판정 로직 분리
   - 대상: 출근일/배송일/회차/시간 파싱
   - 보존: 기존 업로드 결과의 `dispatch_date`, `source_date`, `round_no`

4. 배차 확정 정산 생성 로직 분리
   - 대상: `finalize`
   - 보존: Settlement/SettlementDetail 생성 결과, 금액 산식, 응답 구조

각 작업 후 필수 검증:

```powershell
python scripts/api_audit.py --no-write
python scripts/regression_gate.py
cd backend; $env:DEBUG='True'; python manage.py check
cd ..; npm --prefix frontend run build
$env:ADMIN_ACCESS_TOKEN='<운영 관리자 access token>'; python scripts/prod_smoke_check.py --start <최근 시작일> --end <최근 종료일>
```

### 2. Settlement: 정산 산식/상세/내보내기 정리

목표: 정산 금액 산식과 조회 구조를 한 곳에서 관리합니다.

작업 순서:

1. 정산 합계 계산 함수 분리
   - `total_receive`, `total_pay`, `total_overtime`, `total_other_cost`, `total_profit`

2. 정산 상세 그룹 조회 분리
   - 대상: 정산 처리 화면 상세 토글
   - 보존: 회차별 정규/용차 그룹 구조

3. 정산 export 생성 분리
   - 보존: 기존 다운로드 파일 형식과 필드 순서

4. 과거 정산 재계산 로직 분리
   - 보존: 단가 변경 시 “과거 정산 반영” 동작

### 3. Crew: 배송원/용차/단가 변경 정리

목표: 배송원 상태 변경이 정산과 충돌하지 않도록 명확히 분리합니다.

작업 순서:

1. 정규/용차 판정 함수 정리
   - 보존: 정규 배송원, 용차 배송원, 회차별 용차 설정 결과

2. 단가 변경 처리 분리
   - 보존: “과거 정산 반영 예/아니요” 동작

3. 정규/용차 전환 처리 분리
   - 보존: 페이지 이동 없이 현재 탭 유지

4. 배송원 정산 이력 조회 분리
   - 보존: 기존 팝업/월별 이력 구조

### 4. Mobile: 앱 API 안정화

목표: 앱에서 HTML 오류 응답을 받지 않도록 모바일 API 인증/오류 형식을 정리합니다.

작업 순서:

1. 모바일 Bearer token 검증 공통화
   - 보존: 기존 토큰 형식과 앱 로그인 세션

2. 앱 설정/문구 조회 공통화
   - 보존: 앱 관리에서 수정한 문구와 약관 URL 반영

3. 프로필/차량번호/계좌/검사일 저장 로직 분리
   - 보존: 앱 재설치 없이 서버 문구/응답 정상화

4. 근무 시작/종료/업로드 로직 분리
   - 보존: 위치/BLE/CSV 업로드 흐름

### 5. Field Manager: 현장관리자 앱 정리

목표: 현장관리자 자체 토큰 검증과 요청 생성 로직을 분리합니다.

작업 순서:

1. field-manager token 발급/검증 공통화
2. 구독/반납/A/S 요청 생성 로직 분리
3. blocked dates/request history 조회 분리

### 6. API 문서화/권한/중복 정리

이 단계는 위 서비스화가 충분히 진행된 뒤 마지막에 수행합니다.

작업 순서:

1. 함수형 API에 OpenAPI schema 보강
2. 모바일/현장관리자 자체 토큰을 DRF permission 계층으로 이동
3. 프론트 API wrapper의 trailing slash 표준화
4. 중복 endpoint 사용처 확인
5. deprecated endpoint 표시 후 제거

## 작업 단위 템플릿

각 작업은 시작 전에 아래 항목을 문서 또는 작업 메모에 남깁니다.

```markdown
## 작업명

### 목표
- 

### 변경 범위
- 

### 변경하지 않는 것
- URL:
- request/response:
- 권한:
- DB schema:

### 위험 요소
- 

### 로컬 검증
- 

### 운영 검증
- 

### 롤백 기준
- 
```

## 배포 기준

배포 전:

- `api_audit` 결과의 endpoint/method-route 수가 의도 없이 변하지 않아야 합니다.
- `regression_gate`가 통과해야 합니다.
- `manage.py check`가 통과해야 합니다.
- 프론트 build가 통과해야 합니다.
- 운영 smoke를 배포 전/후 모두 실행합니다.

배포 후:

- 운영 smoke가 통과해야 합니다.
- 운영현황/정산/앱 핵심 조회가 HTML 오류를 반환하지 않아야 합니다.
- Nginx/Django 로그에서 새 4xx/5xx 증가가 없어야 합니다.

## 보류 원칙

아래 상황이면 다음 리팩터링으로 넘어가지 않습니다.

- 운영 smoke 실패
- 운영현황/정산 숫자 불일치
- 앱에서 JSON parse 오류 발생
- API endpoint 수 또는 권한 분류가 의도 없이 변경됨
- 배포 후 로그에 새 500 오류 발생
