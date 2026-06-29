# 새회사 ONE 정산 v1 구현 기록

## 범위

- 대상 회사: `새회사` (`company_app=new`)
- 대상 화주사: `오네` (`shipper_code=one`)
- 화면 진입: `/company/new/settlement`에서 화주사 `오네` 선택 시 ONE 전용 화면 표시
- 기존 천하운수, ABC, CLEVER 통합관리 정산/배차 로직과 분리

## 데이터 입력

- `ONE/data` 엑셀 파일의 `RAW` 시트만 사용한다.
- `생수RAW`, `수기` 등 다른 시트는 v1 계산에서 제외한다.
- RAW 1행은 헤더, 2행은 보조 설명 행, 3행부터 데이터로 처리한다.
- 필수 컬럼:
  - `일자`
  - `주문번호`
  - `수수료명칭`
  - `시군구`
  - `SM`

## 그룹핑 규칙

동일한 아래 조합을 하나의 착지, 즉 1가구로 본다.

```text
일자 + 수수료명칭 + SM + 주문번호
```

- 같은 그룹 안의 RAW 행 수 = 박스 수
- `착지/건` = 주문번호 그룹 수
- `추가박스` = `max(박스 수 - 1, 0)`의 합
- `시군구 == 종로구`이면 해당 그룹의 박스 수마다 200원 추가

## 임시 수수료명칭 매핑

실제 오네 기준표가 확정되기 전까지 아래 매핑으로 시작한다.

| RAW 수수료명칭 패턴 | 서비스 | 항목 |
| --- | --- | --- |
| `새벽_*SSG*` | `W4_새벽` | `SSG` |
| `새벽_*공동배송*` | `W4_새벽` | `공동배송` |
| `새벽_*도서*`, `새벽_*YES24*` | `W4_새벽` | `YES24` |
| `당일_*N3*SSG*`, `일요_*N3*SSG*` | `N3_당일` | `SSG` |
| `당일_*N3*도서*`, `일요_*N3*YES24*` | `N3_당일` | `YES24` |
| `*1W*`, `*2W*` + `SSG` | `W1,2_당일` | `SSG` |
| `*1W*`, `*2W*` + `공동` | `W1,2_당일` | `공동배송` |
| `*1W*`, `*2W*` + `트레이더` | `W1,2_당일` | `트레이더스` |
| `*1W*`, `*2W*` + `도서/YES24` | `W1,2_당일` | `YES24` |

매핑 교체 지점:

- `backend/apps/one_settlement/services.py`의 `classify_fee_name`
- 단가표는 `backend/apps/one_settlement/constants.py`

## 백엔드 구조

신규 Django 앱:

```text
backend/apps/one_settlement
```

주요 모델:

- `OneDriver`: SM 기준 자동 배송원
- `OneSettlementUpload`: 업로드 원본 및 RAW 해시
- `OneShipmentOrder`: 그룹핑된 착지/가구 단위 정산 행
- `OneDriverStatementOverride`: 지급 예정일, 수기 항목, 메모 수정값

주요 API:

- `POST /api/v1/one/uploads/`
- `GET /api/v1/one/uploads/`
- `GET /api/v1/one/summary/`
- `GET /api/v1/one/drivers/`
- `GET /api/v1/one/drivers/{id}/statement/`
- `PATCH /api/v1/one/statements/{id}/`
- `GET /api/v1/one/statements/{id}/export.xlsx/`
- `GET /api/v1/one/statements/{id}/export.pdf/`

## 프론트 구조

신규 화면 컴포넌트:

```text
frontend/src/components/oneSettlement/OneSettlementPanel.vue
```

회사 정산 화면:

```text
frontend/src/views/SettlementView.vue
```

분기 규칙:

- 화주사 선택값이 `one`이면 ONE 전용 패널 표시
- `one` 상태에서는 기존 정산 overview API를 호출하지 않음
- `new` 회사의 활성 화주사에 `one`이 있으면 기본 선택값을 `one`으로 둠

## 검증 기준

테스트 파일:

```text
backend/apps/one_settlement/tests.py
```

검증 내용:

- `RAW`만 읽고 다른 시트는 무시
- 동일 RAW 해시 업로드 중복 방지
- `임준형` 2026년 5월 샘플:
  - W4_새벽 / SSG 착지 993건
  - 추가박스 1008
  - 금액 2,783,400원

## v1 제외 항목

- 생수 정산
- 추가 전달
- 지원금
- 사고귀책 상계건
- 수수료명칭 확정 매핑

위 항목은 배송원별 지급명세서의 수기 수정 항목으로 우선 처리한다.
