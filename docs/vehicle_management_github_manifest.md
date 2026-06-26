# 차량관리 Vue/API 이관 GitHub 반영 매니페스트

## 목적

운영 통합관리의 차량관리 기능을 정적 HTML 하위 사이트가 아니라 기존 시스템과 같은 구조로 관리한다.

- 프론트엔드: Vue 라우트, Vue 화면, 재사용 컴포넌트, API 클라이언트
- 백엔드: Django REST API, `apps.vehicle_management` 도메인 앱
- 데이터: 기존 `vehicle_mgmt` 스키마와 `fleet_*` 테이블 유지
- 정적 HTML: `/fleet-management/`는 임시 fallback 및 기능 참고용으로만 유지

## GitHub에 포함해야 하는 차량관리 핵심 파일

### 백엔드 신규 앱

아래 전체를 포함한다.

```text
backend/apps/vehicle_management/
```

포함 대상:

- `admin.py`
- `apps.py`
- `holiday_utils.py`
- `models.py`
- `serializers.py`
- `urls.py`
- `views.py`
- `services/evdash_service.py`
- `management/commands/check_evdash.py`
- `management/commands/import_vehicles_xlsx.py`
- `migrations/*.py`

제외 대상:

- `__pycache__/`
- `*.pyc`

### 백엔드 연결 파일

선별 hunk만 포함한다.

```text
backend/config/settings.py
backend/config/urls.py
backend/requirements.txt
```

필요한 변경:

- `INSTALLED_APPS`에 `apps.vehicle_management.apps.VehicleManagementConfig` 추가
- URL에 `path('api/v1/vehicle/', include('apps.vehicle_management.urls'))` 추가
- 엑셀 처리 의존성 유지: `pandas`, `xlrd`, `openpyxl`

주의:

- 현재 작업트리의 `settings.py`, `urls.py`, `requirements.txt`에는 ONE, 포인트, 추적, 인력풀 등 다른 기능 변경도 섞여 있다.
- 차량관리만 올릴 때는 `git add -p` 또는 별도 클린 브랜치에서 차량관리 hunk만 적용해야 한다.

### 프론트엔드 차량관리 Vue 파일

아래 파일을 포함한다.

```text
frontend/src/api/fleetManagement.js
frontend/src/views/FleetManagementView.vue
frontend/src/components/fleet/FleetVehicleTable.vue
frontend/src/components/fleet/FleetSimpleTable.vue
frontend/src/composables/useFleetSite.js
```

역할:

- `fleetManagement.js`: `/api/v1/vehicle/*` 전용 클라이언트
- `FleetManagementView.vue`: 차량관리 최상위 Vue 화면
- `FleetVehicleTable.vue`: 차량번호 기준 차량 그룹 테이블
- `FleetSimpleTable.vue`: 구독, 반납, 보험, 사고 공통 테이블
- `useFleetSite.js`: 회사 선택, 차량 데이터 로딩, 에러/로딩 상태 분리

### 프론트엔드 라우팅 및 포털 연결

선별 또는 동반 포함이 필요하다.

```text
frontend/src/router/index.js
frontend/src/views/CleverPortalAdminView.vue
frontend/src/components/portal/VehicleManagementPanel.vue
frontend/src/api/vehicle.js
```

필요한 라우트:

```text
/portal/vehicle/dashboard
/portal/vehicle/vehicles
/portal/vehicle/subscriptions
/portal/vehicle/returns
/portal/vehicle/insurance
/portal/vehicle/accidents
/portal/vehicle/upload
```

주의:

- `router/index.js`는 회사별 라우팅 개편과 포털 라우팅 변경이 같이 섞여 있다.
- `CleverPortalAdminView.vue`는 포털 전체 화면 의존성이 많다.
- 클린 브랜치에서 차량관리만 반영할 경우, 포털 전체 변경을 그대로 가져올지, `/portal/vehicle/*` 라우트만 최소 반영할지 먼저 결정해야 한다.

### 문서

아래 문서를 함께 올린다.

```text
docs/vehicle_management_erd.md
docs/vehicle_management_vue_migration.md
docs/vehicle_management_github_manifest.md
```

## 현재 검증 명령

프론트엔드:

```powershell
cd frontend
npm run build
```

백엔드:

```powershell
cd backend
$env:DEBUG='True'
python manage.py check
```

## 안전한 GitHub 반영 절차

현재 `main` 작업트리에는 차량관리 외 작업이 많이 섞여 있으므로 아래 중 하나로 진행한다.

### 권장: 클린 브랜치에서 재적용

1. 현재 작업을 보존한다.
2. `main` 기준 새 브랜치를 만든다.
3. 위 매니페스트 파일만 복사한다.
4. `settings.py`, `urls.py`, `requirements.txt`, `router/index.js`는 필요한 hunk만 수동 적용한다.
5. 빌드와 Django check를 통과시킨다.
6. `vehicle-management-vue-api` 같은 별도 브랜치로 push한다.

### 차선: 현재 작업트리에서 선별 staging

1. `git add -p`로 설정/라우터 hunk를 직접 고른다.
2. `git status --short`로 스테이징 범위를 확인한다.
3. `git diff --cached --name-only`가 차량관리 관련 파일만 가리키는지 확인한다.
4. 빌드와 Django check를 통과시킨 뒤 커밋한다.

## 남은 작업

- 정적 `fleet_management_fixed.html`에 있는 모든 모달/업로드/미리보기 동작을 Vue 컴포넌트로 세분화해야 한다.
- 현재 Vue 화면은 차량관리 read-model과 핵심 테이블/상태 변경 중심이다.
- 완전한 기능 이관을 위해 문서, 구독 계약, 반납 사진, 보험, 사고 보상, 월별 청구 엑셀 기능을 세부 컴포넌트로 분리해야 한다.
