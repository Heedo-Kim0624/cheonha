# ONE 정산 업로드/파싱/웨이브 매칭/표시 흐름

이 문서는 현재 `새회사(new)`의 화주사 `오네(one)` 정산 화면에서 파일 업로드부터 RAW 파싱, DB 저장, 웨이브 매칭, 월별 요약/기사별 명세서 표시까지 실제 코드가 어떤 기준으로 동작하는지 정리한 문서다.

## 1. 적용 범위

- 대상 회사: `company_app = new`
- 대상 화주사: `shipper_code = one`
- 기존 천하운수, ABC, CLEVER 통합관리 정산 로직과 분리된 ONE 전용 로직이다.
- 백엔드 앱: `backend/apps/one_settlement`
- 프론트 컴포넌트: `frontend/src/components/oneSettlement`
- 프론트 API 래퍼: `frontend/src/api/oneSettlement.js`

## 2. 전체 흐름 요약

```text
사용자 파일 업로드
  -> POST /api/v1/one/uploads/
  -> 엑셀 파일 바이트 읽기
  -> RAW 시트 파싱
  -> 주문번호/배송원/날짜/수수료명칭 정규화
  -> 일자 + 수수료명칭 + SM + 주문번호 기준으로 주문 그룹 생성
  -> 수수료명칭으로 웨이브/항목 매칭
  -> 단가 계산
  -> OneSettlementUpload / OneShipmentOrder / OneDriver 저장
  -> 월별 요약, 월별 취합, 배송원 목록, 배송원별 명세서 화면에서 조회
```

## 3. 업로드 API

프론트는 `OneSettlementPanel.vue`에서 파일 선택 또는 드래그 앤 드랍으로 `.xlsx`, `.xlsm` 파일을 받는다.

업로드 요청은 다음 API로 전송된다.

```http
POST /api/v1/one/uploads/
```

전송 파라미터:

```text
company_app = new
files[] = 업로드 엑셀 파일 목록
```

업로드 후 프론트는 다음 데이터를 다시 불러온다.

```text
GET /api/v1/one/uploads/
GET /api/v1/one/summary/
GET /api/v1/one/drivers/
```

## 4. 파일 중복 판단

중복 판단은 단순 파일명 기준이 아니다.

백엔드는 엑셀 안의 주요 시트를 읽어서 정규화된 내용을 해시로 만든다.

대상 시트:

```text
RAW
생수RAW
수기
```

동일한 내용의 파일이 다시 올라오면 같은 `raw_hash`가 생성되고, `OneSettlementUpload`에 이미 같은 해시가 있으면 중복 업로드로 처리된다.

## 5. RAW 시트 파싱 기준

현재 정산의 핵심 입력은 `RAW` 시트다.

필수 컬럼:

```text
일자
주문번호
수수료명칭
시군구
SM
```

파싱 시 주요 처리:

- `일자`는 배송일로 변환한다.
- `SM`은 배송원명으로 사용한다.
- 배송원명은 공백 정리 및 일부 이름 보정을 거친다.
- `수수료명칭`은 웨이브/항목 매칭의 기준으로 사용한다.
- `주문번호`가 비어 있는 경우 운송장번호와 인접 RAW 행 정보를 이용해 보정한다.
- `시군구`가 `종로구`면 종로 할증 계산에 사용한다.
- RAW 행 단위 금액은 원본 정산 금액 검증과 대시보드 금액 표시에 사용한다.

현재 배송원명 보정:

| 원본 | 보정 |
| --- | --- |
| 정승호 | 정승용 |
| 최기준 | 최길준 |

## 6. 주문 그룹 생성 기준

RAW 행을 그대로 한 줄씩 저장하지 않고, 아래 기준으로 묶어서 하나의 배송 주문 그룹으로 저장한다.

```text
일자 + 수수료명칭 + SM + 주문번호
```

이 기준으로 묶인 1개 그룹이 `1가구`다.

그룹 안에 들어간 RAW 행 수가 박스 수다.

```text
가구 수 = 주문 그룹 수
박스 수 = 같은 주문 그룹에 포함된 RAW 행 수
추가박스 = max(박스 수 - 1, 0)
```

예:

```text
같은 일자, 같은 수수료명칭, 같은 배송원, 같은 주문번호 RAW 행이 3개
-> 가구 1
-> 박스 3
-> 추가박스 2
```

## 7. 저장되는 주요 DB 모델

### OneSettlementUpload

업로드 파일 단위 기록이다.

주요 필드:

```text
company_app
shipper_code
month
delivery_date
original_filename
raw_hash
total_rows
order_count
mapped_order_count
unmapped_order_count
total_amount
validation_errors
status
```

### OneShipmentOrder

파싱된 주문 그룹 단위 기록이다.

주요 필드:

```text
upload
company_app
shipper_code
month
delivery_date
driver
driver_name
order_number
fee_name
service_code
category_code
city
boxes
extra_boxes
amount
base_amount
jongno_extra_amount
is_mapped
raw_payload
```

### OneDriver

SM 기준 배송원 마스터다.

업로드 중 새 배송원명이 나오면 자동 생성된다.

### OneDriverStatementOverride

배송원별 명세서에서 수정하는 지급 예정일, 수기 항목, 메모를 저장한다.

## 8. 웨이브 매칭 기준

웨이브 매칭은 `수수료명칭` 문자열을 기준으로 한다.

저장되는 서비스 코드:

| 화면 표시 | 코드 |
| --- | --- |
| W1,2_당일 | `W12_DAY` |
| N3_당일 | `N3_DAY` |
| W4_새벽 | `W4_DAWN` |

저장되는 항목 코드:

| 화면 표시 | 코드 |
| --- | --- |
| SSG | `SSG` |
| 공동배송 | `COMMON` |
| 트레이더스 | `TRADERS` |
| YES24 | `YES24` |

### 8.1 W1,2_당일 매칭

수수료명칭에 `1W` 또는 `2W`가 있으면 기본적으로 `W1,2_당일`로 본다.

그 안에서 다음처럼 항목을 나눈다.

```text
YES24 또는 도서 포함 -> YES24
트레이더스 또는 애플 포함 -> 트레이더스
공동 포함 -> 공동배송
SSG 포함 -> SSG
```

### 8.2 N3_당일 매칭

수수료명칭에 `당일` 또는 `일요`가 있고 `N3` 조건에 맞으면 `N3_당일`로 본다.

```text
3W + SSG -> N3_당일 / SSG
YES24 또는 도서 -> N3_당일 / YES24
```

### 8.3 W4_새벽 매칭

수수료명칭에 `새벽`이 있으면 `W4_새벽`으로 본다.

```text
공동배송 포함 -> W4_새벽 / 공동배송
도서 또는 YES24 포함 -> W4_새벽 / YES24
SSG 포함 -> W4_새벽 / SSG
```

### 8.4 미매칭

위 규칙에 걸리지 않으면 다음 상태로 저장된다.

```text
service_code = ""
category_code = ""
is_mapped = false
```

미매칭이 있으면 업로드 상태가 `NEEDS_REVIEW`가 되고, 업로드 기록에 미매칭 수수료명칭이 남는다.

## 9. 예외 매칭

현재 코드에는 원본 자료와 맞추기 위한 일부 주문 단위 예외가 있다.

### 9.1 주문번호 보정 예외

```text
2026-05-09 / 조정훈 / 6979-0724-9755 -> 6979-0724-9755
2026-05-20 / 박형배 / 6981-1097-5740 -> 6980-9960-0600
```

### 9.2 카테고리 보정 예외

```text
2026-05-16 / 이현국 / 10201307949 -> N3_당일 / SSG
```

이 예외들은 현재 기준 파일과 일치시키기 위한 보정값이다.

## 10. 단가 계산 기준

정산 금액은 웨이브/항목/박스 수에 따라 계산된다.

### 10.1 W1,2_당일 SSG

박스 수별 테이블 단가를 사용한다.

```text
1박스 2,370원
2박스 2,670원
3박스 2,870원
4박스 3,360원
5박스 3,850원
5박스 초과 시 초과 박스당 400원 추가
```

### 10.2 N3_당일 SSG

박스 수별 테이블 단가를 사용한다.

```text
1박스 2,570원
2박스 2,870원
3박스 3,070원
4박스 3,560원
5박스 4,050원
5박스 초과 시 초과 박스당 400원 추가
```

### 10.3 W4_새벽 SSG/공동배송

박스 수별 테이블 단가를 사용한다.

```text
1박스 2,600원
2박스 2,800원
3박스 3,000원
4박스 3,200원
5박스 3,400원
5박스 초과 시 초과 박스당 200원 추가
```

### 10.4 YES24

YES24는 고정 단가를 사용한다.

```text
W1,2_당일 YES24 = 1,430원
N3_당일 YES24 = 1,430원
W4_새벽 YES24 = 2,475원
```

### 10.5 W1,2_당일 공동배송/트레이더스

배송원별 월 물량 구간에 따라 기본 단가를 정한다.

```text
500건 미만: 1,650원
800건 미만: 1,630원
1,100건 미만: 1,610원
1,400건 미만: 1,590원
1,700건 미만: 1,570원
2,000건 미만: 1,550원
2,300건 미만: 1,530원
2,300건 이상: 1,510원
```

트레이더스는 추가박스 금액을 별도로 더한다.

```text
추가박스 * 1,000원
```

### 10.6 종로구 할증

`시군구 == 종로구`이면 그룹 박스 수마다 200원이 추가된다.

```text
종로 할증 = 박스 수 * 200원
최종 지급액 = 기본 계산액 + 종로 할증
```

## 11. 원본 금액과 지급액의 차이

현재 ONE 데이터에는 두 종류의 금액이 같이 존재한다.

### 11.1 source 금액

RAW 파일에서 읽은 원본 금액이다.

주로 `CJ대한통운 ONE 정산` 대시보드와 원본 검은 표 기준 금액 비교에 사용한다.

코드상 주요 필드:

```text
source_amount
source_base_amount
source_extra_amount
source_total_amount
```

### 11.2 calculated 지급액

현재 코드의 단가표로 다시 계산한 배송원 지급액이다.

주로 배송원별 정산, 지급명세서, 기사별 정산 총량에 사용한다.

코드상 주요 필드:

```text
amount
base_amount
jongno_extra_amount
total_amount
```

따라서 화면에서 `CJ대한통운 ONE 정산` 금액과 `기사별 정산 총량` 금액은 의도적으로 다른 기준을 볼 수 있다.

## 12. 월별 요약 집계 기준

월별 요약 API:

```http
GET /api/v1/one/summary/?company_app=new&month=YYYY-MM
```

월별 요약은 크게 두 축으로 나뉜다.

### 12.1 검은 대시보드 표 기준

원본 대시보드와 맞추기 위한 기준이다.

집계 키:

```text
서비스 + 항목 + 주문번호
```

특징:

- 배송원은 집계 키에서 제외한다.
- 날짜도 월 전체 기준에서는 제외한다.
- 같은 주문번호가 여러 행에 나뉘어 있어도 원본 검은 표와 맞도록 주문번호 기준으로 합친다.
- `CJ대한통운 ONE 배송 수량`, `CJ대한통운 ONE 정산` 화면에서 사용한다.

### 12.2 일자별 검은 대시보드 표 기준

일자별 표에서는 날짜를 포함한다.

집계 키:

```text
일자 + 서비스 + 항목 + 주문번호
```

`일자별 배송 수량`, `일자별 ONE 정산` 표에서 사용한다.

### 12.3 기사별 기준

기사별 화면과 지급명세서는 배송원 기준을 유지한다.

집계 키:

```text
배송원 + 서비스 + 항목
```

또는 명세서 상세에서는:

```text
배송원 + 일자 + 서비스 + 항목
```

이 기준은 실제 지급 대상자를 구분해야 하기 때문에 검은 대시보드 표 기준과 다르다.

## 13. 월별 요약 화면 표시

프론트 컴포넌트:

```text
OneMonthlySummaryDashboard.vue
```

상단에는 4개 요약 선택 항목이 있다.

```text
CJ대한통운 ONE 배송 수량
CJ대한통운 ONE 정산
기사별 배송 총량
기사별 정산 총량
```

각 항목을 클릭하면 아래 표가 바뀐다.

### 13.1 CJ대한통운 ONE 배송 수량

사용 데이터:

```text
summary.by_service
summary.by_day_service
summary.by_day
```

표시 내용:

- 월 전체 기준 서비스/항목별 착지/건
- 월 전체 기준 서비스/항목별 추가박스
- 일자별 배송 수량 표

### 13.2 CJ대한통운 ONE 정산

사용 데이터:

```text
source_base_amount
source_extra_amount
source_total_amount
```

표시 내용:

- 원본 RAW 기준 착지/건 금액
- 원본 RAW 기준 추가박스 금액
- 원본 RAW 기준 총 정산 금액
- 일자별 ONE 정산 표

### 13.3 기사별 배송 총량

사용 데이터:

```text
summary.by_driver_service
drivers
```

표시 내용:

- 배송원별 서비스/항목별 착지/건
- 배송원별 서비스/항목별 추가박스

### 13.4 기사별 정산 총량

사용 데이터:

```text
summary.by_driver_service
drivers
```

표시 내용:

- 배송원별 서비스/항목별 계산 지급액
- 배송원별 총 지급액

## 14. 월별 취합 탭

탭 이름:

```text
월별 취합
```

API:

```http
GET /api/v1/one/summary/collection/
GET /api/v1/one/summary/collection-export/
```

목적:

- 업로드된 RAW 데이터를 `취합B_(기사)` 양식에 맞게 다시 펼쳐서 보여준다.
- 웹에서는 페이지네이션된 표로 보여준다.
- Excel 다운로드를 제공한다.

주요 컬럼:

```text
일자
주문번호
운송장번호
구분
수수료명칭
시군구
기준단가
할증유형1
할증유형2
할증유형3
합계
배송완료시간
SM
받는분
받는분주소
비고
```

## 15. 배송원 목록 탭

API:

```http
GET /api/v1/one/drivers/?company_app=new&month=YYYY-MM
```

표시 내용:

```text
배송원명
가구 수
박스 수
추가박스 수
지급액
원본 금액
```

배송원은 RAW의 `SM` 기준으로 자동 생성된다.

## 16. 배송원별 정산 탭

API:

```http
GET /api/v1/one/drivers/{driverId}/statement/
PATCH /api/v1/one/statements/{statementId}/
GET /api/v1/one/statements/{statementId}/export.xlsx/
GET /api/v1/one/statements/{statementId}/export.pdf/
```

화면 컴포넌트:

```text
OneStatementSheet.vue
```

표시 내용:

- 운송료 지급명세서
- 지급 대상자
- 정산 기간
- 지급 예정일
- 지급내역 요약
- 일자별 배송/추가박스 매트릭스
- 운송료 외/생수/사고귀책 수기 금액 입력
- 메모
- Excel/PDF 다운로드

웹 명세서 양식 안의 다음 금액 칸은 직접 숫자를 입력할 수 있다.

```text
생수
추가 전달
수당
사고귀책
```

입력한 값은 저장 시 `manual_items`에 반영되고, 지급 합계와 Excel/PDF 다운로드에도 반영된다.

지급 예정일 기본값:

```text
정산월의 다음 달 25일
```

예:

```text
2026년 05월 정산 -> 2026년 06월 25일
```

## 17. 현재 검증 기준 예시

2026년 5월 기준으로 통합 파일 3개를 업로드했을 때, 현재 월별 요약은 다음 방향으로 맞춰져 있다.

```text
업로드 파일 수: 3
미매칭 주문 수: 0
원본/CJ 정산 총액: 247,859,080원
```

원본 검은 대시보드 표와 맞춰야 하는 기준은 `CJ대한통운 ONE 배송 수량`, `CJ대한통운 ONE 정산` 쪽이다.

배송원별 명세서와 기사별 총량은 실제 지급 대상자별 계산을 위한 별도 기준이다.

## 18. 현재 구조에서 특히 헷갈리기 쉬운 부분

### 18.1 대시보드와 기사별 명세서는 같은 집계가 아니다

대시보드는 원본 검은 표와 맞추기 위해 `주문번호` 중심으로 묶는다.

기사별 명세서는 배송원에게 지급해야 하므로 `SM`을 유지한다.

따라서 어떤 주문번호가 여러 배송원/날짜/행에 걸쳐 있으면 대시보드 집계와 기사별 집계의 세부 수치가 다르게 보일 수 있다.

### 18.2 RAW 원본 금액과 계산 지급액도 다르다

`CJ대한통운 ONE 정산`은 RAW 원본 금액 기준이다.

`배송원별 정산`은 코드의 단가표로 계산한 지급액 기준이다.

### 18.3 수수료명칭 매칭이 핵심이다

수수료명칭이 웨이브/항목으로 매칭되지 않으면 그 주문은 월별 요약과 명세서 계산에서 정상 반영되지 않는다.

새로운 수수료명칭이 생기면 우선 `classify_fee_name()` 매핑을 확인해야 한다.

## 19. 수정이 필요할 때 봐야 할 파일

### 업로드/파싱/저장

```text
backend/apps/one_settlement/services.py
backend/apps/one_settlement/views.py
backend/apps/one_settlement/models.py
backend/apps/one_settlement/constants.py
```

### URL/API 연결

```text
backend/apps/one_settlement/urls.py
frontend/src/api/oneSettlement.js
```

### 화면 표시

```text
frontend/src/components/oneSettlement/OneSettlementPanel.vue
frontend/src/components/oneSettlement/OneMonthlySummaryDashboard.vue
frontend/src/components/oneSettlement/OneStatementSheet.vue
```

### 일괄 재업로드/초기화

```text
backend/apps/one_settlement/management/commands/import_one_data_folder.py
```

사용 예:

```bash
python manage.py import_one_data_folder "ONE/data" --company-app new --clear-month 2026-05
```

주의:

```text
폴더를 재귀적으로 읽으므로 테스트 파일이나 원본 대시보드 파일이 섞이지 않은 업로드 전용 폴더를 쓰는 것이 안전하다.
```

## 20. 앞으로 매핑/단가를 바꿀 때의 권장 방향

- 수수료명칭 매핑은 `classify_fee_name()`에서만 바꾸는 것이 좋다.
- 단가표는 `constants.py`에 둔 값을 수정하는 방향이 좋다.
- 원본 대시보드와 맞추는 집계 기준은 `build_month_summary()`의 대시보드 그룹 기준을 바꿔야 한다.
- 배송원별 지급 기준은 기사별 명세서 로직을 바꿔야 한다.
- 두 기준을 섞으면 원본 검증과 지급 명세서가 동시에 깨질 수 있다.
