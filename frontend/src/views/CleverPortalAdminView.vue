<template>
  <div class="min-h-screen bg-slate-50 text-slate-900">
    <header class="border-b border-slate-200 bg-white">
      <div class="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <div class="flex items-center gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-900 text-sm font-bold text-white">
            CL
          </div>
          <div>
            <h1 class="text-xl font-bold">CLEVER</h1>
            <p class="text-xs text-slate-500">운영 통합 관리</p>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <RouterLink
            v-if="isCleverAdminSession"
            :to="companyLink"
            class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          >
            {{ selectedCompanyName }} 페이지
          </RouterLink>
          <button
            v-if="authStore.isAuthenticated"
            type="button"
            class="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
            @click="logout"
          >
            로그아웃
          </button>
        </div>
      </div>
    </header>

    <main class="mx-auto max-w-7xl px-6 py-8">
      <section v-if="!isCleverAdminSession" class="mx-auto w-full max-w-md">
        <form class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm" @submit.prevent="login">
          <h2 class="text-xl font-bold">관리자 로그인</h2>
          <p class="mt-1 text-sm text-slate-500">CLEVER 운영 통합 관리 계정으로 로그인하세요.</p>

          <div
            v-if="authStore.isAuthenticated && !isCleverAdminSession"
            class="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800"
          >
            현재 계정은 운영 통합 관리 권한이 없습니다. 통합 관리자 계정으로 다시 로그인하세요.
          </div>

          <label class="mt-6 block">
            <span class="mb-2 block text-sm font-semibold text-slate-600">아이디</span>
            <input
              v-model="loginId"
              type="text"
              required
              class="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-lime-500"
            />
          </label>

          <label class="mt-4 block">
            <span class="mb-2 block text-sm font-semibold text-slate-600">비밀번호</span>
            <input
              v-model="loginPassword"
              type="password"
              required
              class="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-lime-500"
            />
          </label>

          <div v-if="loginError" class="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {{ loginError }}
          </div>

          <button
            type="submit"
            :disabled="loginLoading"
            class="mt-5 w-full rounded-lg bg-lime-500 px-4 py-3 font-bold text-slate-900 hover:bg-lime-400 disabled:opacity-50"
          >
            {{ loginLoading ? '로그인 중...' : '로그인' }}
          </button>
        </form>
      </section>

      <section v-else class="portal-layout">
        <aside class="portal-sidebar">
          <div class="sidebar-head">
            <span class="sidebar-mark">CL</span>
            <div>
              <p class="sidebar-kicker">CLEVER</p>
              <h2 class="text-lg font-bold text-slate-900">통합 관리</h2>
            </div>
          </div>

          <nav class="sidebar-nav" aria-label="통합 관리 메뉴">
            <RouterLink
              :to="{ name: 'CleverPortal' }"
              class="sidebar-tab"
              :class="{ active: activeTab === 'operations' }"
            >
              <span>운영현황</span>
              <small>날짜별 운영 지표</small>
            </RouterLink>
            <RouterLink
              :to="{ name: 'CleverPortalRevenue' }"
              class="sidebar-tab"
              :class="{ active: activeTab === 'revenue' }"
            >
              <span>매출 현황</span>
              <small>업체별 월별·일별 매출</small>
            </RouterLink>
            <RouterLink
              :to="{ name: 'CleverPortalWorkLive' }"
              class="sidebar-tab"
              :class="{ active: activeTab === 'work' }"
            >
              <span>근무기록</span>
              <small>실시간 근무와 CSV</small>
            </RouterLink>
            <RouterLink
              :to="{ name: 'CleverPortalPointsSummary' }"
              class="sidebar-tab"
              :class="{ active: activeTab === 'points' }"
            >
              <span>포인트</span>
              <small>요약과 상점 설정</small>
            </RouterLink>
            <RouterLink
              :to="{ name: 'CleverPortalAppMessages' }"
              class="sidebar-tab"
              :class="{ active: activeTab === 'app' }"
            >
              <span>앱 관리</span>
              <small>팝업과 안내 문구</small>
            </RouterLink>
            <RouterLink
              :to="{ name: 'CleverPortalVehicleDashboard' }"
              class="sidebar-tab"
              :class="{ active: activeTab === 'vehicle' }"
            >
              <span>차량관리</span>
              <small>차량관리 전용 사이트</small>
            </RouterLink>
            <RouterLink
              :to="{ name: 'CleverPortalPitStatus' }"
              class="sidebar-tab"
              :class="{ active: activeTab === 'pit' }"
            >
              <span>피트</span>
              <small>피트 현황, 배정, A/S</small>
            </RouterLink>
            <RouterLink
              :to="{ name: 'CleverPortalCompanies' }"
              class="sidebar-tab"
              :class="{ active: activeTab === 'companies' }"
            >
              <span>회사 관리</span>
              <small>회사 추가, 승인, 탭 설정</small>
            </RouterLink>
          </nav>
        </aside>

        <section class="portal-content">
          <header class="portal-topbar">
            <div>
              <p class="portal-kicker">{{ selectedCompanyName }}</p>
              <h2 class="text-2xl font-bold text-slate-900">{{ activeTitle }}</h2>
              <p class="portal-desc">{{ activeDescription }}</p>
            </div>

            <label class="portal-company">
              <span>회사</span>
              <select v-model="selectedCompany">
                <option v-for="company in companies" :key="company.code" :value="company.code">
                  {{ company.name }}
                </option>
              </select>
            </label>
          </header>

          <section v-if="activeTab === 'companies'" class="space-y-5">
            <CompanyManagementPanel @updated="applyCompanyList" />
          </section>

          <section v-else-if="activeTab === 'operations'" class="space-y-5 min-w-0 overflow-x-hidden">
            <div class="team-button-panel">
              <span class="team-button-label">조 선택</span>
              <div class="team-buttons">
                <button type="button" :class="{ active: selectedTeamId === '' }" @click="selectTeam('')">전체</button>
                <button
                  v-for="team in teams"
                  :key="team.id"
                  type="button"
                  :class="{ active: selectedTeamId === String(team.id) }"
                  @click="selectTeam(String(team.id))"
                >
                  {{ team.name }}
                </button>
              </div>
            </div>

            <OperationReportPanel
              :key="`operations-${selectedCompany}`"
              :company-name="selectedCompanyName"
              :company-code="selectedCompany"
              :team-name="selectedTeamName"
              :show-company-select="false"
              :show-team-filter="false"
            />
          </section>

          <section v-else-if="activeTab === 'revenue'" class="space-y-5 min-w-0 overflow-x-hidden">
            <RevenueStatusPanel :key="`revenue-${selectedCompany}`" :company-code="selectedCompany" />
          </section>

          <section v-else-if="activeTab === 'work'" class="space-y-5">
            <div class="subtab-bar">
              <RouterLink
                :to="{ name: 'CleverPortalWorkLive' }"
                class="subtab-pill"
                :class="{ active: activeSubtab === 'live' }"
              >
                실시간 근무 현황
              </RouterLink>
              <RouterLink
                :to="{ name: 'CleverPortalWorkCsv' }"
                class="subtab-pill"
                :class="{ active: activeSubtab === 'csv' }"
              >
                근무기록 CSV
              </RouterLink>
              <RouterLink
                :to="{ name: 'CleverPortalWorkLegalConsents' }"
                class="subtab-pill"
                :class="{ active: activeSubtab === 'legal-consents' }"
              >
                약관 버전 동의 이력
              </RouterLink>
            </div>

            <div class="team-button-panel">
              <span class="team-button-label">조 선택</span>
              <div class="team-buttons">
                <button type="button" :class="{ active: selectedTeamId === '' }" @click="selectTeam('')">전체</button>
                <button
                  v-for="team in teams"
                  :key="team.id"
                  type="button"
                  :class="{ active: selectedTeamId === String(team.id) }"
                  @click="selectTeam(String(team.id))"
                >
                  {{ team.name }}
                </button>
              </div>
              <button type="button" class="refresh-button" :disabled="workRefreshing" @click="refreshCurrentView()">
                새로고침
              </button>
            </div>

            <template v-if="activeSubtab === 'live'">
              <div class="stat-grid">
                <div class="stat-card">
                  <span>등록 기사</span>
                  <strong>{{ formatNumber(liveSummary.crew_count) }}명</strong>
                </div>
                <div class="stat-card">
                  <span>근무 중</span>
                  <strong>{{ formatNumber(liveSummary.working_count) }}명</strong>
                </div>
                <div class="stat-card">
                  <span>위치 권한 정상</span>
                  <strong>{{ formatNumber(liveSummary.background_location_ok_count) }}명</strong>
                </div>
              </div>

              <div v-if="workLoading && liveRows.length === 0" class="empty-state">로딩 중...</div>
              <div v-else-if="liveRows.length === 0" class="empty-state">실시간 근무 데이터가 없습니다.</div>
              <div v-else class="overflow-x-auto rounded-xl border border-slate-200 bg-white">
                <table class="w-full min-w-[1080px] text-sm">
                  <thead class="border-b border-slate-200 bg-slate-50">
                    <tr>
                      <th class="table-th">조</th>
                      <th class="table-th">기사</th>
                      <th class="table-th">차량</th>
                      <th class="table-th">앱 버전</th>
                      <th class="table-th">근무 상태</th>
                      <th class="table-th">권한</th>
                      <th class="table-th">근무 시작</th>
                      <th class="table-th">마지막 신호</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="row in liveRows" :key="row.id" class="border-b border-slate-100">
                      <td class="table-td">{{ row.team_name || '-' }}</td>
                      <td class="table-td font-semibold">
                        <button
                          type="button"
                          class="font-bold text-slate-900 underline-offset-4 hover:text-lime-700 hover:underline"
                          @click="openPointDetail(row)"
                        >
                          {{ row.name }}
                        </button>
                      </td>
                      <td class="table-td">{{ row.vehicle_number || '-' }}</td>
                      <td class="table-td">{{ row.app_version || '-' }}</td>
                      <td class="table-td">
                        <span
                          class="inline-flex items-center gap-2 text-xs font-semibold"
                          :class="row.is_working ? 'text-emerald-600' : 'text-slate-500'"
                        >
                          <span class="status-dot" :class="{ working: row.is_working }"></span>
                          {{ row.is_working ? '근무 중' : '대기' }}
                        </span>
                      </td>
                      <td class="table-td">{{ row.background_location_granted ? '정상 허용' : '확인 필요' }}</td>
                      <td class="table-td">{{ formatDateTime(row.session_started_at) }}</td>
                      <td class="table-td">{{ formatDateTime(row.last_seen_at) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </template>

            <template v-else-if="activeSubtab === 'csv'">
              <div class="toolbar-card">
                <label>
                  <span>시작일</span>
                  <input v-model="usageStartDate" type="date" />
                </label>
                <label>
                  <span>종료일</span>
                  <input v-model="usageEndDate" type="date" />
                </label>
                <button type="button" :disabled="workRefreshing" @click="loadTrackingOverview()">조회</button>
              </div>

              <div class="stat-grid">
                <div class="stat-card">
                  <span>기사 수</span>
                  <strong>{{ formatNumber(trackingSummary.crew_count) }}명</strong>
                </div>
                <div class="stat-card">
                  <span>앱 계정 수</span>
                  <strong>{{ formatNumber(trackingSummary.mobile_account_count) }}명</strong>
                </div>
                <div class="stat-card">
                  <span>수집 가능</span>
                  <strong>{{ formatNumber(trackingSummary.data_ready_count) }}명</strong>
                </div>
                <div class="stat-card">
                  <span>CSV 건수</span>
                  <strong>{{ formatNumber(trackingSummary.session_count) }}건</strong>
                </div>
              </div>

              <div v-if="workLoading && trackingSessions.length === 0" class="empty-state">로딩 중...</div>
              <div v-else-if="trackingSessions.length === 0" class="empty-state">근무기록 CSV가 없습니다.</div>
              <div v-else class="overflow-x-auto rounded-xl border border-slate-200 bg-white">
                <table class="w-full min-w-[1200px] text-sm">
                  <thead class="border-b border-slate-200 bg-slate-50">
                    <tr>
                      <th class="table-th">근무일</th>
                      <th class="table-th">조</th>
                      <th class="table-th">기사</th>
                      <th class="table-th">차량</th>
                      <th class="table-th">앱 버전</th>
                      <th class="table-th text-right">이동거리</th>
                      <th class="table-th text-right">사이클</th>
                      <th class="table-th text-right">촬영</th>
                      <th class="table-th">RSSI</th>
                      <th class="table-th">업로드 시각</th>
                      <th class="table-th text-center">CSV</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="session in trackingSessions" :key="session.id" class="border-b border-slate-100">
                      <td class="table-td font-semibold">{{ session.session_date }}</td>
                      <td class="table-td">{{ session.team_name || '-' }}</td>
                      <td class="table-td">{{ session.crew_name || '-' }}</td>
                      <td class="table-td">{{ session.vehicle_number || '-' }}</td>
                      <td class="table-td">{{ session.app_version || '-' }}</td>
                      <td class="table-td text-right">{{ formatKm(session.distance_m) }}</td>
                      <td class="table-td text-right">{{ formatNumber(session.cycle_count) }}</td>
                      <td class="table-td text-right">{{ formatNumber(session.capture_count) }}</td>
                      <td class="table-td">{{ session.has_rssi ? '수집됨' : '없음' }}</td>
                      <td class="table-td">{{ formatDateTime(session.uploaded_at) }}</td>
                      <td class="table-td text-center">
                        <button
                          type="button"
                          class="rounded-lg bg-slate-900 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-800"
                          @click="downloadSessionCsv(session)"
                        >
                          다운로드
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </template>

            <template v-else-if="activeSubtab === 'legal-consents'">
              <div class="stat-grid">
                <div class="stat-card">
                  <span>배송원</span>
                  <strong>{{ formatNumber(legalConsentSummary.crew_count) }}명</strong>
                </div>
                <div class="stat-card">
                  <span>앱 계정</span>
                  <strong>{{ formatNumber(legalConsentSummary.mobile_account_count) }}명</strong>
                </div>
                <div class="stat-card">
                  <span>필수 전체 동의</span>
                  <strong>{{ formatNumber(legalConsentSummary.all_required_agreed_count) }}명</strong>
                </div>
                <div class="stat-card">
                  <span>현재 약관 버전</span>
                  <strong class="text-lg">{{ legalConsentSummary.current_version || '-' }}</strong>
                </div>
              </div>

              <div v-if="workLoading && legalConsentRows.length === 0" class="empty-state">로딩 중...</div>
              <div v-else-if="legalConsentRows.length === 0" class="empty-state">약관 동의 이력 데이터가 없습니다.</div>
              <div v-else class="overflow-x-auto rounded-xl border border-slate-200 bg-white">
                <table class="w-full min-w-[1180px] text-sm">
                  <thead class="border-b border-slate-200 bg-slate-50">
                    <tr>
                      <th class="table-th">조</th>
                      <th class="table-th">기사이름</th>
                      <th class="table-th">차량</th>
                      <th class="table-th">앱 계정</th>
                      <th
                        v-for="column in legalConsentColumns"
                        :key="column.key"
                        class="table-th"
                      >
                        {{ column.label }}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="row in legalConsentRows" :key="row.id" class="border-b border-slate-100">
                      <td class="table-td">{{ row.team_name || '-' }}</td>
                      <td class="table-td font-semibold">{{ row.name }}</td>
                      <td class="table-td">{{ row.vehicle_number || '-' }}</td>
                      <td class="table-td">
                        <span
                          class="consent-badge"
                          :class="row.has_mobile_account ? 'ok' : 'missing'"
                        >
                          {{ row.has_mobile_account ? '있음' : '없음' }}
                        </span>
                        <span class="mt-1 block text-xs text-slate-500">
                          {{ row.last_app_version || '-' }}
                        </span>
                      </td>
                      <td
                        v-for="column in legalConsentColumns"
                        :key="`${row.id}-${column.key}`"
                        class="table-td consent-table-cell"
                      >
                        <div class="consent-cell">
                          <span
                            class="consent-badge"
                            :class="getConsentCell(row, column.key).agreed ? 'ok' : 'missing'"
                          >
                            {{ getConsentCell(row, column.key).agreed ? '동의' : '미동의' }}
                          </span>
                          <span class="consent-line">
                            버전 {{ getConsentCell(row, column.key).version || '기록 없음' }}
                          </span>
                          <span class="consent-line">
                            {{ formatDateTime(getConsentCell(row, column.key).agreed_at) }}
                          </span>
                          <span
                            v-if="getConsentCell(row, column.key).source === 'legacy_field'"
                            class="consent-source"
                          >
                            필드 확인
                          </span>
                          <span
                            v-else-if="getConsentCell(row, column.key).app_version"
                            class="consent-source"
                          >
                            앱 {{ getConsentCell(row, column.key).app_version }}
                          </span>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </template>
          </section>

          <section v-else-if="activeTab === 'points'" class="space-y-5">
            <div class="subtab-bar">
              <RouterLink
                :to="{ name: 'CleverPortalPointsSummary' }"
                class="subtab-pill"
                :class="{ active: activeSubtab === 'summary' }"
              >
                포인트 조회
              </RouterLink>
              <RouterLink
                :to="{ name: 'CleverPortalPointsShop' }"
                class="subtab-pill"
                :class="{ active: activeSubtab === 'shop' }"
              >
                상점 설정
              </RouterLink>
            </div>

            <template v-if="activeSubtab === 'shop'">
              <div class="rounded-xl border border-slate-200 bg-white p-5">
                <div class="grid gap-4 md:grid-cols-5">
                  <label class="md:col-span-1">
                    <span class="mb-2 block text-sm font-semibold text-slate-700">키</span>
                    <input v-model="pointItemForm.key" type="text" class="form-input" />
                  </label>
                  <label class="md:col-span-2">
                    <span class="mb-2 block text-sm font-semibold text-slate-700">항목명</span>
                    <input v-model="pointItemForm.name" type="text" class="form-input" />
                  </label>
                  <label>
                    <span class="mb-2 block text-sm font-semibold text-slate-700">포인트</span>
                    <input v-model.number="pointItemForm.cost_points" type="number" min="0" class="form-input" />
                  </label>
                  <label>
                    <span class="mb-2 block text-sm font-semibold text-slate-700">정렬순서</span>
                    <input v-model.number="pointItemForm.sort_order" type="number" min="0" class="form-input" />
                  </label>
                </div>
                <label class="mt-4 inline-flex items-center gap-2 text-sm font-medium text-slate-700">
                  <input v-model="pointItemForm.is_active" type="checkbox" />
                  사용 중
                </label>
                <div class="mt-4 flex flex-wrap gap-2">
                  <button type="button" class="primary-btn" :disabled="shopSaving" @click="submitPointItem">
                    {{ editingPointItemId ? '수정 저장' : '항목 추가' }}
                  </button>
                  <button type="button" class="secondary-btn" @click="resetPointItemForm">초기화</button>
                </div>
              </div>

              <div v-if="shopLoading && pointItems.length === 0" class="empty-state">로딩 중...</div>
              <div v-else-if="pointItems.length === 0" class="empty-state">등록된 상점 항목이 없습니다.</div>
              <div v-else class="overflow-x-auto rounded-xl border border-slate-200 bg-white">
                <table class="w-full min-w-[860px] text-sm">
                  <thead class="border-b border-slate-200 bg-slate-50">
                    <tr>
                      <th class="table-th">정렬</th>
                      <th class="table-th">키</th>
                      <th class="table-th">항목명</th>
                      <th class="table-th text-right">포인트</th>
                      <th class="table-th">상태</th>
                      <th class="table-th text-right">작업</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="item in pointItems" :key="item.id" class="border-b border-slate-100">
                      <td class="table-td">{{ formatNumber(item.sort_order) }}</td>
                      <td class="table-td font-mono text-xs">{{ item.key }}</td>
                      <td class="table-td font-semibold">{{ item.name }}</td>
                      <td class="table-td text-right">{{ formatNumber(item.cost_points) }}P</td>
                      <td class="table-td">{{ item.is_active ? '사용 중' : '비활성' }}</td>
                      <td class="table-td text-right">
                        <div class="flex justify-end gap-2">
                          <button type="button" class="table-action" @click="startEditPointItem(item)">수정</button>
                          <button type="button" class="table-action danger" @click="removePointItem(item)">삭제</button>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </template>

            <template v-else>
              <div class="team-button-panel">
                <span class="team-button-label">조 선택</span>
                <div class="team-buttons">
                  <button type="button" :class="{ active: selectedTeamId === '' }" @click="selectTeam('')">전체</button>
                  <button
                    v-for="team in teams"
                    :key="team.id"
                    type="button"
                    :class="{ active: selectedTeamId === String(team.id) }"
                    @click="selectTeam(String(team.id))"
                  >
                    {{ team.name }}
                  </button>
                </div>
                <button class="refresh-button" type="button" @click="loadPoints" :disabled="pointLoading">새로고침</button>
              </div>

              <div v-if="pointLoading && pointRows.length === 0" class="empty-state">로딩 중...</div>
              <div v-else-if="pointRows.length === 0" class="empty-state">포인트 데이터가 없습니다.</div>
              <div v-else class="overflow-x-auto rounded-xl border border-slate-200 bg-white">
                <table class="w-full min-w-[1100px] text-sm">
                  <thead class="border-b border-slate-200 bg-slate-50">
                    <tr>
                      <th class="table-th">조</th>
                      <th class="table-th">배송원</th>
                      <th class="table-th">차량번호</th>
                      <th class="table-th text-right">보유 포인트</th>
                      <th class="table-th text-right">사용 대기</th>
                      <th class="table-th text-right">사용 가능</th>
                      <th class="table-th">사용 요청</th>
                      <th class="table-th">직접 수정</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="row in pointRows"
                      :key="row.id"
                      class="border-b border-slate-100"
                      :class="{ 'bg-amber-50': row.pending_redemptions?.length }"
                    >
                      <td class="table-td">{{ row.team_name || '-' }}</td>
                      <td class="table-td font-semibold">{{ row.name }}</td>
                      <td class="table-td">{{ row.vehicle_number || '-' }}</td>
                      <td class="table-td text-right font-semibold">{{ formatNumber(row.balance) }}P</td>
                      <td class="table-td text-right">{{ formatNumber(row.pending_points) }}P</td>
                      <td class="table-td text-right">{{ formatNumber(row.available_points) }}P</td>
                      <td class="table-td">
                        <div v-if="row.pending_redemptions?.length" class="space-y-2">
                          <div
                            v-for="redemption in row.pending_redemptions"
                            :key="redemption.id"
                            class="flex items-center justify-between gap-3 rounded-lg border border-amber-300 bg-white p-2"
                          >
                            <div class="min-w-0">
                              <div class="font-semibold text-slate-900">{{ redemption.item_name }}</div>
                              <div class="text-xs text-amber-700">{{ formatNumber(redemption.cost_points) }}P</div>
                            </div>
                            <div class="flex shrink-0 gap-1.5">
                              <button
                                type="button"
                                class="rounded-lg bg-slate-900 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
                                :disabled="pointActionLoading === redemption.id"
                                @click="confirmRedemption(redemption.id)"
                              >
                                승인
                              </button>
                              <button
                                type="button"
                                class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-600 hover:bg-red-100 disabled:opacity-50"
                                :disabled="pointActionLoading === redemption.id"
                                @click="cancelRedemption(redemption)"
                              >
                                취소
                              </button>
                            </div>
                          </div>
                        </div>
                        <span v-else class="text-slate-400">-</span>
                      </td>
                      <td class="table-td">
                        <div class="flex items-center gap-2">
                          <input
                            v-model.number="pointDrafts[row.id]"
                            type="number"
                            min="0"
                            class="w-28 rounded-lg border border-slate-300 px-3 py-2 text-right outline-none focus:border-lime-500"
                          />
                          <button
                            type="button"
                            class="rounded-lg bg-slate-900 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
                            :disabled="pointSavingCrewId === row.id"
                            @click="savePointBalance(row)"
                          >
                            저장
                          </button>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </template>
          </section>

          <section v-else-if="activeTab === 'app'" class="space-y-5">
            <div class="rounded-xl border border-slate-200 bg-white p-5">
              <div class="flex items-center justify-between gap-3">
                <div>
                  <h3 class="text-lg font-semibold text-slate-900">앱 팝업 문구 관리</h3>
                  <p class="mt-1 text-sm text-slate-500">기사용 앱에 표시되는 안내 문구를 서버에서 직접 수정합니다.</p>
                </div>
                <div class="flex gap-2">
                  <button type="button" class="secondary-btn" :disabled="appConfigLoading" @click="loadAppConfig">다시 불러오기</button>
                  <button type="button" class="primary-btn" :disabled="appConfigSaving" @click="saveAppConfig">저장</button>
                </div>
              </div>

              <div
                v-if="appConfigNotice"
                class="mt-4 rounded-lg border p-3 text-sm"
                :class="appConfigNotice.type === 'success' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-red-200 bg-red-50 text-red-700'"
              >
                {{ appConfigNotice.message }}
              </div>

              <div v-if="appConfigLoading" class="empty-state mt-4">로딩 중...</div>
              <div v-else-if="appConfigSections.length === 0" class="empty-state mt-4">앱 관리 항목이 없습니다.</div>
              <div v-else class="mt-4 space-y-6">
                <section
                  v-for="section in appConfigSections"
                  :key="section.key"
                  class="rounded-xl border border-slate-200 bg-slate-50 p-4"
                >
                  <h4 class="text-base font-semibold text-slate-900">{{ section.title || section.key }}</h4>
                  <p v-if="section.description" class="mt-1 text-sm text-slate-500">{{ section.description }}</p>
                  <div class="mt-4 grid gap-4 md:grid-cols-2">
                    <label
                      v-for="field in section.fields || []"
                      :key="field.key"
                      class="block"
                      :class="{ 'md:col-span-2': (field.rows || 0) >= 3 }"
                    >
                      <span class="mb-2 block text-sm font-semibold text-slate-700">
                        {{ field.label || field.title || field.key }}
                      </span>
                      <p v-if="field.description" class="mb-2 text-xs text-slate-500">{{ field.description }}</p>
                      <textarea
                        v-model="appConfigForm[field.key]"
                        class="min-h-[120px] w-full rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-lime-500"
                        :rows="field.rows || 5"
                      ></textarea>
                    </label>
                  </div>
                </section>
              </div>
            </div>
          </section>

          <section v-else-if="activeTab === 'vehicle'" class="space-y-5">
            <VehicleManagementPanel :subtab="activeSubtab || 'status'" />
          </section>

          <section v-else-if="activeTab === 'pit'" class="space-y-5">
            <PitManagementPanel :subtab="activeSubtab || 'status'" />
          </section>
        </section>
      </section>
    </main>

    <div
      v-if="pointDetailModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 px-4 py-6"
      @click.self="closePointDetail"
    >
      <section class="flex max-h-[86vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
        <header class="flex items-start justify-between gap-4 border-b border-slate-200 px-6 py-5">
          <div>
            <p class="text-sm font-bold text-lime-600">{{ pointDetailModal.team_name || '-' }}</p>
            <h3 class="mt-1 text-2xl font-extrabold text-slate-900">{{ pointDetailModal.name }}</h3>
            <p class="mt-1 text-sm text-slate-500">
              보유 {{ formatNumber(pointDetailModal.balance) }}P · 사용 가능 {{ formatNumber(pointDetailModal.available_points) }}P
            </p>
          </div>
          <button
            type="button"
            class="rounded-xl border border-slate-300 px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50"
            @click="closePointDetail"
          >
            닫기
          </button>
        </header>

        <div v-if="pointDetailLoading" class="px-6 py-12 text-center text-slate-400">포인트 내역을 불러오는 중...</div>
        <div v-else-if="pointDetailError" class="mx-6 my-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">
          {{ pointDetailError }}
        </div>
        <div v-else class="min-h-0 overflow-y-auto">
          <div class="grid grid-cols-3 gap-3 border-b border-slate-100 px-6 py-4 text-sm">
            <div class="rounded-xl bg-slate-50 p-4">
              <span class="block text-xs font-bold text-slate-500">보유 포인트</span>
              <strong class="mt-1 block text-xl text-slate-900">{{ formatNumber(pointDetailModal.balance) }}P</strong>
            </div>
            <div class="rounded-xl bg-slate-50 p-4">
              <span class="block text-xs font-bold text-slate-500">사용 대기</span>
              <strong class="mt-1 block text-xl text-amber-700">{{ formatNumber(pointDetailModal.pending_points) }}P</strong>
            </div>
            <div class="rounded-xl bg-slate-50 p-4">
              <span class="block text-xs font-bold text-slate-500">사용 가능</span>
              <strong class="mt-1 block text-xl text-lime-700">{{ formatNumber(pointDetailModal.available_points) }}P</strong>
            </div>
          </div>

          <div v-if="!pointDetailTransactions.length" class="px-6 py-12 text-center text-slate-400">
            포인트 지급 내역이 없습니다.
          </div>
          <table v-else class="w-full text-sm">
            <thead class="sticky top-0 z-10 border-b border-slate-200 bg-slate-50">
              <tr>
                <th class="table-th">지급/처리 시각</th>
                <th class="table-th">근무일</th>
                <th class="table-th">구분</th>
                <th class="table-th text-right">포인트</th>
                <th class="table-th">메모</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="tx in pointDetailTransactions" :key="tx.id" class="border-b border-slate-100">
                <td class="table-td">{{ formatDateTime(tx.created_at) }}</td>
                <td class="table-td">{{ tx.work_date || '-' }}</td>
                <td class="table-td">
                  <span
                    class="rounded-full px-2.5 py-1 text-xs font-bold"
                    :class="Number(tx.points || 0) >= 0 ? 'bg-lime-50 text-lime-700' : 'bg-red-50 text-red-600'"
                  >
                    {{ formatPointKind(tx) }}
                  </span>
                </td>
                <td
                  class="table-td text-right font-extrabold"
                  :class="Number(tx.points || 0) >= 0 ? 'text-lime-700' : 'text-red-600'"
                >
                  {{ formatSignedPoint(tx.points) }}
                </td>
                <td class="table-td whitespace-normal text-slate-600">
                  {{ tx.memo || tx.redemption_item_name || '-' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import client from '@/api/client'
import { fetchMobileAppConfig, updateMobileAppConfig } from '@/api/mobileAdmin'
import { fetchPublicCompanyApps } from '@/api/companyAdmin'
import OperationReportPanel from '@/components/operations/OperationReportPanel.vue'
import CompanyManagementPanel from '@/components/portal/CompanyManagementPanel.vue'
import PitManagementPanel from '@/components/portal/PitManagementPanel.vue'
import RevenueStatusPanel from '@/components/portal/RevenueStatusPanel.vue'
import VehicleManagementPanel from '@/components/portal/VehicleManagementPanel.vue'
import {
  cancelPointRedemption,
  confirmPointRedemption,
  createPointItem,
  deletePointItem,
  fetchCrewPointDetail,
  fetchPointItems,
  fetchPointSummaries,
  setCrewPointBalance,
  updatePointItem,
} from '@/api/points'
import {
  downloadTrackingCsv,
  fetchLegalConsentMatrix,
  fetchLiveWorkStatuses,
  fetchTrackingUsageOverview,
} from '@/api/tracking'
import { useAuthStore } from '@/stores/auth'
import { buildCompanyApp, getSelectedCompanyAppCode, setRuntimeCompanyApps, setSelectedCompanyAppCode } from '@/utils/companyApp'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const companies = ref([
  { code: 'cheonha', name: '천하운수', dashboardPath: '/cheonha/dashboard' },
])
setRuntimeCompanyApps(companies.value)
const cleverAdminUsernames = ['clever_admin', 'admin2']

const selectedCompany = ref(getSelectedCompanyAppCode())

const loginId = ref('')
const loginPassword = ref('')
const loginLoading = ref(false)
const loginError = ref('')

const teams = ref([])
const selectedTeamId = ref('')

const workLoading = ref(false)
const workRefreshing = ref(false)
const liveSummary = ref({ crew_count: 0, working_count: 0, background_location_ok_count: 0 })
const liveRows = ref([])
const trackingSummary = ref({ crew_count: 0, mobile_account_count: 0, data_ready_count: 0, session_count: 0 })
const trackingSessions = ref([])
const legalConsentSummary = ref({ crew_count: 0, mobile_account_count: 0, all_required_agreed_count: 0, missing_required_count: 0, current_version: '' })
const legalConsentColumns = ref([])
const legalConsentRows = ref([])
const usageStartDate = ref(toDateInput(addDays(new Date(), -6)))
const usageEndDate = ref(toDateInput(new Date()))

const pointLoading = ref(false)
const pointRows = ref([])
const pointDrafts = ref({})
const pointSavingCrewId = ref(null)
const pointActionLoading = ref(null)
const pointDetailModal = ref(null)
const pointDetailLoading = ref(false)
const pointDetailError = ref('')
const pointItems = ref([])
const shopLoading = ref(false)
const shopSaving = ref(false)
const editingPointItemId = ref(null)
const pointItemForm = ref(createEmptyPointItemForm())

const appConfigLoading = ref(false)
const appConfigSaving = ref(false)
const appConfigSections = ref([])
const appConfigForm = ref({})
const appConfigNotice = ref(null)

const selectedCompanyItem = computed(() => companies.value.find((company) => company.code === selectedCompany.value) || companies.value[0])
const selectedCompanyName = computed(() => selectedCompanyItem.value?.name || selectedCompany.value)
const companyLink = computed(() => selectedCompanyItem.value?.dashboardPath || buildCompanyApp({ code: selectedCompany.value }).dispatchPath)
const selectedTeamName = computed(() => teams.value.find((team) => String(team.id) === String(selectedTeamId.value))?.name || '')
const activeTab = computed(() => route.meta.portalTab || 'operations')
const activeSubtab = computed(() => route.meta.portalSubtab || '')
const isCleverAdminSession = computed(() => {
  const username = authStore.user?.username || ''
  return authStore.isAuthenticated && cleverAdminUsernames.includes(username)
})

const activeTitle = computed(() => {
  if (activeTab.value === 'companies') return '회사 관리'
  if (activeTab.value === 'revenue') return '매출 현황'
  if (activeTab.value === 'work') return '근무기록'
  if (activeTab.value === 'points') return '포인트'
  if (activeTab.value === 'app') return '앱 관리'
  if (activeTab.value === 'vehicle') return '차량관리'
  if (activeTab.value === 'pit') return '피트'
  return '운영현황'
})

const activeDescription = computed(() => {
  if (activeTab.value === 'companies') return '회사 추가, 대표 계정 승인, 회사별 탭 노출을 관리합니다.'
  if (activeTab.value === 'revenue') return '업체별 월별·일별 매출과 예상매출을 확인합니다.'
  if (activeTab.value === 'work' && activeSubtab.value === 'live') return '실시간 근무 상태와 위치 권한 상태를 확인합니다.'
  if (activeTab.value === 'work' && activeSubtab.value === 'legal-consents') return '배송앱 필수 약관의 동의 여부와 동의 당시 버전을 확인합니다.'
  if (activeTab.value === 'work') return '근무기록 CSV 수집 현황과 업로드 상태를 확인합니다.'
  if (activeTab.value === 'points' && activeSubtab.value === 'shop') return '포인트 상점 항목과 교환 비용을 관리합니다.'
  if (activeTab.value === 'points') return '기사별 포인트 잔액과 사용 요청을 처리합니다.'
  if (activeTab.value === 'app') return '기사용 앱에 표시되는 팝업과 안내 문구를 관리합니다.'
  if (activeTab.value === 'vehicle') return '차량관리, 캘린더, 구독 요청 현황을 봅니다.'
  if (activeTab.value === 'pit') return '피트 차량현황, 차량 배정, A/S 진행을 관리합니다.'
  return '회사별 운영 지표를 날짜 기준으로 확인합니다.'
})

const pointItemNextSortOrder = computed(() => {
  if (!pointItems.value.length) return 1
  return Math.max(...pointItems.value.map((item) => Number(item.sort_order || 0))) + 1
})

function toDateInput(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function addDays(date, days) {
  const next = new Date(date)
  next.setDate(next.getDate() + days)
  return next
}

function applyCompanyList(rows = []) {
  const normalized = (rows || []).map((company) => {
    const app = buildCompanyApp(company)
    return {
      ...company,
      name: company.name || app.displayName,
      dashboardPath: app.enabledTabs?.includes('dashboard') ? app.dashboardPath : app.dispatchPath,
    }
  })
  if (normalized.length) {
    companies.value = normalized
    setRuntimeCompanyApps(normalized)
    if (!companies.value.some((company) => company.code === selectedCompany.value)) {
      selectedCompany.value = companies.value[0].code
    }
  }
}

async function loadCompanyList() {
  try {
    const response = await fetchPublicCompanyApps()
    applyCompanyList(response.data?.results || response.data || [])
  } catch (error) {
    if (!companies.value.length) {
      applyCompanyList([{ code: 'cheonha', name: '천하운수' }])
    }
  }
}

function createEmptyPointItemForm(nextSortOrder = 1) {
  return {
    key: '',
    name: '',
    cost_points: 0,
    sort_order: nextSortOrder,
    is_active: true,
  }
}

function buildTeamParams() {
  return selectedTeamId.value ? { team: selectedTeamId.value } : {}
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString()
}

function formatKm(meters) {
  return `${(Number(meters || 0) / 1000).toLocaleString(undefined, { maximumFractionDigits: 2 })}km`
}

function formatDateTime(value) {
  if (!value) return '-'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function getConsentCell(row, key) {
  return row?.consents?.[key] || {
    agreed: false,
    version: '',
    agreed_at: null,
    app_version: '',
    source: 'none',
  }
}

const pointDetailTransactions = computed(() => pointDetailModal.value?.transactions || [])

function formatSignedPoint(value) {
  const points = Number(value || 0)
  const sign = points > 0 ? '+' : ''
  return `${sign}${formatNumber(points)}P`
}

function formatPointKind(tx = {}) {
  if (tx.kind === 'WORK_REWARD') return '근무 지급'
  if (tx.kind === 'MANUAL_ADJUST') return '수동 조정'
  if (tx.kind === 'REDEMPTION_DEDUCT') return '사용 차감'
  return tx.kind || '-'
}

function applyAppConfigPayload(payload = {}) {
  const sections = payload.sections || []
  const messages = payload.messages || {}
  appConfigSections.value = sections
  appConfigForm.value = sections.reduce((acc, section) => {
    for (const field of section.fields || []) {
      acc[field.key] = messages[field.key] ?? field.default_value ?? ''
    }
    return acc
  }, {})
}

async function loadTeams() {
  try {
    const response = await client.get('/accounts/teams/')
    teams.value = response.data.results || response.data || []
  } catch {
    teams.value = []
  }
}

async function loadLiveStatus() {
  workLoading.value = true
  workRefreshing.value = true
  try {
    const response = await fetchLiveWorkStatuses(buildTeamParams())
    liveSummary.value = response.data.summary || { crew_count: 0, working_count: 0, background_location_ok_count: 0 }
    liveRows.value = response.data.rows || []
  } catch {
    liveSummary.value = { crew_count: 0, working_count: 0, background_location_ok_count: 0 }
    liveRows.value = []
  } finally {
    workLoading.value = false
    workRefreshing.value = false
  }
}

async function loadTrackingOverview() {
  workLoading.value = true
  workRefreshing.value = true
  try {
    const response = await fetchTrackingUsageOverview({
      ...buildTeamParams(),
      start_date: usageStartDate.value || undefined,
      end_date: usageEndDate.value || undefined,
    })
    trackingSummary.value = response.data.summary || { crew_count: 0, mobile_account_count: 0, data_ready_count: 0, session_count: 0 }
    trackingSessions.value = response.data.sessions || []
  } catch {
    trackingSummary.value = { crew_count: 0, mobile_account_count: 0, data_ready_count: 0, session_count: 0 }
    trackingSessions.value = []
  } finally {
    workLoading.value = false
    workRefreshing.value = false
  }
}

async function loadLegalConsentMatrix() {
  workLoading.value = true
  workRefreshing.value = true
  try {
    const response = await fetchLegalConsentMatrix(buildTeamParams())
    legalConsentSummary.value = response.data.summary || {
      crew_count: 0,
      mobile_account_count: 0,
      all_required_agreed_count: 0,
      missing_required_count: 0,
      current_version: '',
    }
    legalConsentColumns.value = response.data.columns || []
    legalConsentRows.value = response.data.rows || []
  } catch {
    legalConsentSummary.value = {
      crew_count: 0,
      mobile_account_count: 0,
      all_required_agreed_count: 0,
      missing_required_count: 0,
      current_version: '',
    }
    legalConsentColumns.value = []
    legalConsentRows.value = []
  } finally {
    workLoading.value = false
    workRefreshing.value = false
  }
}

async function loadPoints() {
  pointLoading.value = true
  try {
    const response = await fetchPointSummaries(buildTeamParams())
    const rows = response.data.results || response.data || []
    pointRows.value = rows
    pointDrafts.value = rows.reduce((acc, row) => {
      acc[row.id] = row.balance || 0
      return acc
    }, {})
  } catch {
    pointRows.value = []
    pointDrafts.value = {}
  } finally {
    pointLoading.value = false
  }
}

async function openPointDetail(row) {
  pointDetailModal.value = { ...row, transactions: [], redemptions: [] }
  pointDetailLoading.value = true
  pointDetailError.value = ''
  try {
    const response = await fetchCrewPointDetail(row.id)
    pointDetailModal.value = {
      ...row,
      ...(response.data || {}),
      transactions: response.data?.transactions || [],
      redemptions: response.data?.redemptions || [],
    }
  } catch (error) {
    pointDetailError.value = error.response?.data?.detail || '포인트 내역을 불러오지 못했습니다.'
  } finally {
    pointDetailLoading.value = false
  }
}

function closePointDetail() {
  pointDetailModal.value = null
  pointDetailLoading.value = false
  pointDetailError.value = ''
}

async function loadPointItems() {
  shopLoading.value = true
  try {
    const response = await fetchPointItems()
    pointItems.value = response.data.results || response.data || []
    if (!editingPointItemId.value) {
      pointItemForm.value = createEmptyPointItemForm(pointItemNextSortOrder.value)
    }
  } catch {
    pointItems.value = []
  } finally {
    shopLoading.value = false
  }
}

async function loadAppConfig() {
  appConfigLoading.value = true
  appConfigNotice.value = null
  try {
    const response = await fetchMobileAppConfig()
    applyAppConfigPayload(response.data || {})
  } catch (error) {
    appConfigSections.value = []
    appConfigForm.value = {}
    appConfigNotice.value = {
      type: 'error',
      message: error.response?.data?.detail || '앱 설정을 불러오지 못했습니다.',
    }
  } finally {
    appConfigLoading.value = false
  }
}

async function saveAppConfig() {
  appConfigSaving.value = true
  appConfigNotice.value = null
  try {
    const response = await updateMobileAppConfig({ messages: appConfigForm.value })
    applyAppConfigPayload(response.data || {})
    appConfigNotice.value = { type: 'success', message: '앱 문구를 저장했습니다.' }
  } catch (error) {
    appConfigNotice.value = {
      type: 'error',
      message: error.response?.data?.detail || '앱 문구 저장에 실패했습니다.',
    }
  } finally {
    appConfigSaving.value = false
  }
}

async function refreshCurrentView() {
  if (activeTab.value === 'companies') {
    return
  }
  if (activeTab.value === 'work') {
    if (activeSubtab.value === 'legal-consents') {
      await loadLegalConsentMatrix()
      return
    }
    if (activeSubtab.value === 'csv') {
      await loadTrackingOverview()
      return
    }
    await loadLiveStatus()
    return
  }
  if (activeTab.value === 'points') {
    if (activeSubtab.value === 'shop') {
      await loadPointItems()
      return
    }
    await loadPoints()
    return
  }
  if (activeTab.value === 'app') {
    await loadAppConfig()
  }
}

async function selectTeam(teamId) {
  selectedTeamId.value = teamId || ''
  if (activeTab.value !== 'operations' && activeTab.value !== 'vehicle' && activeTab.value !== 'pit') {
    await refreshCurrentView()
  }
}

async function savePointBalance(row) {
  const balance = Number(pointDrafts.value[row.id] || 0)
  if (!Number.isFinite(balance) || balance < 0) {
    window.alert('포인트는 0 이상의 숫자만 입력할 수 있습니다.')
    return
  }
  pointSavingCrewId.value = row.id
  try {
    await setCrewPointBalance(row.id, {
      balance,
      memo: 'CLEVER 포인트 조회 직접 수정',
    })
    await loadPoints()
  } catch (error) {
    window.alert(error.response?.data?.detail || '포인트 수정에 실패했습니다.')
  } finally {
    pointSavingCrewId.value = null
  }
}

async function confirmRedemption(redemptionId) {
  pointActionLoading.value = redemptionId
  try {
    await confirmPointRedemption(redemptionId)
    await loadPoints()
  } catch (error) {
    window.alert(error.response?.data?.detail || '사용 요청 승인에 실패했습니다.')
  } finally {
    pointActionLoading.value = null
  }
}

async function cancelRedemption(redemption) {
  if (!redemption?.id) return
  const itemName = redemption.item_name || '포인트 사용 요청'
  const cost = formatNumber(redemption.cost_points)
  if (!window.confirm(`${itemName} ${cost}P 사용 요청을 취소할까요?`)) return

  pointActionLoading.value = redemption.id
  try {
    await cancelPointRedemption(redemption.id, {
      note: '관리자 요청 취소',
    })
    await loadPoints()
  } catch (error) {
    window.alert(error.response?.data?.detail || '사용 요청 취소에 실패했습니다.')
  } finally {
    pointActionLoading.value = null
  }
}

function resetPointItemForm() {
  editingPointItemId.value = null
  pointItemForm.value = createEmptyPointItemForm(pointItemNextSortOrder.value)
}

function startEditPointItem(item) {
  editingPointItemId.value = item.id
  pointItemForm.value = {
    key: item.key || '',
    name: item.name || '',
    cost_points: Number(item.cost_points || 0),
    sort_order: Number(item.sort_order || 0),
    is_active: Boolean(item.is_active),
  }
}

async function submitPointItem() {
  const payload = {
    key: String(pointItemForm.value.key || '').trim(),
    name: String(pointItemForm.value.name || '').trim(),
    cost_points: Number(pointItemForm.value.cost_points || 0),
    sort_order: Number(pointItemForm.value.sort_order || 0),
    is_active: Boolean(pointItemForm.value.is_active),
  }
  if (!payload.key || !payload.name) {
    window.alert('키와 항목명을 입력하세요.')
    return
  }
  shopSaving.value = true
  try {
    if (editingPointItemId.value) {
      await updatePointItem(editingPointItemId.value, payload)
    } else {
      await createPointItem(payload)
    }
    resetPointItemForm()
    await loadPointItems()
  } catch (error) {
    window.alert(error.response?.data?.detail || '상점 항목 저장에 실패했습니다.')
  } finally {
    shopSaving.value = false
  }
}

async function removePointItem(item) {
  if (!window.confirm(`${item.name} 항목을 삭제할까요?`)) return
  try {
    await deletePointItem(item.id)
    if (editingPointItemId.value === item.id) {
      resetPointItemForm()
    }
    await loadPointItems()
  } catch (error) {
    window.alert(error.response?.data?.detail || '상점 항목 삭제에 실패했습니다.')
  }
}

function downloadBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

async function downloadSessionCsv(session) {
  const response = await downloadTrackingCsv(session.id)
  const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8;' })
  downloadBlob(blob, `CLEVER_${selectedCompanyName.value}_근무기록_${session.session_date}_${session.crew_name || session.id}.csv`)
}

async function login() {
  loginLoading.value = true
  loginError.value = ''
  try {
    await authStore.cleverLogin(loginId.value, loginPassword.value)
  } catch (error) {
    loginError.value = error.response?.data?.detail || '로그인에 실패했습니다.'
  } finally {
    loginLoading.value = false
  }
}

async function logout() {
  authStore.logout()
  liveRows.value = []
  trackingSessions.value = []
  legalConsentRows.value = []
  pointRows.value = []
  pointItems.value = []
  appConfigSections.value = []
  appConfigForm.value = {}
  await router.push('/')
}

watch(
  isCleverAdminSession,
  async (enabled) => {
    if (!enabled) return
    await loadCompanyList()
    setSelectedCompanyAppCode(selectedCompany.value)
    await loadTeams()
    await refreshCurrentView()
  },
  { immediate: true },
)

watch(selectedCompany, async (companyCode) => {
  setSelectedCompanyAppCode(companyCode)
  selectedTeamId.value = ''
  if (!isCleverAdminSession.value) return
  await loadTeams()
  await refreshCurrentView()
})

watch(
  () => [activeTab.value, activeSubtab.value],
  async () => {
    if (!isCleverAdminSession.value) return
    await refreshCurrentView()
  },
  { immediate: true },
)

onMounted(() => {
  if (isCleverAdminSession.value) {
    void loadCompanyList()
  }
})
</script>

<style scoped>
.portal-layout {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 20px;
  align-items: start;
}

.portal-layout > * {
  min-width: 0;
}

.portal-sidebar {
  position: sticky;
  top: 24px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  border: 1px solid #d7dde5;
  border-radius: 8px;
  background: #ffffff;
  padding: 16px;
}

.sidebar-head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 14px;
  border-bottom: 1px solid #e2e8f0;
}

.sidebar-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 8px;
  background: #111827;
  color: #ffffff;
  font-size: 13px;
  font-weight: 900;
}

.sidebar-kicker {
  color: #64748b;
  font-size: 11px;
  font-weight: 900;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sidebar-tab {
  display: block;
  border-radius: 10px;
  padding: 12px 14px;
  border: 1px solid #e5e7eb;
  color: #334155;
  transition: all 0.15s ease;
}

.sidebar-tab span {
  display: block;
  font-weight: 700;
}

.sidebar-tab small {
  display: block;
  margin-top: 3px;
  font-size: 12px;
  color: #64748b;
}

.sidebar-tab:hover {
  background: #f8fafc;
}

.sidebar-tab.active {
  border-color: #84cc16;
  background: #ecfccb;
  color: #1e293b;
}

.portal-content {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.portal-topbar {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 20px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #ffffff;
  padding: 18px 20px;
}

.portal-kicker {
  font-size: 12px;
  font-weight: 800;
  color: #84cc16;
}

.portal-desc {
  margin-top: 6px;
  color: #64748b;
  font-size: 14px;
}

.portal-company {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 180px;
}

.portal-company span {
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
}

.portal-company select,
.form-input,
.toolbar-card input {
  width: 100%;
  border: 1px solid #d1d5db;
  border-radius: 10px;
  padding: 10px 12px;
  outline: none;
}

.team-button-panel,
.toolbar-card,
.subtab-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #ffffff;
  padding: 14px 16px;
}

.team-button-label {
  font-size: 13px;
  font-weight: 800;
  color: #64748b;
}

.team-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.team-buttons button,
.subtab-pill,
.refresh-button,
.secondary-btn,
.primary-btn {
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 14px;
  font-weight: 700;
  transition: all 0.15s ease;
}

.team-buttons button {
  border: 1px solid #e5e7eb;
  background: #ffffff;
  color: #334155;
}

.team-buttons button.active,
.subtab-pill.active {
  background: #84cc16;
  border-color: #84cc16;
  color: #111827;
}

.subtab-pill {
  border: 1px solid #e5e7eb;
  color: #475569;
}

.refresh-button,
.secondary-btn {
  border: 1px solid #d1d5db;
  color: #334155;
}

.primary-btn {
  background: #84cc16;
  color: #111827;
}

.empty-state {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #ffffff;
  padding: 48px 16px;
  text-align: center;
  color: #94a3b8;
}

.stat-grid {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.stat-card {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #ffffff;
  padding: 18px;
}

.stat-card span {
  display: block;
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
}

.stat-card strong {
  display: block;
  margin-top: 6px;
  font-size: 24px;
  font-weight: 800;
  color: #0f172a;
}

.table-th {
  padding: 12px 16px;
  text-align: left;
  font-weight: 700;
  color: #475569;
}

.table-td {
  padding: 12px 16px;
  color: #334155;
  white-space: nowrap;
}

.consent-table-cell {
  min-width: 190px;
  white-space: normal;
  vertical-align: top;
}

.consent-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  line-height: 1.35;
}

.consent-badge {
  display: inline-flex;
  align-items: center;
  border-radius: 9999px;
  padding: 4px 9px;
  font-size: 12px;
  font-weight: 800;
}

.consent-badge.ok {
  background: #dcfce7;
  color: #166534;
}

.consent-badge.missing {
  background: #fee2e2;
  color: #991b1b;
}

.consent-line {
  color: #475569;
  font-size: 12px;
}

.consent-source {
  color: #64748b;
  font-size: 11px;
  font-weight: 700;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 9999px;
  background: #94a3b8;
}

.status-dot.working {
  background: #10b981;
}

.table-action {
  border-radius: 8px;
  border: 1px solid #d1d5db;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 700;
  color: #334155;
}

.table-action.danger {
  color: #b91c1c;
  border-color: #fecaca;
}

@media (max-width: 1024px) {
  .portal-layout {
    grid-template-columns: 1fr;
  }

  .portal-sidebar {
    position: static;
  }

  .portal-topbar {
    align-items: start;
    flex-direction: column;
  }
}
</style>
