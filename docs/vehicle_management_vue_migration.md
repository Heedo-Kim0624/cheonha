# 차량관리 Vue/API 분리 이관 메모

## 목표

운영 통합관리의 차량관리 화면을 정적 HTML 하위 사이트가 아니라 기존 시스템과 같은 구조로 관리한다.

- 프론트엔드: Vue 라우터, Vue 화면, 재사용 컴포넌트
- 백엔드: Django REST API
- 도메인 격리: `backend/apps/vehicle_management`
- 기존 데이터 보존: 기존 `vehicle_mgmt` 스키마와 `fleet_*` 테이블을 그대로 사용
- 기존 기능 보존: 정적 `/fleet-management/` 화면은 완전 이관 전까지 fallback으로 유지

## 현재 구조

```text
운영 통합관리
  └─ /portal/vehicle/*
       └─ frontend/src/views/FleetManagementView.vue
            ├─ frontend/src/api/fleetManagement.js
            ├─ frontend/src/components/fleet/FleetVehicleTable.vue
            └─ frontend/src/components/fleet/FleetSimpleTable.vue

백엔드
  └─ /api/v1/vehicle/*
       └─ backend/apps/vehicle_management
```

## 화면 경로

| 경로 | Vue 화면 | 설명 |
|---|---|---|
| `/portal/vehicle/dashboard` | `FleetManagementView.vue` | 대시보드 |
| `/portal/vehicle/vehicles` | `FleetManagementView.vue` | 차량 목록 |
| `/portal/vehicle/subscriptions` | `FleetManagementView.vue` | 구독 전자계약 |
| `/portal/vehicle/returns` | `FleetManagementView.vue` | 반납/수리비 |
| `/portal/vehicle/insurance` | `FleetManagementView.vue` | 보험 |
| `/portal/vehicle/accidents` | `FleetManagementView.vue` | 사고 관리 |
| `/portal/vehicle/upload` | `FleetManagementView.vue` | 업로드/양식 다운로드 |

## API 경계

| 기능 | API |
|---|---|
| 통합 차량관리 조회 | `GET /api/v1/vehicle/fleet-site/` |
| 대폐차 등록 | `POST /api/v1/vehicle/fleet-site/replacement/` |
| 차량 생성 | `POST /api/v1/vehicle/vehicles/fleet-create/` |
| 차량 정보 수정 | `PATCH /api/v1/vehicle/vehicles/{id}/fleet-info/` |
| 차량 상태 수정 | `PATCH /api/v1/vehicle/vehicles/{id}/status/` |
| 차량 삭제 | `DELETE /api/v1/vehicle/vehicles/{id}/fleet-delete/` |
| 차량 이력 수정 | `PATCH /api/v1/vehicle/fleet-records/{id}/` |
| 차량 이력 상태 수정 | `PATCH /api/v1/vehicle/fleet-records/{id}/status/` |
| 차량 서류 | `/api/v1/vehicle/fleet-documents/` |
| 구독 계약 | `/api/v1/vehicle/fleet-subscriptions/` |
| 반납/수리비 | `/api/v1/vehicle/fleet-returns/` |
| 반납 사진 업로드 | `POST /api/v1/vehicle/fleet-returns/{id}/photos/` |
| 보험 | `/api/v1/vehicle/fleet-insurances/` |
| 사고 | `/api/v1/vehicle/fleet-accidents/` |
| 사고 이력 통합 업로드 | `POST /api/v1/vehicle/fleet-accidents/upload-history/` |
| 사고 이력 업로드 양식 | `GET /api/v1/vehicle/fleet-accidents/upload-template/` |

## GitHub 선별 대상

차량관리 이관을 GitHub에서 재현하려면 아래 파일들이 필요하다.

### 백엔드

- `backend/apps/vehicle_management/**`
- `backend/config/settings.py`
  - `apps.vehicle_management.apps.VehicleManagementConfig` 등록 필요
- `backend/config/urls.py`
  - `path('api/v1/vehicle/', include('apps.vehicle_management.urls'))` 필요
- `backend/requirements.txt`
  - `pandas`, `xlrd`, `openpyxl` 등 차량관리 엑셀 처리 의존성 필요

제외:

- `backend/apps/vehicle_management/**/__pycache__/**`
- `backend/apps/vehicle_management/**/*.pyc`

### 프론트엔드

- `frontend/src/api/fleetManagement.js`
- `frontend/src/views/FleetManagementView.vue`
- `frontend/src/components/fleet/FleetVehicleTable.vue`
- `frontend/src/components/fleet/FleetSimpleTable.vue`
- `frontend/src/router/index.js`
- `frontend/src/views/CleverPortalAdminView.vue`
- `frontend/src/components/portal/VehicleManagementPanel.vue`

주의:

- `frontend/src/router/index.js`는 회사별 라우팅, 포털 라우팅 등 이전 변경도 함께 섞여 있다. 차량관리만 커밋하려면 라우터 diff를 별도 검토해야 한다.
- `CleverPortalAdminView.vue`도 포털 전반 의존성이 있으므로 이 파일만 올리면 관련 `components/portal`, `components/operations`, `api/companyAdmin`, `api/mobileAdmin`, `api/points`, `api/tracking`, `utils/companyApp` 등이 추가로 필요할 수 있다.

## 검증

현재 로컬 검증 결과:

- `frontend`: `npm run build` 성공
- `backend`: `DEBUG=True python manage.py check` 성공

잔여 경고:

- 프론트 CSS minify 경고 `Expected identifier but found "-"`는 기존 전역 CSS에서 발생하며 이번 차량관리 분리 작업의 신규 오류는 아니다.
- Django `staticfiles.W004`는 `backend/static` 폴더 부재 경고다.

## 남은 이관 작업

정적 HTML fallback을 완전히 제거하려면 다음 기능을 Vue로 추가 이관해야 한다.

- 차량 생성/수정/삭제 모달
- 자동차등록증, 보험청약서, 구독계약서, 반납사진 미리보기/교체/다운로드
- 반납 접수, 수리비 청구, 보험 등록/삭제, 사고 보상금 수기 입력
- 월별 구독료 산정/엑셀 다운로드
- 대시보드 카드 클릭 결과 목록
- 엑셀 업로드 드래그앤드롭 및 업로드 결과 표시
