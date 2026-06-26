# Performance Tuning - 2026-05-20

## Scope

운영현황과 정산관리 조회 속도 개선을 위해 사용자 기능/API URL은 유지하고 내부 조회 방식만 변경했다.

## Changes

- `GET /api/v1/dispatch/uploads/operation-report/`
  - 기존 객체 prefetch 후 Python 루프 집계를 유지하되, 기본 경로를 DB aggregate 기반 빠른 집계 함수로 변경했다.
  - 응답 필드와 계산 기준은 기존과 동일하게 유지했다.
  - 배포 전후 같은 조건(`2026-05-01`~`2026-05-20`)의 응답 SHA256이 동일했다.

- `GET /api/v1/settlement/settlements/`
  - 목록 조회 기본값에서는 `details` 배열을 내려주지 않도록 변경했다.
  - 필요 시 `include_details=true`를 붙이면 기존처럼 상세 포함 응답을 받을 수 있다.
  - 정규/용차 합계는 상세 행을 직렬화하지 않고 annotate 집계값으로 계산한다.

- `GET /api/v1/settlement/settlements/web_overview/`
  - 달력/카드 overview에서 상세 행 prefetch를 제거했다.
  - 상세 화면은 기존 `web-detail-groups` API로 필요한 시점에만 조회한다.

## Production Measurements

Base URL: `http://43.201.160.163`

| API | Before | After cold | After repeated |
| --- | ---: | ---: | ---: |
| operation-report `2026-05-01`~`2026-05-20` | 8151 ms | 563 ms | 94~334 ms |
| settlements `limit=20` | 19824 ms | 194 ms | 136~213 ms |
| settlement web_overview `2026-05` | 8004 ms | 168 ms | 179~311 ms |

## Verification

- `python -m py_compile backend/apps/dispatch/views.py backend/apps/settlement/views.py backend/apps/settlement/serializers.py`
- `DEBUG=True python manage.py check`
  - 기존 경고: `backend/static` 경로 없음
- `npm --prefix frontend run build`
  - 기존 CSS minify warning 1건, 빌드 성공
- 운영 smoke:
  - web root, privacy, mobile app config, teams, dashboard KPI
  - operation report, operation report map, operation report CSV
  - settlements
- 운영 로그 확인:
  - 배포 후 `Traceback`, `ERROR`, `500` 없음

## Notes

- Django test runner는 로컬 SQLite 테스트 DB가 `field_mgr` 스키마를 지원하지 않아 마이그레이션 단계에서 중단됐다.
- 운영현황 응답은 배포 전후 SHA256이 동일했다.
- 정산 목록/overview 응답은 상세 배열 제거로 크기가 줄어들기 때문에 SHA256이 달라지는 것이 정상이다.

## Follow-up: Operation Preset Switching

운영현황 화면에서 `오늘`, `이번 주`, `이번 달` 전환 체감 속도를 추가 개선했다.

- 표 조회와 지도 조회를 분리했다.
  - 기존에는 표 API와 지도 API를 모두 기다린 뒤 한 번에 화면을 갱신했다.
  - 변경 후에는 표 API가 끝나는 즉시 표를 갱신하고, 지도는 별도 로딩 상태로 백그라운드 갱신한다.
- 같은 기간/조/화주사/물량 기준을 60초 안에 다시 선택하면 브라우저 메모리 캐시를 먼저 사용한다.
- 같은 조건의 요청이 이미 진행 중이면 새 요청을 만들지 않고 진행 중 Promise를 재사용한다.
- `조회` 버튼은 `force=true`로 남겨 두어 사용자가 명시적으로 새로 조회할 때는 서버를 다시 호출한다.

운영 브라우저 자동화 확인:

- 로그인 후 `/cheonha/operations` 진입 성공
- 프리셋 전환 후 표 로딩은 1초 이내 해제
- 캐시된 전환은 추가 report/map API 없이 즉시 화면 유지
- 프론트/nginx 로그 error 없음
