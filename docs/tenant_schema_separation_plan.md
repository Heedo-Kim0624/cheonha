# 회사별 스키마 분리 계획

## 결정 사항

분리 방식은 **Shared DB + Separate Schema**로 간다.

- PostgreSQL DB는 현재처럼 하나를 사용한다.
- `public` schema는 중앙 관리 영역으로 둔다.
- 회사별 운영 데이터는 `tenant_<company_code>` schema에 둔다.
- 천하운수도 최종적으로 `tenant_cheonha` schema로 옮긴다.
- 화주사는 schema를 나누지 않고, 각 tenant schema 안에서 `shipper_code`로 구분한다.

## 최종 목표 구조

```text
DB: cheonha

public
  accounts_companyapp        # 회사 목록, 승인, 삭제/복구 상태
  accounts_shipper           # 컬리, 쿠팡, 오네 같은 화주사 메타데이터
  accounts_user              # CLEVER 관리자와 중앙 관리용 사용자
  django_migrations          # public schema migration 이력

tenant_cheonha
  accounts_user
  accounts_team
  crew_crewmember
  dispatch_dispatchupload
  dispatch_dispatchrecord
  settlement_settlement
  settlement_settlementdetail
  region_region
  tracking_...
  points_...

tenant_new
  accounts_user
  accounts_team
  crew_crewmember
  dispatch_...
  settlement_...
```

## 현재 구조와 차이

현재는 1개 DB, 1개 schema, 공유 테이블 구조다.

```text
public.accounts_team
public.crew_crewmember
public.dispatch_dispatchupload
public.settlement_settlement
```

그리고 `company_app = "cheonha"`, `company_app = "new"` 같은 컬럼으로 회사를 구분한다.

스키마 분리 후에는 같은 테이블명이 회사별 schema 안에 따로 생긴다.

```text
tenant_cheonha.dispatch_dispatchupload
tenant_new.dispatch_dispatchupload
```

## 제일 중요한 안전 원칙

- 천하운수 운영 트래픽은 최종 전환 전까지 계속 현재 public 테이블을 사용한다.
- `tenant_cheonha`는 먼저 shadow schema로 만든다.
- shadow schema에 데이터를 복사해도 실제 서비스는 읽지 않는다.
- count/hash/API 결과 비교가 통과하기 전에는 라우팅을 켜지 않는다.
- 라우팅은 feature flag로 회사 단위로 켠다.
- 문제가 생기면 flag를 끄면 즉시 기존 public 테이블로 돌아와야 한다.
- 기존 URL, 버튼, request/response 구조는 바꾸지 않는다.

## 모델 분류

### 중앙 모델

`public`에만 둔다.

- `accounts.CompanyApp`
- `accounts.Shipper`

### Dual 모델

`public`에도 있고, 각 tenant schema에도 있다.

- `accounts.User`

이유:

- `public.accounts_user`는 CLEVER 관리자, 회사 승인자, 중앙 관리용 사용자에 필요하다.
- `tenant_<company>.accounts_user`는 해당 회사의 ERP/앱 로그인 사용자에 필요하다.
- 현재 `CompanyApp.representative_user`, `approved_by`, `deleted_by` 등이 `User`를 FK로 참조하므로 `public.accounts_user`는 계속 필요하다.

### Tenant 모델

회사 운영 데이터이므로 각 tenant schema에 둔다.

- `accounts.Team`
- `crew.*`
- `dispatch.*`
- `settlement.*`
- `region.*`
- `territory.*`
- `inquiry.*`
- `tracking.*`
- `points.*`
- `mobile.*`
- `manpower.*`
- 필요 시 `vehicle_management.*`, `field_manager.*`

주의:

- 현재 `field_manager`, `vehicle_management` 일부 모델은 `db_table = 'field_mgr"."session'` 같은 방식으로 schema가 하드코딩되어 있다.
- 이런 모델은 `search_path`를 바꿔도 tenant schema로 가지 않는다.
- 따라서 이 도메인은 다음 중 하나를 별도 결정해야 한다.
  - 중앙 공통 기능으로 유지한다.
  - tenant schema 대상에서 제외한다.
  - `db_table` 하드코딩을 제거하고 tenant schema로 들어가게 리팩터링한다.
- 천하운수 정산/배차/배송원/운영현황 전환과 섞지 말고 별도 단계로 처리한다.

## 요청 처리 방식

### 일반 회사 화면

1. 프론트가 기존처럼 `X-Company-App: cheonha`를 보낸다.
2. middleware가 회사 코드를 확인한다.
3. 회사 코드가 tenant routing 대상이면 DB connection의 `search_path`를 설정한다.
   - 예: `tenant_cheonha, public`
4. Django ORM은 기존 코드 그대로 `DispatchUpload.objects...`를 호출한다.
5. PostgreSQL이 `tenant_cheonha.dispatch_dispatchupload`를 읽는다.
6. 요청 종료 시 `search_path`를 기본값으로 되돌린다.

### CLEVER 통합관리

회사관리, 화주사관리, 승인/삭제/복구는 중앙 관리 기능이다.

- 항상 `public` 기준으로 동작해야 한다.
- tenant schema의 운영 테이블을 직접 수정하지 않는다.
- tenant schema 생성/복구/비활성화는 별도 명령 또는 명시적 관리 API로만 한다.

### 로그인

로그인은 가장 조심해야 한다.

1. `X-Company-App`으로 회사 코드를 받는다.
2. 해당 회사가 tenant routing 대상이면 먼저 `search_path`를 tenant schema로 설정한다.
3. 해당 schema의 `accounts_user`에서 인증한다.
4. JWT에는 `company_app`을 넣는다.
5. 이후 요청에서 JWT의 `company_app`과 `X-Company-App`이 다르면 차단한다.

## 천하운수 전환 전략

천하운수는 실제 사용 중이므로 바로 옮기지 않는다.

### 1단계: shadow schema 생성

- `tenant_cheonha` schema를 만든다.
- public에 있는 운영 테이블 구조를 tenant schema에 만든다.
- 아직 서비스 트래픽은 public을 본다.

### 2단계: 1차 데이터 복사

public의 천하운수 데이터만 `tenant_cheonha`로 복사한다.

대상 예:

- `accounts_user` 중 `company_app='cheonha'`
- `accounts_team` 중 `company_app='cheonha'`
- `crew_crewmember` 중 천하운수 team 참조
- `dispatch_dispatchupload` 중 천하운수 team 참조
- `settlement_settlement` 중 천하운수 team 참조
- 관련 detail, inquiry, tracking, points

이 단계도 서비스 트래픽은 계속 public을 본다.

### 3단계: 검증

다음 값이 public과 tenant에서 같아야 한다.

- 팀 수
- 배송원 수
- 최근 30일 배차 업로드 수
- 최근 30일 정산 수
- 최근 30일 정산 상세 수
- 운영현황 핵심 숫자
- 정산관리 금액
- 앱 정산 조회 결과

### 4단계: 짧은 write freeze 또는 최종 delta sync

천하운수는 계속 사용 중이므로 1차 복사 후에도 public에 새 데이터가 들어올 수 있다.

가장 안전한 방식:

1. 아주 짧은 점검 시간을 잡는다.
2. 배차 업로드/정산 생성/배송원 수정 같은 쓰기 기능을 잠깐 막는다.
3. public에서 tenant로 최종 delta를 복사한다.
4. 검증 쿼리를 다시 실행한다.
5. `cheonha` routing flag를 tenant schema로 켠다.
6. 즉시 smoke test를 실행한다.

대체 방식:

- dual write를 구현해 public과 tenant에 동시에 쓰는 기간을 둔다.
- 더 복잡하므로 현재 시스템에는 우선 권장하지 않는다.

### 5단계: 전환

- `TENANT_SCHEMA_ROUTING_ENABLED=True`
- `TENANT_SCHEMA_COMPANIES=cheonha,new,...`
- `cheonha -> tenant_cheonha`

전환 후에도 public의 천하운수 데이터는 바로 삭제하지 않는다.

### 6단계: 안정화 후 보관

- 최소 1개월 이상 public 원본 데이터를 보관한다.
- tenant 결과가 안정화되면 public의 천하운수 운영 테이블은 read-only archive로 남기거나 별도 백업 후 정리한다.

## 새 회사 흐름

새 회사는 처음부터 tenant schema를 사용한다.

1. 회사 신청
2. CLEVER 승인
3. `tenant_<company_code>` schema 생성
4. tenant schema migrate
5. tenant schema에 대표 관리자 user 생성
6. 기본 Team/화주사 설정 seed
7. 회사 상태 `ACTIVE`
8. 이후 로그인과 모든 운영 API는 tenant schema 사용

## 구현 단계

### Phase 0. 비파괴 준비

- 문서 추가
- preflight 스크립트 추가
- 운영 동작 변경 없음

### Phase 1. tenant registry 모델 추가

새 중앙 모델 예:

- `CompanyTenant`
  - `company_app`
  - `schema_name`
  - `status`
  - `routing_enabled`
  - `created_at`
  - `last_migrated_at`
  - `last_verified_at`

아직 라우팅은 켜지 않는다.

현재 구현 상태:

- `accounts.CompanyTenant` 모델과 admin 등록을 추가한다.
- 기존 회사에는 `tenant_<company_code>` row를 `PLANNED`, `routing_enabled=False`로 seed한다.
- 이 단계는 요청 라우팅, 로그인, `search_path`를 전혀 변경하지 않는다.

### Phase 2. schema 생성/마이그레이션 명령 추가

명령 후보:

```bash
python manage.py create_tenant_schema cheonha
python manage.py create_tenant_schema cheonha --apply
python manage.py migrate_tenant_schema cheonha
```

주의:

- public schema에는 영향 없어야 한다.
- 실패해도 기존 서비스는 그대로 동작해야 한다.

현재 구현 상태:

- `python manage.py create_tenant_schema <company_code>` 명령을 추가한다.
- 기본 실행은 dry-run이며 DB를 변경하지 않는다.
- 실제 schema 생성은 `--apply`를 붙일 때만 실행된다.
- 이 명령은 schema 생성 계획만 담당한다.
- table migration, 데이터 복사, routing enable은 아직 하지 않는다.
- 운영에는 빈 schema `tenant_cheonha`, `tenant_new`까지만 생성되어 있으며, 둘 다 테이블은 없고 routing은 꺼져 있다.

### Phase 2-1. tenant migration plan 명령 추가

명령:

```bash
python manage.py migrate_tenant_schema cheonha
python manage.py migrate_tenant_schema new
```

현재 구현 상태:

- 기본 동작은 read-only plan이다.
- pending migration 목록과 앱별 개수를 출력한다.
- table 생성, data copy, routing enable은 하지 않는다.
- `--apply`는 안전을 위해 아직 거부한다.
- `field_manager`, `vehicle_management`는 hard-coded schema 때문에 제외 대상으로 표시한다.

### Phase 2-2. tenant table inventory 명령 추가

명령:

```bash
python manage.py plan_tenant_tables cheonha
python manage.py plan_tenant_tables new
```

현재 구현 상태:

- 기본 동작은 read-only inventory이다.
- 모델별로 tenant schema에 필요한 table, public table 존재 여부, tenant table 존재 여부를 출력한다.
- row count는 큰 테이블에서 느릴 수 있으므로 기본값에서는 조회하지 않는다.
- 필요할 때만 `--with-counts`를 붙여 public row count를 확인한다.
- `accounts.CompanyApp`, `accounts.CompanyTenant`, `accounts.Shipper`는 central-only 모델로 보고 public에 남긴다.
- `accounts.User`는 dual 모델로 보고 tenant에도 별도 table이 필요하다고 표시한다.
- migrations가 없는 앱은 syncdb/schema-editor 전략이 필요하다고 따로 표시한다.
- table 생성, data copy, migration 기록 작성, routing enable은 하지 않는다.

### Phase 2-3. tenant table creation readiness 명령 추가

명령:

```bash
python manage.py plan_tenant_table_creation cheonha
python manage.py plan_tenant_table_creation new
```

현재 구현 상태:

- 기본 동작은 read-only readiness plan이다.
- tenant schema에 아직 없는 concrete model table을 대상으로 생성 순서를 계산한다.
- FK와 M2M 의존성을 따라 위상 정렬을 수행한다.
- 순환 의존성이 있으면 `creation_readiness: BLOCKED`로 표시하고, 어떤 모델들이 서로 막고 있는지 출력한다.
- 순환 의존성이 nullable FK로 풀릴 수 있으면 `Nullable FK split plan`에 어떤 FK를 초기 생성에서 미루고 나중에 추가할지 표시한다.
- 현재 운영 DB 기준으로 `accounts.User.team`을 뒤로 미루면 `accounts.Team`과의 순환 의존성을 풀 수 있다.
- auto-created many-to-many table은 어떤 owner model이 생성하는지도 표시한다.
- migrations가 없는 앱은 syncdb/schema-editor 처리 대상으로 따로 표시한다.
- `--show-sql`은 blocker가 없을 때만 허용한다. blocker가 있으면 불완전한 SQL을 보여주지 않기 위해 거부한다.
- table 생성, data copy, migration 기록 작성, routing enable은 하지 않는다.

### Phase 2-4. tenant table creation dry-run 명령 추가

명령:

```bash
python manage.py create_tenant_tables cheonha
python manage.py create_tenant_tables new
python manage.py create_tenant_tables new --apply
```

현재 구현 상태:

- 기본 실행은 operation plan만 출력한다.
- `--apply`는 비핵심 회사이면서 tenant schema가 비어 있는 경우에만 허용한다.
- 천하운수 같은 core company에는 이 단계에서 `--apply`를 거부한다.
- schema가 비어 있지 않으면 idempotency 검토 전까지 `--apply`를 거부한다.
- Phase 1에는 concrete model table 생성 순서를 출력한다.
- Phase 1a에는 `create_model` 과정에서 생성될 auto-created M2M table을 출력한다.
- Phase 2에는 초기 생성에서 미룬 nullable FK를 나중에 추가하는 순서를 출력한다.
- Phase 3에는 table 생성 직후 데이터 복사 전에 해야 하는 검증 항목을 출력한다.
- `--apply` 실행 시에도 data copy, migration 기록 작성, routing enable은 하지 않는다.
- `--apply`는 PostgreSQL transaction 안에서 실행한다. 실패하면 전체 table creation을 rollback한다.
- `accounts.User.team`은 초기 `accounts_user` 생성에서 제외하고, 모든 대상 table이 만들어진 뒤 `ALTER TABLE`로 추가한다.

### Phase 2-5. tenant table verification 명령 추가

명령:

```bash
python manage.py verify_tenant_tables new
python manage.py verify_tenant_tables cheonha --allow-incomplete
```

현재 구현 상태:

- read-only 검증 명령이다.
- tenant schema의 table, column, FK, unique constraint, 기본 index coverage를 모델 기준으로 비교한다.
- 오류가 있으면 기본적으로 실패한다.
- 아직 비어 있거나 전환 전인 schema는 `--allow-incomplete`로 오류를 출력만 하게 할 수 있다.
- table 생성, data copy, migration 기록 작성, routing enable은 하지 않는다.

### Phase 2-6. tenant base seed dry-run/apply 명령 추가

명령:

```bash
python manage.py seed_tenant_base_data new
python manage.py seed_tenant_base_data new --apply
```

현재 구현 상태:

- 기본 실행은 read-only seed plan이다.
- `--apply` is now available only for non-core companies with an existing empty tenant table set.
- `--apply` is refused for core companies such as `cheonha`.
- `--apply` is refused when any reference seed table already contains rows.
- The apply step inserts only base reference data and company-local login/team rows.
- The apply step does not copy dispatch, settlement, crew, region, tracking, inquiry, or other operational data.
- The apply step does not enable tenant routing.
- 대상 seed 후보:
  - `django_content_type`
  - `auth_permission`
  - `auth_group`
  - `auth_group_permissions`
  - 회사별 `accounts_user`
  - 회사별 `accounts_team`
  - `accounts_user_groups`
  - `accounts_user_user_permissions`
  - `mobile_app_message_config`
  - `points_point_items`
- 배차/정산/배송원/권역/추적 같은 운영 데이터는 이 단계에서 제외한다.
- 향후 apply에서는 content type, permission, user, team primary key를 public source와 동일하게 보존해야 한다.
- public에 아직 없는 content type은 tenant seed 시 새로 생성하고, 해당 모델의 기본 permission도 함께 생성하는 전략으로 간다.
- data insert, table 생성, migration 기록 작성, routing enable은 하지 않는다.

### Phase 3. 천하운수 데이터 복사 명령 추가

명령 후보:

```bash
python manage.py copy_company_to_tenant_schema cheonha --dry-run
python manage.py copy_company_to_tenant_schema cheonha
```

처음에는 dry-run과 count 비교만 만든다.

현재 구현 상태:

- `copy_company_to_tenant_schema <company_code>`는 dry-run으로 복사 계획을 출력한다.
- `--apply`는 non-core 회사에서만 허용한다.
- `--apply`는 base seed가 끝났고 운영 target table이 비어 있는 경우에만 허용한다.
- `--apply`는 PostgreSQL transaction 안에서 실행하며 실패 시 전체 copy를 rollback한다.
- `--apply`는 감사용 user FK(`created_by`, `uploaded_by`, `confirmed_by` 등)가 tenant user에 없으면 `NULL`로 보정한다.
- `public` 원본 row 수와 tenant schema의 기존 row 수만 센다.
- `seed_tenant_base_data`가 처리한 기준 테이블은 별도로 표시한다.
- 운영 데이터 테이블은 회사/조/배송원/업로드/정산 FK 기준으로만 집계한다.
- 회사 구분 기준이 없는 `manpower_manpower`는 별도 정책 확정 전까지 blocked로 표시한다.
- 이 명령은 routing 변경을 하지 않는다.

### Phase 4. read-only 비교 API/명령 추가

명령 후보:

```bash
python manage.py verify_tenant_schema cheonha
python manage.py verify_company_tenant_copy new
python manage.py verify_company_tenant_copy cheonha --allow-incomplete
```

비교 항목:

- row count
- FK 누락
- 최근 기간 운영현황 숫자
- 최근 기간 정산 합계

현재 구현 상태:

- `verify_company_tenant_copy <company_code>`를 추가했다.
- read-only 명령이며 DB를 변경하지 않는다.
- base seed 핵심 테이블과 운영 copy 정책 테이블을 source/tenant 기준으로 비교한다.
- 운영 copy 테이블은 row count, id min/max/sum, 주요 숫자 합계를 비교한다.
- 주요 숫자 합계:
  - `dispatch_dispatchrecord`: boxes, households, original_boxes
  - `settlement_settlement`: total_receive, total_pay, total_overtime, total_other_cost, total_profit
  - `settlement_settlementdetail`: boxes, receive_amount, pay_amount, overtime_cost, other_cost, profit
- 아직 준비되지 않은 schema는 `--allow-incomplete`로 오류를 출력만 하게 할 수 있다.

### Phase 5. 비활성 middleware/router 추가

- 기본값은 off다.
- off 상태에서 기존 smoke가 완전히 통과해야 한다.

```env
TENANT_SCHEMA_ROUTING_ENABLED=False
TENANT_SCHEMA_COMPANIES=
```

현재 구현 상태:

- `TenantSchemaRoutingMiddleware`를 추가했다.
- 기본값은 `TENANT_SCHEMA_ROUTING_ENABLED=False`라서 요청 동작을 바꾸지 않는다.
- 라우팅이 켜져도 `TENANT_SCHEMA_COMPANIES` allow-list와 `CompanyTenant.routing_enabled=True`가 모두 맞아야 tenant schema로 간다.
- `CompanyTenant.status`는 `READY` 또는 `ACTIVE`일 때만 라우팅 후보가 된다.
- 중앙 관리/문서/clever-login 경로는 tenant routing에서 제외한다.
- request 종료 후 PostgreSQL `search_path`를 `public`으로 되돌린다.
- 현재 운영 배포는 routing off 상태로만 검증한다.

### Phase 6. 테스트 회사부터 routing on

- 천하운수 전에 테스트 회사로 검증한다.
- 성공해도 천하운수는 바로 켜지 않는다.

### Phase 7. 천하운수 전환

- 짧은 write freeze
- 최종 delta sync
- verify
- flag on
- smoke
- 로그 확인

## 롤백

천하운수 전환 후 문제가 생기면:

1. `TENANT_SCHEMA_COMPANIES`에서 `cheonha` 제거
2. backend 재시작 또는 설정 reload
3. 즉시 public 테이블 기준으로 복귀
4. tenant schema는 보관하고 원인 분석

이 롤백이 가능하려면 public 천하운수 원본 데이터를 전환 직후에도 삭제하면 안 된다.

## 중단 기준

아래 중 하나라도 발생하면 다음 단계로 진행하지 않는다.

- public과 tenant row count 불일치
- 정산 금액 불일치
- 운영현황 숫자 불일치
- 앱에서 JSON parse 오류 발생
- 회사 간 데이터가 섞여 보임
- tenant routing off 상태에서도 기존 smoke가 실패
- `search_path` 원복 실패 가능성이 발견됨
- hard-coded schema 모델을 tenant 대상에 포함해야 하는데 처리 방침이 확정되지 않음

## 다음 작은 작업

1. preflight 스크립트를 실행해 모델 분류와 위험 FK를 확인한다.
2. `CompanyTenant` 모델 설계를 확정한다.
3. tenant schema 생성 명령을 dry-run으로만 만든다.
4. 그 다음에야 실제 schema 생성으로 넘어간다.
