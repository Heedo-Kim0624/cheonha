# API 문서화/권한/중복 Endpoint 정리 기준

## 공식 API 표준

- 공식 문서에는 trailing slash가 있는 경로를 표준으로 적는다.
  - 표준: `/api/v1/dispatch/uploads/operation-report/`
  - 비표준: `/api/v1/dispatch/uploads/operation-report`
- DRF format suffix 경로는 공식 업무 API로 보지 않는다.
  - 예: `/api/v1/crew/members.json`
- DRF router root는 보조 endpoint로만 본다.
  - 예: `/api/v1/crew/`, `/api/v1/dispatch/`

## 권한 분류

| 분류 | 기준 | 예시 |
|---|---|---|
| `public` | 로그인 전 호출 가능 | 로그인, 회원가입, 앱 설정, 토큰 갱신 |
| `jwt-authenticated` | 관리자 웹 JWT 필요 | 배차, 정산, 배송원, 차량, 포인트 관리 |
| `custom-mobile-token` | 정산 앱 Bearer token 필요 | 앱 정산조회, 근무 시작/종료, 앱 포인트 |
| `custom-field-manager-token` | 현장관리자 앱 Bearer token 필요 | 구독/반납/A/S 요청, 요청 이력 |

## 현재 결론

- 업무 API는 168개 endpoint pattern, 256개 method-route다.
- 중복으로 보이는 route 대부분은 DRF `DefaultRouter`가 자동 생성하는 format suffix route다.
- 관리자 웹 API는 거의 모두 `IsAuthenticated`로 통일되어 있다.
- 모바일/현장관리자 API는 DRF 레벨에서는 `AllowAny`지만, 함수 내부에서 자체 Bearer token을 검증한다.
- 따라서 당장 endpoint를 제거하기보다, 공식 문서와 감사 파일에서 표준 경로와 권한 분류를 명확히 하는 방식이 안전하다.

## 다음 코드 정리 후보

1. 모바일/현장관리자 토큰 검증을 공통 helper 또는 permission 계층으로 분리한다.
2. OpenAPI 경고가 많은 함수형 API에 `@extend_schema`를 붙여 request/response serializer를 명시한다.
3. 새 API를 만들 때는 기존 domain prefix를 우선 사용하고, 화면 전용 API는 `web_`, `admin_`, `mobile_` 같은 접두사를 명확히 둔다.
4. 프론트 API 래퍼는 trailing slash 표준으로 통일한다. 단, 운영 서버 rewrite와 기존 앱 호환성을 확인한 뒤 진행한다.

## 산출물

- `docs/api_audit.md`: endpoint, 권한, 노출 분류 감사 문서
- `docs/api_inventory.csv`: CSV 형태의 전체 route inventory
- `docs/openapi.yaml`: drf-spectacular OpenAPI 3 스펙
- `scripts/api_audit.py`: 위 문서를 다시 생성하는 감사 스크립트
