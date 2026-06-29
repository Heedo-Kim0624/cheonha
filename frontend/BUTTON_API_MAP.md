# 천하운수 시스템 — 화면별 버튼 ↔ API 매핑 (전체)

> **목적**: 웹 포털과 모든 모바일 앱에서 어떤 버튼/액션이 어떤 백엔드 API를 호출하고 어떤 결과가 발생하는지 한 문서로 추적할 수 있도록 정리.
> **기준일**: 2026-04-30
> **백엔드 베이스 URL**: `http://43.201.160.163/api/v1` (운영) / `http://13.124.120.147/api/v1` (스테이징) / `http://localhost:8000/api/v1` (개발)

---

## 0. 시스템 구성 요약

| 구분 | 이름 | 기술 | 베이스 경로 | 주 사용자 |
|------|------|------|-------------|-----------|
| 웹 (관리자) | **CLEVER 포털 + 천하 ERP** | Vue 3 + Vite + Pinia | `/`, `/cheonha/*`, `/portal/*` | 본사 관리자, 슈퍼관리자 |
| 모바일 앱 | **천하 정산 앱** (`cheonha-settlement-app`) | React Native (Expo) | `/api/v1/mobile/*` | 배송기사 |
| 모바일 앱 | **현장관리자 앱** (`field-manager-app`) | React Native (Expo) | `/api/v1/field-manager/*` | 영업소 / 현장관리자 |
| 모바일 앱 | **비콘 근태관리 앱** (`beacon-app`) | React Native | (로컬 BLE 스캔 + AsyncStorage 저장) | 작업자 |
| 안드로이드 네이티브 | **기압계 앱** (`barometer-app`) | Java/Kotlin | (로컬) | 테스트용 |

### 백엔드 API 라우트 트리 (`config/urls.py`)

```
/api/v1/admin/                  Django Admin
/api/v1/schema/                 OpenAPI 스키마
/api/v1/docs/                   Swagger UI

/api/v1/auth/                   웹 로그인/회원가입 (apps.accounts.auth_urls)
/api/v1/accounts/               유저/조 관리 (apps.accounts.urls)
/api/v1/dispatch/               배차표 업로드/정산 (apps.dispatch.urls)
/api/v1/region/                 권역/단가 (apps.region.urls)
/api/v1/settlement/             정산 결과 (apps.settlement.urls)
/api/v1/crew/                   배송원 (apps.crew.urls)
/api/v1/partner/                협력사 (apps.partner.urls)
/api/v1/dashboard/              대시보드 KPI (apps.dashboard.urls)

/api/v1/mobile/                 기사용 모바일 앱 (apps.mobile.urls)
/api/v1/inquiry/                정산 문의 (apps.inquiry.urls)
/api/v1/tracking/               배송 추적 (apps.tracking.urls)
/api/v1/points/                 포인트 (apps.points.urls)
/api/v1/manpower/               인력풀 (apps.manpower.urls)
/api/v1/territory/              권역(폴리곤) (apps.territory.urls)
/api/v1/vehicle/                차량관리 (apps.vehicle_management.urls)
/api/v1/field-manager/          현장관리자 앱 (apps.field_manager.urls)
```

---

# Part A. 웹 포털

## A1. CLEVER 포털 진입 (비로그인 / `/` · `/portal/*`)

라우트: `CleverPortalAdminView.vue` (탭: `operations | work | points | vehicle`)

### A1-1. 탭 네비게이션

| 위치 | 버튼 | 동작 | 호출되는 API |
|------|------|------|--------------|
| 상단 메뉴 | **운영현황 / 운행현황 / 포인트 / 차량관리** 탭 | `router.push('/portal/...')` | (없음, 라우터 전환) |
| 상단 우측 | **로그아웃** | `authStore.logout()` → `/cheonha/login` 이동 | `POST /auth/logout/` |
| 좌측 조 필터 | "전체" 클릭 | `selectTeam('')` | (탭 전환에 따라 다음 API들 호출) |
| 좌측 조 필터 | 특정 조 클릭 | `selectTeam(teamId)` | 동상 |

탭이 바뀌거나 조 필터가 바뀌면 `loadInitialData()` → `loadCommonData() + loadTabData()` 가 실행되어 다음 API들이 호출됩니다:

- `GET /accounts/teams/` — 조 목록
- (탭이 `operations`) `GET /dashboard/dashboard/kpi`, `GET /dashboard/dashboard/revenue_by_region`, `GET /dashboard/dashboard/settlement_summary`
- (탭이 `work/live`) `GET /tracking/live-status/?team_id=...`
- (탭이 `work/csv`) `GET /tracking/usage-overview/?team_id=...&date_from=...&date_to=...`
- (탭이 `points/summary`) `GET /points/summaries/?team_id=...`
- (탭이 `points/shop`) `GET /points/items/`
- (탭이 `vehicle`) `GET /vehicle/companies/`, `GET /vehicle/vehicles/`, `GET /vehicle/pit-records/`, `GET /vehicle/calendar/`, `GET /vehicle/subscriptions/`, `GET /vehicle/returns/`, `GET /vehicle/as-requests/`

### A1-2. 운행현황(Live) 서브탭

| 버튼 | 동작 | API |
|------|------|-----|
| **새로고침** | `refreshCurrentView({force:true})` | `GET /tracking/live-status/?team_id=...` |
| **운행추적 새로고침** | `loadTrackingOverview()` | `GET /tracking/usage-overview/` |
| 세션 행 **CSV 다운로드** | `downloadSessionCsv(session)` | `GET /tracking/sessions/{id}/download_csv/` (blob) |

### A1-3. 포인트 — Summary 서브탭

| 버튼 | 동작 | API |
|------|------|-----|
| **포인트 조회** | `loadPoints()` | `GET /points/summaries/?team_id=...` |
| 행별 **승인** | `confirmRedemption(redemptionId)` | `POST /points/redemptions/{id}/confirm/` |
| 행별 **잔액 저장** | `savePointBalance(row)` | `POST /points/crew/{crewId}/set-balance/` |

### A1-4. 포인트 — Shop 서브탭

| 버튼 | 동작 | API |
|------|------|-----|
| **상품 등록 / 수정** | `submitPointItem()` | `POST /points/items/` (신규) 또는 `PATCH /points/items/{id}/` (수정) |
| **초기화** | `resetPointItemForm()` | (로컬) |
| 상품 행 **수정** | `startEditPointItem(item)` | (폼 채우기) |
| 상품 행 **삭제** | `removePointItem(item)` | `DELETE /points/items/{id}/` |

### A1-5. 차량관리 탭 (4개 서브탭)

차량 / 피트 / 캘린더 / 구독 / A/S 의 기본 CRUD는 `cheonha/frontend/src/api/vehicle.js` 에 모두 정의되어 있습니다. 각 서브탭 화면에서 사용되는 액션:

| 서브탭 | 버튼 | API |
|--------|------|-----|
| status | 등록/수정/삭제 | `POST/PATCH/DELETE /vehicle/vehicles/{id?}/` |
| status | 통계 새로고침 | `GET /vehicle/vehicles/stats/` |
| pit | 등록/수정/삭제 | `POST/PATCH/DELETE /vehicle/pit-records/{id?}/` |
| calendar | 일정 추가/수정/삭제 | `POST/PATCH/DELETE /vehicle/calendar/{id?}/` |
| subscription | **차량 배정** | `POST /vehicle/subscriptions/{id}/assign/` `{vehicle_ids}` |
| subscription | **완료** | `POST /vehicle/subscriptions/{id}/complete/` |
| as | **확인** | `POST /vehicle/returns/{id}/confirm/` 또는 `POST /vehicle/as-requests/{id}/complete/` |
| return | **조정** | `POST /vehicle/returns/{id}/adjust/` |

---

## A2. 천하 ERP 로그인 (`/cheonha/login`)

`LoginView.vue` — 로그인 / 회원가입 토글.

| 폼 | 버튼 | 동작 | API |
|----|------|------|-----|
| `mode === 'login'` | **로그인** | `handleLogin()` → `authStore.login(email,password)` | `POST /auth/login/` `{email,password}` |
| `mode === 'signup'` | **회원가입** | `handleSignup()` | `POST /accounts/signup/` `{name, email, password, team_id, ...}` |
| 회원가입 진입 시 | (자동) | `loadTeams()` | `GET /accounts/teams/` |
| 토큰 만료 후 첫 호출 | (자동) | client interceptor 401 → `authStore.logout()` → `/cheonha/login` 이동 | (없음) |

> **구현**: `frontend/src/api/auth.js` 에 `login`, `cleverLogin`, `logout`, `refreshToken`, `getProfile` 정의. 클라이언트 헤더 `Authorization: Bearer <token>` 자동 부착, 응답 401 자동 로그아웃.

---

## A3. 대시보드 (`/cheonha/dashboard`)

`HomeView.vue`. 페이지 진입 시 `loadDashboard()` 가 실행되며, 기간 프리셋 변경 시 `applyRangePreset()` 이 같은 API를 다시 호출합니다.

| 버튼 | 동작 | API |
|------|------|-----|
| 페이지 진입 | `loadDashboard()` | `GET /dashboard/dashboard/kpi` ＋ `GET /dashboard/dashboard/revenue_by_region` ＋ `GET /dashboard/dashboard/settlement_summary` |
| 기간 프리셋 (오늘/7일/30일/...) | `applyRangePreset(value)` | 동상 (params 포함) |

---

## A4. 배송원 관리 (`/cheonha/crew`)

`CrewView.vue`. 정규/용차 탭 분리.

### A4-1. 정규 탭

| 버튼 | 동작 | API |
|------|------|-----|
| 페이지 진입 | `fetchCrew()` | `GET /crew/members?status=regular` |
| 행 **수정** | `editCrew(member)` → `submitEditCrew()` | `PATCH /crew/members/{id}` |
| 행 **용차 전환** | `convertRegularToYongcha(member)` | `POST /crew/members/{id}/convert_to_yongcha` |
| 행 **삭제** | `deleteCrew(member)` | `DELETE /crew/members/{id}` |
| 페이지 네비게이션 | (페이지 변수만) | (재호출 없음, 클라이언트 페이지네이션) |

### A4-2. 용차 탭

| 버튼 | 동작 | API |
|------|------|-----|
| 탭 전환 | `activeTab='yongcha'` → `fetchYongchaSummary()` | `GET /crew/members/yongcha_summary` |
| 카드 클릭 | `selectYongcha(member)` → 일별 내역 | `GET /crew/members/{id}/yongcha_daily` |
| **용차 → 정규 전환** | `convertYongcha(member)` | `POST /crew/members/{id}/convert_to_regular` |
| **삭제** | `deleteYongcha(member)` | `DELETE /crew/members/{id}` |

### A4-3. 신규 등록 대기

`getNewMembers()` → `GET /crew/members/new_members`,
`markRegistered(id)` → `POST /crew/members/{id}/mark_registered`.
정산내역 팝업: `GET /crew/members/{id}/settlement_history`.

---

## A5. 배차 업로드 / 정산 확정 (`/cheonha/dispatch`)

`DispatchView.vue` — 4단계 마법사.

### A5-1. 1단계 — 파일 업로드

| 버튼 | 동작 | API |
|------|------|-----|
| **파일 선택** (input) | `onFileSelected()` → `uploadDispatchFile(file)` | `POST /dispatch/uploads` (multipart, `file`) |
| 페이지 진입 시 목록 | `fetchUploads()` | `GET /dispatch/uploads` |
| 업로드 행 **이어서** | `resumeUpload(upload)` | (로컬 + 다음 호출) `GET /dispatch/uploads/{id}/detected_info` |
| 업로드 행 **원본 다운로드** | `downloadUploadFile(upload)` | `GET /dispatch/uploads/{id}/download-file` (blob) |
| 업로드 행 **삭제** | `deleteUpload(upload)` | (DELETE 미정의 — Codex 리뷰에서 별개 이슈 가능) |

### A5-2. 2단계 — 권역/배송원 매핑

| 버튼 | 동작 | API |
|------|------|-----|
| 자동 진입 | `loadDetected()` | `GET /dispatch/uploads/{uploadId}/detected_info` |
| **다음** | `handleNextStep()` → `configureAll(uploadId, payload)` | `POST /dispatch/uploads/{id}/configure` |

### A5-3. 3단계 — 박스/특근 조정

| 버튼 | 동작 | API |
|------|------|-----|
| 박스수 변경 저장 | `updateBoxes(uploadId, records)` | `POST /dispatch/uploads/{id}/update_boxes` `{records}` |
| 특근 토글 저장 | `setOvertime(uploadId, crew)` | `POST /dispatch/uploads/{id}/set_overtime` `{crew}` |
| 레코드 새로고침 | `getRecords(uploadId)` | `GET /dispatch/records?upload_id=...&limit=500` |

### A5-4. 4단계 — 정산 확정

| 버튼 | 동작 | API |
|------|------|-----|
| **확정** | `handleFinalize()` → `finalizeUpload(uploadId, payload)` | `POST /dispatch/uploads/{id}/finalize` |
| **여러 업로드 일괄확정** | `handleBatchFinalize()` | 각 업로드에 대해 `POST .../finalize` 반복 |
| **재시작** | `resetUpload()` | (로컬 상태 초기화) |
| 운영현황 보고서 | (Operations 화면 사용) | `GET /dispatch/uploads/operation-report?date=...` |
| 운영현황 CSV | (Operations 화면 사용) | `GET /dispatch/uploads/operation-report-csv` (blob) |
| 데이터 전체 초기화 (관리) | `resetAllData()` | `POST /dispatch/uploads/reset_data` |

---

## A6. 정산 (`/cheonha/settlement`)

`SettlementView.vue`. 캘린더 + 일별 정산서 + 기타 비용.

| 버튼 | 동작 | API |
|------|------|-----|
| 페이지 진입 | `fetchSettlements()` | `GET /settlement/settlements?...` |
| 일자 셀 클릭 | `selectDate(date)` | (필터 적용 + 위 호출 재실행) |
| 정산 카드 클릭 | `toggleDetail(id)` → `getSettlementDetails(id)` | `GET /settlement/details?settlement_id={id}` |
| 정산서 다운로드 | `exportSettlement(id)` | `GET /settlement/settlements/{id}/export` (blob) |
| 배송원 셀 **상세팝업** | `openCrewPopup(crew, ug)` | `GET /crew/members/{id}/settlement_history` |
| **기타 비용** 추가 | `openOtherCostModal()` → `saveOtherCost()` | `POST /settlement/settlements` (`other_cost` payload) |

---

## A7. 권역/단가 (`/cheonha/region`)

`RegionView.vue`.

| 버튼 | 동작 | API |
|------|------|-----|
| 페이지 진입 | `fetchRegions()`, `fetchTeams()` | `GET /region`, `GET /region/teams` |
| **+ 새 조** | `showCreateModal=true` → `createTeam()` | `POST /region/teams` |
| 조 행 저장 | `saveTeam(team)` | `PUT /region/teams/{id}` |
| 조 행 **삭제** | `deleteTeam(team)` | `DELETE /region/teams/{id}` |
| 사용자 **승인** | `approveUser(id)` | `POST /accounts/users/{id}/approve/` |
| 사용자 **거절** | `rejectUser(id)` | `POST /accounts/users/{id}/reject/` |
| 사용자 **삭제** | `deleteUser(u)` | `DELETE /accounts/users/{id}/` |
| 단가 수정 (지역별) | `updatePrice(regionId, payload)` | `PUT /region/{id}/price` |
| 일괄 단가 업로드 | `bulkUpdatePrices(list)` | `POST /region/bulk-prices` |
| 단가 템플릿 다운로드 | `downloadPriceTemplate()` | `GET /region/template/prices` (blob) |

---

## A8. 정산 문의 (`/cheonha/inquiry`)

`InquiryView.vue`.

| 버튼 | 동작 | API |
|------|------|-----|
| 상태 필터 (전체/대기/응답/읽음) | `statusFilter=k; loadList()` | `GET /inquiry/inquiries/?status=...` |
| 행 클릭 (상세) | `openDetail(iq)` → `getInquiry(id)` | `GET /inquiry/inquiries/{id}/` |
| **저장 (조정금액 등)** | `saveInquiry()` | `PATCH /inquiry/inquiries/{id}/` |
| **답글 보내기** | `sendMessage()` | `POST /inquiry/inquiries/{id}/messages/` `{content, author_type:'admin'}` |
| **읽음 처리** | `markRead()` | `POST /inquiry/inquiries/{id}/mark_read/` |
| 페이지 진입 시 카운터 | (자동) | `GET /inquiry/inquiries/counts/` |

---

## A9. 배송 추적 (`/cheonha/tracking`)

`TrackingView.vue`. 지도 기반.

| 버튼 | 동작 | API |
|------|------|-----|
| 조 변경 | `onTeamChange(id)` | `GET /territory/territories/?team_id=...` |
| 권역 카드 클릭 | `selectTerritory(t)` | `GET /territory/territories/{id}/box_series/` |
| **+ 박스 추가** | `openBoxEditor()` → `saveBoxEditor()` | `POST /territory/territories/{id}/box_set/` |
| **인근 인력 풀** | `loadNearbyManpower()` | `GET /territory/territories/{id}/nearby_manpower/?radius_m=...` |
| 사이클 카드 클릭 | `onCycleCardClick(c)` | (지도 줌) `GET /territory/territories/{id}/cycles_inside/` |
| 권역 그리기 토글 | `toggleDraw()` | (지도 모드) |
| 그린 폴리곤 **저장** | `savePendingPolygon()` | `POST /territory/territories/` `{name, polygon}` |
| 폴리곤 **삭제** | `removeTerritory()` | `DELETE /territory/territories/{id}/` |
| 추적 히스토리 클릭 | `onTerritoryHistoryClick(h)` | `GET /tracking/sessions/{id}/`, `GET /tracking/sessions/{id}/points/`, `GET /tracking/sessions/{id}/cycles/`, `GET /tracking/sessions/{id}/captures/` |
| **CSV 다운로드** (히스토리 행) | `downloadHistoryCsv(h)` | `GET /tracking/sessions/{id}/download_csv/` (blob) |
| 사용 가능 일자 조회 | (자동) | `GET /tracking/sessions/available_dates/` |

---

## A10. 인력풀 (`/cheonha/manpower`)

`ManpowerView.vue` (간단 화면 + 새로고침).

| 버튼 | 동작 | API |
|------|------|-----|
| **새로고침** | `reload()` | `GET /manpower/people/sheet/` |
| (다른 화면 통합) 시트 동기화 | `syncManpowerSheet(url)` | `POST /manpower/people/sync_sheet/` `{url}` |
| 엑셀 import | `importManpowerXlsx(file)` | `POST /manpower/people/import_xlsx/` (multipart) |
| 추가/수정/삭제 | `createManpower / updateManpower / deleteManpower` | `POST/PATCH/DELETE /manpower/people/{id?}/` |
| 좌표 보정 (단건/일괄) | `geocodeManpower / geocodeAllManpower` | `POST /manpower/people/{id}/geocode/` 또는 `POST /manpower/people/geocode_all/` |
| 인근 검색 | `nearbyManpower(lat, lon, r)` | `GET /manpower/people/nearby/?lat=&lon=&radius_m=` |

---

## A11. 권역(폴리곤) 관리 (`/cheonha/territory` → `/cheonha/tracking` 으로 redirect)

`TerritoryView.vue` 는 현재 redirect 으로 비활성. 위 A9에 통합.

기능:
- `listTerritories()` `GET /territory/territories/`
- `importTerritoryGeoJSON(file)` `POST /territory/territories/import_geojson/`
- `createTerritory / updateTerritory / deleteTerritory`

---

## A12. 운영현황 (`/cheonha/operations`)

`OperationsView.vue` (12 lines, wrapper). 내부에서 dispatch.js의 `fetchOperationReport`, `downloadOperationReportCsv` 호출.

| 버튼 | API |
|------|-----|
| 일자/조 필터 → 조회 | `GET /dispatch/uploads/operation-report?date=...&team_id=...` |
| **CSV 다운로드** | `GET /dispatch/uploads/operation-report-csv?...` (blob) |

---

# Part B. 모바일 앱 — `cheonha-settlement-app` (천하 정산 앱 / 기사용)

## B1. 로그인 (`LoginScreen.tsx`)

| 입력/버튼 | 동작 | API |
|-----------|------|-----|
| 이름 + 조 코드 + 비밀번호 → **로그인** | `api.login(name, teamCode, password)` | `POST /api/v1/mobile/login/` `{name, team_code, password}` |
| **개인정보처리방침** | `openPrivacyPolicy()` | (외부 브라우저로 `${API}/privacy`) |

응답에 `requires_password_change`가 포함되며, 이후 캘린더 화면에서 모달로 비밀번호 변경을 강제합니다.

토큰 만료 자동 처리: `request()` 내부에서 401 ↔ `refreshAccessToken()` → `POST /api/v1/mobile/refresh/` `{refresh}`.

## B2. 캘린더 메인 (`CalendarScreen.tsx`)

진입 시 호출되는 API:
- `api.getProfile()` → `GET /api/v1/mobile/profile/`
- `api.getSettlements(month)` → `GET /api/v1/mobile/settlements/?month=YYYY-MM`
- `api.getPoints()` → `GET /api/v1/mobile/points/`

### B2-1. 헤더 / 도구 영역

| 버튼 | 동작 | API |
|------|------|-----|
| ◀ ▶ (월 이동) | `setMonth/setYear` | `GET /api/v1/mobile/settlements/?month=...` |
| **로그아웃** | `clearTokens()` → `Login` 화면 | (서버 호출 없음, 로컬 토큰만 삭제) |
| **비밀번호 변경** | 모달 → `handleChangePassword()` | `POST /api/v1/mobile/password/` `{password, password_confirm, vehicle_number?}` |
| **차량번호 변경** | 모달 → `handleSaveVehicleNumber()` | `POST /api/v1/mobile/vehicle-number/` `{vehicle_number}` |
| **급여계좌 변경** | 모달 → `handleSavePayrollAccount()` | `POST /api/v1/mobile/payroll-account/` `{bank_name, bank_account_number}` |
| **검사일자 등록** | 모달 → `handleSaveVehicleInspectionDate()` | `POST /api/v1/mobile/vehicle-inspection-date/` `{vehicle_inspection_date}` |

### B2-2. 캘린더 셀 / 정산 문의

| 동작 | API |
|------|-----|
| 일자 셀 클릭 | `openInquiry(date)` → `api.getSettlementInquiry(date)` → `GET /api/v1/mobile/settlement-inquiry/?date=...` |
| 문의 모달 **등록** | `api.commentSettlementInquiry(date, content)` → `POST /api/v1/mobile/settlement-inquiry/comment/` `{date, content}` |
| (자동) 모달 진입 후 30초 내 | `api.markSettlementInquiryRead(inquiryId)` → `POST /api/v1/mobile/settlement-inquiry/read/` `{inquiry_id}` |

### B2-3. 근무 세션 (네이티브 모듈 + 서버 양쪽)

| 버튼 | 동작 | 서버 API | 네이티브 동작 |
|------|------|----------|--------------|
| **근무 시작** (`workStartButton`) | `handleStartSession()` | `POST /api/v1/mobile/work-session/start/` `{vehicle_number, background_location_granted}` | `WorkSessionModule.startSessionWithSignalCheck(name, vehicle, 2000)` — BLE/GPS 수집 시작 |
| (백그라운드) 약 5분 간격 | `handleHeartbeat()` (CalendarScreen 449줄) | `POST /api/v1/mobile/work-session/heartbeat/` | (없음 — 서버에 살아있음 통보) |
| **근무 종료** | `handleStopSession()` (1) 정지 (2) 업로드 | `POST /api/v1/mobile/work-session/stop/` 후 `POST /api/v1/mobile/work-session/upload/` `{csv_content, file_name, vehicle_number}` | `WorkSessionModule.stopSession()` — CSV 산출 |
| 응답 처리 | `point_awarded` 시 알림 + 포인트 새로고침 | `GET /api/v1/mobile/points/` | (없음) |

> **Codex 리뷰 P2**: `mobile/views.py:694-709` 에서 `/work-session/upload/` 가 `WORK_REWARD` 트랜잭션을 *비동기 처리 완료 전에* 적립함. 비동기 실패 시 포인트만 살아남음. (백엔드 측 이슈, 프론트는 그대로)

### B2-4. 포인트 교환

| 버튼 | 동작 | API |
|------|------|-----|
| **포인트 교환** 카드 | `openPointExchange()` (모달) | `GET /api/v1/mobile/points/` |
| **새로고침** (모달 안) | `onRefresh()` | `GET /api/v1/mobile/points/` |
| 상품 **교환하기** | `onRedeem(item)` → `api.redeemPoints(item.key)` | `POST /api/v1/mobile/points/redeem/` `{item_key}` |

---

# Part C. 모바일 앱 — `field-manager-app` (현장관리자 앱)

## C1. 로그인 (`LoginScreen.tsx`)

| 입력/버튼 | 동작 | API |
|-----------|------|-----|
| 회사 선택 (`YUHAN / CHEONHA / PERSONAL`) | `setCompanyCode(c.code)` | (없음) |
| 조 코드 + 전화번호 + PIN → **로그인** | `api.login(companyCode, teamCode, phone, pin)` | `POST /api/v1/field-manager/login/` `{company_code, team_code, phone, pin}` |

응답: `{ token, identity }` → `saveSession()` 으로 SecureStore 저장.

## C2. 메인 (`MainScreen.tsx`)

| 버튼 | 동작 | API |
|------|------|-----|
| **차량 구독** 카드 | `nav.navigate('SubscriptionMenu')` | (없음) |
| **A/S 신청** 카드 | `nav.navigate('ASRequest')` | (없음) |
| **로그아웃** | `clearSession()` → `Login` | (없음) |

## C3. 구독 메뉴 (`SubscriptionMenuScreen.tsx`)

| 버튼 | 동작 | API |
|------|------|-----|
| **신규 신청** | `nav.navigate('SubscriptionRequest')` | (없음) |
| **반납 신청** | `nav.navigate('SubscriptionReturn')` | (없음) |

## C4. 구독 신청 (`SubscriptionRequestScreen.tsx`)

| 버튼 | 동작 | API |
|------|------|-----|
| 수량 +/− | `setQty(...)` | (없음) |
| **신청하기** | `submit()` → `api.createSubscriptionRequest({...})` | `POST /api/v1/field-manager/subscription-requests/` `{company_code, team_code, phone, requested_date, quantity}` |

## C5. 구독 반납 (`SubscriptionReturnScreen.tsx`)

| 버튼/이벤트 | 동작 | API |
|-------------|------|-----|
| 화면 진입 | `loadBlockedDates()` | `GET /api/v1/field-manager/blocked-dates/?company_code=...` |
| 시간 선택 | `setTime(h)` | (없음) |
| **반납 신청** | `submit()` → `api.createReturnRequest({...})` | `POST /api/v1/field-manager/return-requests/` `{company_code, team_code, phone, vehicle_number, reason, hope_date, hope_time}` |

## C6. A/S 신청 (`ASRequestScreen.tsx`)

| 버튼 | 동작 | API |
|------|------|-----|
| **신청하기** | `submit()` → `api.createASRequest({...})` | `POST /api/v1/field-manager/as-requests/` `{company_code, team_code, phone, vehicle_number, owner_name, owner_phone, reason}` |

> **Codex 리뷰 P1 (보안)**: 백엔드 `field_manager/views.py:97-103` 핸들러가 인증 토큰의 `auth.company_code/team_code/phone` 대신 *body의 같은 필드*를 신뢰함. 즉, 로그인한 토큰으로도 *다른 회사/조* 의 구독·반납·A/S·blocked-dates 요청을 만들 수 있음. 같은 패턴이 위 4개 핸들러 전체에 반복. 프론트 측 보호 없음 — 백엔드 수정 필요.

---

# Part D. 모바일 앱 — `beacon-app` (비콘 근태)

서버 통신이 없는 로컬 전용 앱. AsyncStorage(`beacon_account` key) 에만 저장.

## D1. 로그인 (`LoginScreen.js`)

| 버튼 | 동작 | API |
|------|------|-----|
| **근무 화면으로** | `handleSubmit()` → `AsyncStorage.setItem(...)` → `Work` | (없음) |

저장 형식: `{ name, accountId, beaconId }`. 검증 정규식:
- `accountId`: `/^[A-Za-z0-9_-]{1,30}$/`
- `beaconId`: `/^[A-Za-z0-9가-힣ㄱ-ㅎㅏ-ㅣ\s_-]{1,30}$/`

## D2. 근무 화면 (`WorkScreen.js`)

| 버튼 | 동작 | API |
|------|------|-----|
| **근무 시작** | `handleStartWork()` — BLE 스캔 시작 | (없음) |
| **근무 종료** | `handleStopWork()` — 스캔 중지 + 로그 보존 | (없음) |
| **CSV 내보내기** | `doExportCSV()` | (없음, 로컬 파일 시스템) |
| **초기화** | `handleReset()` | (없음, AsyncStorage 클리어) |

> 이 앱은 백엔드와 통신하지 않습니다. 추후 서버 연동을 추가한다면 별도 엔드포인트가 필요합니다.

---

# Part E. 안드로이드 — `barometer-app` (기압계)

`AndroidManifest.xml + src` 의 네이티브 앱. 외부 API 호출 없음 (센서 → 화면 표시만). 본 문서 범위 외.

---

# Part F. 백엔드 엔드포인트 종합 (Cross-reference)

> 모든 엔드포인트는 `/api/v1` 접두사. 인증은 별도 표기되지 않으면 `Authorization: Bearer <JWT>` 가 필요.

## F1. 인증 (`/auth/`)
| Method | Path | View | 클라이언트 |
|--------|------|------|------------|
| POST | `/auth/login/` | `auth_views.LoginView` | 웹 LoginView |
| POST | `/auth/clever-login/` | `auth_views.CleverLoginView` | (예약) |
| POST | `/auth/refresh/` | `auth_views.RefreshTokenView` | 웹 |
| GET  | `/auth/profile/` | `auth_views.ProfileView` | 웹 |
| POST | `/auth/logout/` | `auth_views.LogoutView` | 웹 |
| POST | `/auth/signup/` | `auth_views.SignupView` | 웹 LoginView (signup) |

## F2. 유저/조 (`/accounts/`)
| Method | Path | 클라이언트 |
|--------|------|-----------|
| GET/POST/PATCH/DELETE | `/accounts/users/{id?}/` | RegionView / 웹 |
| POST | `/accounts/users/{id}/approve/` | RegionView |
| POST | `/accounts/users/{id}/reject/` | RegionView |
| GET/POST/PATCH/DELETE | `/accounts/teams/{id?}/` | LoginView, CleverPortalAdminView |
| POST | `/accounts/signup/` | LoginView |
| POST | `/accounts/token/`, `/accounts/token/refresh/` | (legacy SimpleJWT) |

## F3. 배차/정산/배송원/조 (`/dispatch /settlement /crew /partner /region /dashboard`)

위 A 섹션 참조. 모든 ViewSet 라우트는 router 자동 생성 (`list / retrieve / create / update / partial_update / destroy + custom @action`).

## F4. 모바일 (`/mobile/`)
| Method | Path | 호출처 |
|--------|------|-------|
| POST | `/mobile/register/` | (등록 절차) |
| POST | `/mobile/login/` | settlement-app LoginScreen |
| POST | `/mobile/refresh/` | settlement-app api 자동 |
| POST | `/mobile/password/` | CalendarScreen 비밀번호 모달 |
| POST | `/mobile/vehicle-number/` | CalendarScreen 차량번호 모달 |
| POST | `/mobile/payroll-account/` | CalendarScreen 급여계좌 모달 |
| POST | `/mobile/vehicle-inspection-date/` | CalendarScreen 검사일자 모달 |
| GET  | `/mobile/status/` | (헬스체크) |
| GET  | `/mobile/profile/` | CalendarScreen 진입 |
| POST | `/mobile/work-session/start/` | 근무 시작 |
| POST | `/mobile/work-session/heartbeat/` | 주기 호출 |
| POST | `/mobile/work-session/stop/` | 근무 종료 |
| POST | `/mobile/work-session/upload/` | CSV 업로드 |
| GET  | `/mobile/points/` | 포인트 조회 |
| POST | `/mobile/points/redeem/` | 포인트 교환 |
| GET  | `/mobile/settlements/?month=...` | 정산 캘린더 |
| GET  | `/mobile/settlement-inquiry/?date=...` | 정산 문의 상세 |
| POST | `/mobile/settlement-inquiry/comment/` | 문의 메시지 |
| POST | `/mobile/settlement-inquiry/read/` | 문의 읽음 |
| GET  | `/mobile/admin/approvals/` | (관리자) |
| POST | `/mobile/admin/approvals/{pk}/` | (관리자) |
| GET/POST | `/mobile/admin/users/{pk?}/` | (관리자) |

## F5. 현장관리자 (`/field-manager/`)
| Method | Path | 호출처 |
|--------|------|-------|
| POST | `/field-manager/login/` | LoginScreen |
| POST | `/field-manager/subscription-requests/` | SubscriptionRequestScreen |
| POST | `/field-manager/return-requests/` | SubscriptionReturnScreen |
| POST | `/field-manager/as-requests/` | ASRequestScreen |
| GET  | `/field-manager/blocked-dates/?company_code=...` | SubscriptionReturnScreen |

## F6. 추적 (`/tracking/`)
| Method | Path | 호출처 |
|--------|------|-------|
| GET  | `/tracking/live-status/` | CleverPortal Live 탭 |
| GET  | `/tracking/usage-overview/` | CleverPortal 운행추적 |
| GET  | `/tracking/sessions/` | (목록) |
| GET  | `/tracking/sessions/{id}/` | TrackingView 상세 |
| GET  | `/tracking/sessions/{id}/points/` | TrackingView |
| GET  | `/tracking/sessions/{id}/captures/` | TrackingView |
| GET  | `/tracking/sessions/{id}/cycles/` | TrackingView |
| GET  | `/tracking/sessions/{id}/download_csv/` | CleverPortal/TrackingView CSV 다운로드 |
| GET  | `/tracking/sessions/available_dates/` | (선택 가능 일자) |
| DELETE | `/tracking/sessions/{id}/` | TrackingView |
| DELETE | `/tracking/sessions/bulk_delete/` | (관리) |

## F7. 포인트 (`/points/`)
| Method | Path | 호출처 |
|--------|------|-------|
| GET/POST | `/points/items/` | CleverPortal Shop |
| PATCH/DELETE | `/points/items/{id}/` | CleverPortal Shop |
| GET | `/points/summaries/?team_id=...` | CleverPortal Summary |
| GET | `/points/crew/{id}/` | (상세) |
| POST | `/points/crew/{id}/set-balance/` | CleverPortal 잔액수정 |
| POST | `/points/redemptions/{id}/confirm/` | CleverPortal 승인 |
| POST | `/points/redemptions/{id}/cancel/` | (취소) |

## F8. 차량관리 (`/vehicle/`)

`vehicle.js` ↔ router 자동 생성 (`companies / vehicles / pit-records / calendar / subscriptions / returns / as-requests`) + 커스텀 액션:
- `POST /vehicle/vehicles/stats/` (실제로는 GET, `@action(detail=False, methods=['GET'])`)
- `POST /vehicle/subscriptions/{id}/assign/`
- `POST /vehicle/subscriptions/{id}/complete/`
- `POST /vehicle/returns/{id}/confirm/`
- `POST /vehicle/returns/{id}/adjust/`
- `POST /vehicle/as-requests/{id}/complete/`

## F9. 정산 문의 (`/inquiry/`)
| Method | Path | 호출처 |
|--------|------|-------|
| GET  | `/inquiry/inquiries/` | 웹 InquiryView |
| GET  | `/inquiry/inquiries/{id}/` | 웹 InquiryView |
| PATCH | `/inquiry/inquiries/{id}/` | 웹 (조정금액 저장) |
| POST | `/inquiry/inquiries/{id}/messages/` | 웹 (답글) |
| POST | `/inquiry/inquiries/{id}/mark_read/` | 웹 |
| GET  | `/inquiry/inquiries/counts/` | 웹 |

## F10. 권역(폴리곤) / 인력풀
- `/territory/territories/...` (CRUD + box_set / box_series / cycles_inside / nearby_manpower / import_geojson)
- `/manpower/people/...` (CRUD + sheet, sync_sheet, import_xlsx, geocode, geocode_all, nearby)

---

# Part G. 권한 / 인증 흐름 요약

| 클라이언트 | 토큰 발급 | 헤더 | 만료 처리 |
|-----------|-----------|------|----------|
| 웹 (Pinia) | `POST /auth/login/` | `Authorization: Bearer <token>` (`api/client.js`) | 401 ⇒ `authStore.logout()` + `/cheonha/login` 리다이렉트 |
| settlement-app | `POST /mobile/login/` (`access`+`refresh`) | `Authorization: Bearer <access>` | 401 ⇒ `POST /mobile/refresh/` 자동 → 재시도, 실패 시 토큰 삭제 |
| field-manager-app | `POST /field-manager/login/` | `Authorization: Bearer <token>` | (refresh 없음 — 재로그인) |
| beacon-app | (없음) | (없음) | (없음) |

---

# Part H. 비고 / 알려진 이슈

1. **Codex 리뷰 P1 — field-manager 인증 우회**: 5개 핸들러(login 제외) 전부 body의 `company_code/team_code/phone` 을 신뢰. 토큰의 identity와 비교 / 또는 토큰에서 직접 도출 필요. 위치: `cheonha/backend/apps/field_manager/views.py:97-103`.
2. **Codex 리뷰 P2 — 포인트 적립 타이밍**: `POST /mobile/work-session/upload/` 가 비동기 트래킹 import 완료 전에 `WORK_REWARD` 적립. 위치: `cheonha/backend/apps/mobile/views.py:694-709`.
3. **Codex 리뷰 P3 — kalman_filter.py 문법 오류**: `cheonha/ALGORITHM/kalman_filter.py:6` `output_file='` 미종결 → import 자체 불가능.
4. **DispatchView 삭제**: `deleteUpload` 핸들러는 있으나 `dispatch.js` 에 대응 함수가 없음 → 호출 시점 확인 필요.
5. **TerritoryView 라우트는 redirect** 상태이고, 실제 폴리곤 관리 UI는 `TrackingView` 내부에 통합됨.

---

# Part I. 향후 보강 제안

- Swagger UI (`/api/v1/docs/`) 와 본 문서를 **링크**로 묶고, 새 엔드포인트 추가 시 본 표 + Swagger 동시 업데이트.
- 화면별 테스트 시나리오 (Playwright `e2e/` 와 1:1) 를 표 옆에 컬럼으로 추가.
- 백엔드 `views.py` 에서 각 엔드포인트가 사용하는 **DB 테이블 / 모델** 도 매핑 (현재는 URL 단위까지만).

— 끝 —
