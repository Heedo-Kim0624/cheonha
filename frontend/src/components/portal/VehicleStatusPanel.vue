<template>
  <div class="space-y-3">
    <section class="rounded-xl border border-slate-200 bg-white">
      <div class="flex flex-col gap-3 border-b border-slate-200 px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h3 class="text-base font-bold text-slate-950">전체 차량현황</h3>
          <p class="mt-1 text-sm text-slate-500">차량 상태와 플릿을 변경하고 수리 대기 차량을 피트로 입고합니다.</p>
        </div>
        <div class="flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <span>현재 필터: <strong class="text-slate-900">{{ activeCategoryLabel }}</strong></span>
          <span class="text-slate-300">|</span>
          <span>조회 {{ vehicles.length }}대</span>
          <button
            type="button"
            class="ml-1 rounded-md border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            @click="reload"
          >
            새로고침
          </button>
        </div>
      </div>

      <div class="grid border-b border-slate-200 bg-slate-50/70 sm:grid-cols-2 lg:grid-cols-4 2xl:grid-cols-7">
        <button
          v-for="card in summaryCards"
          :key="card.code || 'all'"
          type="button"
          class="flex items-center justify-between gap-3 border-b border-r border-slate-200 px-4 py-3 text-left last:border-r-0 hover:bg-white"
          :class="activeCategory === card.code ? 'bg-white ring-1 ring-inset ring-slate-900' : ''"
          @click="onCategory(card.code)"
        >
          <div class="min-w-0">
            <p class="text-sm font-bold text-slate-800">{{ card.label }}</p>
            <p class="mt-0.5 truncate text-xs text-slate-500">{{ card.description }}</p>
          </div>
          <strong class="text-xl font-bold text-slate-950">{{ countFor(card.code) }}</strong>
        </button>
      </div>

      <div class="grid gap-3 px-4 py-3 xl:grid-cols-[minmax(260px,1fr)_auto] xl:items-end">
        <label class="min-w-0">
          <span class="mb-1 block text-xs font-semibold text-slate-500">검색</span>
          <input
            v-model="search"
            type="text"
            placeholder="차량번호, VIN, 기사명, 회선명"
            class="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
            @input="debouncedReload"
          />
        </label>
        <p class="rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-500">
          피트 입고는 상태를 수리/대기중으로 변경한 뒤 처리합니다.
        </p>
      </div>

      <div v-if="subFleets.length" class="border-t border-slate-100 px-4 py-3">
        <div class="flex flex-wrap items-center gap-2">
          <span class="text-xs font-semibold text-slate-500">세부 플릿</span>
          <button
            type="button"
            class="rounded-md px-3 py-1.5 text-xs font-semibold"
            :class="activeFleet === '' ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
            @click="activeFleet = ''; reload()"
          >
            전체
          </button>
          <button
            v-for="f in subFleets"
            :key="f"
            type="button"
            class="rounded-md px-3 py-1.5 text-xs font-semibold"
            :class="activeFleet === f ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
            @click="activeFleet = f; reload()"
          >
            {{ f }} {{ stats.by_fleet?.[f] ?? 0 }}
          </button>
        </div>
      </div>
    </section>

    <section class="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
        <div>
          <h4 class="text-sm font-bold text-slate-950">차량 목록</h4>
          <p class="mt-0.5 text-xs text-slate-500">플릿과 배치 상태는 변경 즉시 저장됩니다.</p>
        </div>
        <span class="text-xs text-slate-500">{{ vehicles.length }}대</span>
      </div>

      <div class="max-h-[690px] overflow-auto">
        <table class="w-full min-w-[920px] table-fixed text-sm">
          <colgroup>
            <col class="w-[330px]" />
            <col class="w-[190px]" />
            <col class="w-[260px]" />
            <col class="w-[120px]" />
          </colgroup>
          <thead class="sticky top-0 z-10 border-b border-slate-200 bg-slate-50">
            <tr>
              <th class="px-4 py-2.5 text-left text-xs font-bold text-slate-500">차량</th>
              <th class="px-4 py-2.5 text-left text-xs font-bold text-slate-500">운영 정보</th>
              <th class="px-4 py-2.5 text-left text-xs font-bold text-slate-500">분류 / 상태</th>
              <th class="px-4 py-2.5 text-right text-xs font-bold text-slate-500">조치</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="v in vehicles" :key="v.id" class="border-t border-slate-100 hover:bg-slate-50">
              <td class="cursor-pointer px-4 py-3" @click="openVehicleDetail(v)">
                <div
                  role="button"
                  tabindex="0"
                  :data-vehicle-detail-id="v.id"
                  class="group block w-full min-w-0 rounded-lg px-2 py-1 text-left transition hover:bg-white hover:shadow-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
                  title="차량 상세정보 보기"
                  @keydown.enter.prevent="openVehicleDetail(v)"
                  @keydown.space.prevent="openVehicleDetail(v)"
                >
                  <div class="flex flex-wrap items-center gap-2">
                    <p class="font-bold text-slate-950">{{ v.vehicle_number }}</p>
                    <span class="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600">
                      {{ v.fleet || '미분류' }}
                    </span>
                    <span
                      v-if="v.registration_certificate_url"
                      class="rounded bg-emerald-50 px-2 py-0.5 text-[11px] font-bold text-emerald-700"
                    >
                      등록증
                    </span>
                  </div>
                  <p class="mt-1 text-xs text-slate-600">{{ v.model || '모델 미입력' }}</p>
                  <p class="mt-1 truncate text-xs text-slate-400" :title="`VIN ${v.vin_tid || '-'} / 회선 ${v.hgi || '-'}`">
                    VIN {{ v.vin_tid || '-' }} · 회선 {{ v.hgi || '-' }}
                  </p>
                  <p class="mt-1 text-[11px] font-semibold text-slate-400 group-hover:text-slate-700">
                    클릭해서 상세정보 보기
                  </p>
                </div>
              </td>
              <td class="px-4 py-3 text-xs">
                <p class="font-semibold text-slate-800">{{ v.shipped_at || '-' }}</p>
                <p class="mt-1 text-slate-500">기사 {{ v.driver || '-' }}</p>
              </td>
              <td class="px-4 py-3">
                <div class="grid gap-2 sm:grid-cols-2">
                  <select
                    :value="v.fleet"
                    class="w-full rounded-md border border-slate-300 bg-white px-2.5 py-2 text-xs font-semibold outline-none focus:border-slate-900"
                    @change="updateFleet(v, $event.target.value)"
                  >
                    <option v-for="f in FLEET_OPTIONS" :key="f" :value="f">{{ f || '미분류' }}</option>
                  </select>
                  <select
                    :value="v.placement_status"
                    :class="placementSelectClass(v.placement_status)"
                    class="w-full rounded-md border px-2.5 py-2 text-xs font-bold outline-none focus:border-slate-900"
                    @change="updatePlacement(v, $event.target.value)"
                  >
                    <option value="OPERATING">운영중</option>
                    <option value="REPAIRING">수리/대기중</option>
                    <option value="IDLE">유휴</option>
                    <option value="NOT_SHIPPED">미출고</option>
                  </select>
                </div>
              </td>
              <td class="px-4 py-3 text-right">
                <button
                  v-if="v.placement_status === 'REPAIRING'"
                  type="button"
                  class="rounded-md bg-slate-900 px-3 py-2 text-xs font-bold text-white hover:bg-slate-800"
                  @click="sendToPit(v)"
                >
                  피트 입고
                </button>
                <span v-else class="text-xs text-slate-400">{{ placementLabel(v.placement_status) }}</span>
              </td>
            </tr>
            <tr v-if="!vehicles.length">
              <td colspan="4" class="px-4 py-12 text-center text-sm text-slate-400">조건에 맞는 차량이 없습니다.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <div
      v-if="selectedVehicle"
      class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-3 backdrop-blur-sm sm:p-6"
      @click.self="closeVehicleDetail"
    >
      <section class="flex max-h-[92vh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
        <header class="flex flex-col gap-3 border-b border-slate-200 px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div class="min-w-0">
            <p class="text-xs font-bold text-slate-500">차량 상세정보</p>
            <div class="mt-1 flex flex-wrap items-center gap-2">
              <h3 class="text-2xl font-black text-slate-950">{{ selectedVehicle.vehicle_number }}</h3>
              <span class="rounded bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-600">
                {{ selectedVehicle.company_name || selectedVehicle.company_code || '-' }}
              </span>
              <span :class="statusBadgeClass(selectedVehicle.placement_status)">
                {{ selectedVehicle.placement_status_display || placementLabel(selectedVehicle.placement_status) }}
              </span>
            </div>
          </div>
          <button
            type="button"
            class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50"
            @click="closeVehicleDetail"
          >
            닫기
          </button>
        </header>

        <div class="grid min-h-0 flex-1 overflow-auto lg:grid-cols-[360px_minmax(0,1fr)]">
          <aside class="border-b border-slate-200 bg-slate-50/70 p-5 lg:border-b-0 lg:border-r">
            <h4 class="text-sm font-bold text-slate-950">기본 정보</h4>
            <dl class="mt-4 space-y-3 text-sm">
              <div class="grid grid-cols-[96px_minmax(0,1fr)] gap-3">
                <dt class="font-semibold text-slate-500">차량번호</dt>
                <dd class="font-bold text-slate-950">{{ selectedVehicle.vehicle_number }}</dd>
              </div>
              <div class="grid grid-cols-[96px_minmax(0,1fr)] gap-3">
                <dt class="font-semibold text-slate-500">끝 4자리</dt>
                <dd class="text-slate-800">{{ selectedVehicle.vehicle_number_short || '-' }}</dd>
              </div>
              <div class="grid grid-cols-[96px_minmax(0,1fr)] gap-3">
                <dt class="font-semibold text-slate-500">모델</dt>
                <dd class="text-slate-800">{{ selectedVehicle.model || '-' }}</dd>
              </div>
              <div class="grid grid-cols-[96px_minmax(0,1fr)] gap-3">
                <dt class="font-semibold text-slate-500">VIN/TID</dt>
                <dd class="break-all text-slate-800">{{ selectedVehicle.vin_tid || '-' }}</dd>
              </div>
              <div class="grid grid-cols-[96px_minmax(0,1fr)] gap-3">
                <dt class="font-semibold text-slate-500">출고일</dt>
                <dd class="text-slate-800">{{ selectedVehicle.shipped_at || '-' }}</dd>
              </div>
              <div class="grid grid-cols-[96px_minmax(0,1fr)] gap-3">
                <dt class="font-semibold text-slate-500">플릿</dt>
                <dd class="text-slate-800">{{ selectedVehicle.fleet || '미분류' }}</dd>
              </div>
              <div class="grid grid-cols-[96px_minmax(0,1fr)] gap-3">
                <dt class="font-semibold text-slate-500">운전자</dt>
                <dd class="text-slate-800">{{ selectedVehicle.driver || '-' }}</dd>
              </div>
              <div class="grid grid-cols-[96px_minmax(0,1fr)] gap-3">
                <dt class="font-semibold text-slate-500">회선</dt>
                <dd class="text-slate-800">{{ selectedVehicle.hgi || '-' }}</dd>
              </div>
              <div class="grid grid-cols-[96px_minmax(0,1fr)] gap-3">
                <dt class="font-semibold text-slate-500">운영 구분</dt>
                <dd class="text-slate-800">{{ selectedVehicle.operation_type_display || selectedVehicle.operation_type || '-' }}</dd>
              </div>
              <div class="grid grid-cols-[96px_minmax(0,1fr)] gap-3">
                <dt class="font-semibold text-slate-500">비고</dt>
                <dd class="whitespace-pre-wrap text-slate-800">{{ selectedVehicle.notes || '-' }}</dd>
              </div>
            </dl>
          </aside>

          <main class="p-5">
            <section class="mb-5 overflow-hidden rounded-xl border border-slate-200 bg-white">
              <div class="flex flex-col gap-3 border-b border-slate-200 bg-slate-50/80 px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <h4 class="text-lg font-black text-slate-950">실시간 위치와 차량 상태</h4>
                  <p class="mt-1 text-sm text-slate-500">
                    EV Dashboard 최신 텔레메트리를 차량번호, 뒤 4자리, TID 기준으로 매칭합니다.
                  </p>
                </div>
                <div class="flex flex-wrap items-center gap-2">
                  <span v-if="evdashSummary" :class="evdashOnlineBadgeClass">
                    {{ evdashSummary.online_label }}
                  </span>
                  <button
                    type="button"
                    class="rounded-lg border border-slate-300 px-3 py-2 text-xs font-bold text-slate-700 hover:bg-white disabled:opacity-50"
                    :disabled="evdashLoading"
                    @click="loadEvdash(selectedVehicle)"
                  >
                    {{ evdashLoading ? '조회 중' : '새로고침' }}
                  </button>
                </div>
              </div>

              <div v-if="evdashLoading" class="px-4 py-10 text-center text-sm font-semibold text-slate-500">
                EV Dashboard 차량 상태를 불러오고 있습니다.
              </div>
              <div v-else-if="evdashError" class="m-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
                {{ evdashError }}
              </div>
              <div v-else-if="vehicleEvdash && !vehicleEvdash.matched" class="m-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800">
                {{ vehicleEvdash.detail || 'EV Dashboard에서 일치하는 차량을 찾지 못했습니다.' }}
              </div>
              <div v-else-if="vehicleEvdash?.matched" class="grid gap-4 p-4 xl:grid-cols-[minmax(360px,1.15fr)_minmax(320px,0.85fr)]">
                <div class="overflow-hidden rounded-xl border border-slate-200 bg-slate-100">
                  <div
                    v-if="evdashHasLocation"
                    :id="evdashMapId"
                    ref="evdashMapEl"
                    class="h-[360px] w-full"
                  />
                  <div v-else class="flex h-[360px] flex-col items-center justify-center gap-2 px-6 text-center">
                    <p class="text-lg font-black text-slate-800">수신된 좌표가 없습니다.</p>
                    <p class="max-w-sm text-sm leading-6 text-slate-500">
                      차량 상태는 수신됐지만 최신 텔레메트리에 위도/경도 값이 없어 지도 위치를 표시할 수 없습니다.
                    </p>
                  </div>
                  <div class="border-t border-slate-200 bg-white px-4 py-2 text-xs text-slate-500">
                    <span v-if="evdashHasLocation">
                      위도 {{ evdashLocation.latitude?.toFixed?.(6) || evdashLocation.latitude }},
                      경도 {{ evdashLocation.longitude?.toFixed?.(6) || evdashLocation.longitude }}
                    </span>
                    <span v-else>지도 좌표 미수신</span>
                    <span v-if="evdashSummary?.observed_at" class="ml-2">
                      · 최종 수신 {{ formatEvdashTime(evdashSummary.observed_at) }}
                      <template v-if="evdashSummary.age_seconds != null">
                        ({{ formatAge(evdashSummary.age_seconds) }} 전)
                      </template>
                    </span>
                  </div>
                </div>

                <div class="space-y-4">
                  <div class="grid grid-cols-2 gap-2 sm:grid-cols-4 xl:grid-cols-2">
                    <div
                      v-for="card in evdashStatusCards"
                      :key="card.key"
                      class="min-w-0 rounded-lg border border-slate-200 bg-slate-50 px-3 py-3"
                    >
                      <p class="truncate text-[11px] font-bold text-slate-500">{{ card.label }}</p>
                      <p class="mt-1 min-w-0 break-words text-[15px] font-black leading-snug text-slate-950" :title="String(card.value || '-')">
                        {{ card.value }}
                      </p>
                    </div>
                  </div>

                  <dl class="rounded-xl border border-slate-200 bg-white text-sm">
                    <div class="grid grid-cols-[110px_minmax(0,1fr)] gap-3 border-b border-slate-100 px-4 py-3">
                      <dt class="font-semibold text-slate-500">매칭</dt>
                      <dd class="min-w-0 break-words font-bold text-slate-900">{{ vehicleEvdash.match_method || '-' }}</dd>
                    </div>
                    <div class="grid grid-cols-[110px_minmax(0,1fr)] gap-3 border-b border-slate-100 px-4 py-3">
                      <dt class="font-semibold text-slate-500">EV 차량번호</dt>
                      <dd class="min-w-0 break-words font-bold text-slate-900">{{ evdashVehicle?.plate_number || '-' }}</dd>
                    </div>
                    <div class="grid grid-cols-[110px_minmax(0,1fr)] gap-3 border-b border-slate-100 px-4 py-3">
                      <dt class="font-semibold text-slate-500">TID</dt>
                      <dd class="min-w-0 break-all text-slate-800">{{ evdashVehicle?.tid || '-' }}</dd>
                    </div>
                    <div class="grid grid-cols-[110px_minmax(0,1fr)] gap-3 border-b border-slate-100 px-4 py-3">
                      <dt class="font-semibold text-slate-500">차량 별칭</dt>
                      <dd class="min-w-0 break-words text-slate-800">{{ evdashVehicle?.nickname || '-' }}</dd>
                    </div>
                    <div class="grid grid-cols-[110px_minmax(0,1fr)] gap-3 border-b border-slate-100 px-4 py-3">
                      <dt class="font-semibold text-slate-500">소속 플릿</dt>
                      <dd class="min-w-0 break-words text-slate-800">{{ evdashVehicle?.fleet_name || '-' }}</dd>
                    </div>
                    <div class="grid grid-cols-[110px_minmax(0,1fr)] gap-3 px-4 py-3">
                      <dt class="font-semibold text-slate-500">주행거리</dt>
                      <dd class="min-w-0 break-words text-slate-800">{{ formatTelemetryValue(evdashLatest?.odometer, 'km') }}</dd>
                    </div>
                  </dl>
                </div>
              </div>
              <div v-else class="px-4 py-10 text-center text-sm font-semibold text-slate-400">
                차량을 열면 실시간 위치와 상태를 조회합니다.
              </div>
            </section>

            <div class="flex flex-col gap-3 border-b border-slate-200 pb-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <h4 class="text-lg font-black text-slate-950">자동차등록증</h4>
                <p class="mt-1 text-sm text-slate-500">PDF, JPG, PNG, WEBP 파일을 20MB 이하로 업로드할 수 있습니다.</p>
              </div>
              <div class="flex flex-wrap gap-2">
                <input
                  ref="registrationFileInput"
                  type="file"
                  class="hidden"
                  accept=".pdf,.jpg,.jpeg,.png,.webp,application/pdf,image/*"
                  @change="handleCertificateUpload"
                />
                <button
                  type="button"
                  class="rounded-lg bg-slate-950 px-4 py-2 text-sm font-bold text-white hover:bg-slate-800 disabled:opacity-50"
                  :disabled="certificateUploading"
                  @click="triggerCertificateInput"
                >
                  {{ selectedVehicle.registration_certificate_url ? '등록증 교체' : '등록증 업로드' }}
                </button>
                <a
                  v-if="selectedVehicle.registration_certificate_url"
                  :href="selectedVehicle.registration_certificate_url"
                  target="_blank"
                  rel="noreferrer"
                  class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50"
                >
                  새 창에서 보기
                </a>
                <button
                  v-if="selectedVehicle.registration_certificate_url"
                  type="button"
                  class="rounded-lg border border-red-200 px-4 py-2 text-sm font-bold text-red-600 hover:bg-red-50 disabled:opacity-50"
                  :disabled="certificateUploading"
                  @click="removeCertificate"
                >
                  삭제
                </button>
              </div>
            </div>

            <div v-if="certificateError" class="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
              {{ certificateError }}
            </div>
            <div v-if="certificateUploading" class="mt-4 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm font-semibold text-blue-700">
              등록증을 업로드하는 중입니다.
            </div>

            <div class="mt-4 overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
              <div
                v-if="!selectedVehicle.registration_certificate_url"
                class="flex min-h-[420px] flex-col items-center justify-center gap-3 px-6 py-12 text-center"
              >
                <div class="rounded-full bg-white px-5 py-4 text-sm font-black text-slate-700 shadow-sm">DOC</div>
                <p class="text-lg font-black text-slate-900">등록된 자동차등록증이 없습니다.</p>
                <p class="max-w-md text-sm leading-6 text-slate-500">상단의 등록증 업로드 버튼을 눌러 차량별 자동차등록증을 저장하세요.</p>
              </div>
              <iframe
                v-else-if="certificateIsPdf"
                :src="selectedVehicle.registration_certificate_url"
                class="h-[64vh] min-h-[520px] w-full bg-white"
                title="자동차등록증 PDF 미리보기"
              />
              <div v-else class="flex max-h-[64vh] min-h-[520px] items-center justify-center overflow-auto bg-slate-100 p-4">
                <img
                  :src="selectedVehicle.registration_certificate_url"
                  :alt="`${selectedVehicle.vehicle_number} 자동차등록증`"
                  class="max-h-full max-w-full rounded-lg bg-white object-contain shadow-sm"
                />
              </div>
            </div>

            <p v-if="selectedVehicle.registration_certificate_uploaded_at" class="mt-3 text-xs text-slate-500">
              업로드 시각: {{ formatDateTime(selectedVehicle.registration_certificate_uploaded_at) }}
              <span v-if="selectedVehicle.registration_certificate_file_name">
                · {{ selectedVehicle.registration_certificate_file_name }}
              </span>
            </p>
          </main>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  createPitRecord,
  fetchPitRecords,
  fetchVehicles,
  fetchVehicleStats,
  fetchVehicleEvdash,
  deleteVehicleRegistrationCertificate,
  updateVehicle,
  uploadVehicleRegistrationCertificate,
} from '@/api/vehicle'
import { loadVWorld } from '@/utils/vworld'

const props = defineProps({
  companyCode: {
    type: String,
    default: '',
  },
})

const vehicles = ref([])
const stats = ref({ total: 0, by_category: {}, by_fleet: {} })
const search = ref('')
const activeCategory = ref('')
const activeFleet = ref('')
const selectedVehicle = ref(null)
const vehicleEvdash = ref(null)
const evdashLoading = ref(false)
const evdashError = ref('')
const evdashMapEl = ref(null)
const evdashMapId = `vehicle-evdash-map-${Math.random().toString(36).slice(2, 9)}`
const registrationFileInput = ref(null)
const certificateUploading = ref(false)
const certificateError = ref('')
let debounceId = null
let evdashMap = null
let evdashOl = null
let evdashMarkerLayer = null

const FLEET_OPTIONS = ['', '서비스부문', '물류부문', 'DSV', '천하', '유한', '개인', '쿠팡', '매각', 'A/S']

const categoryDefs = [
  { code: '', label: '전체', description: '전체 차량' },
  { code: 'DIRECT', label: '직영', description: '서비스/물류/DSV', fleets: ['서비스부문', '물류부문', 'DSV'] },
  { code: 'REPAIRING', label: '수리/대기', description: '피트 입고 대상' },
  { code: 'SUBSCRIPTION', label: '구독', description: '천하/유한/개인/쿠팡', fleets: ['천하', '유한', '개인', '쿠팡'] },
  { code: 'SALE', label: '매각', description: '매각 차량' },
  { code: 'IDLE', label: '유휴', description: '배치 전' },
  { code: 'NOT_SHIPPED', label: '미출고', description: '출고 대기' },
]

const summaryCards = computed(() => categoryDefs)
const countFor = (code) => code ? (stats.value.by_category?.[code] ?? 0) : (stats.value.total ?? 0)

const activeCategoryLabel = computed(() => {
  const found = categoryDefs.find((item) => item.code === activeCategory.value)
  if (!found || !found.code) return '전체'
  return activeFleet.value ? `${found.label} / ${activeFleet.value}` : found.label
})

const subFleets = computed(() => {
  const found = categoryDefs.find((item) => item.code === activeCategory.value)
  return found?.fleets || []
})

const placementSelectClass = (status) => ({
  OPERATING: 'border-emerald-300 bg-emerald-50 text-emerald-700',
  REPAIRING: 'border-amber-300 bg-amber-50 text-amber-700',
  IDLE: 'border-slate-300 bg-slate-50 text-slate-600',
  NOT_SHIPPED: 'border-zinc-300 bg-zinc-50 text-zinc-600',
}[status] || 'border-slate-300 bg-white')

const placementLabel = (status) => ({
  OPERATING: '운영중',
  REPAIRING: '피트 가능',
  IDLE: '유휴',
  NOT_SHIPPED: '미출고',
}[status] || '-')

const statusBadgeClass = (status) => ({
  OPERATING: 'rounded bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-700',
  REPAIRING: 'rounded bg-amber-50 px-2.5 py-1 text-xs font-bold text-amber-700',
  IDLE: 'rounded bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-600',
  NOT_SHIPPED: 'rounded bg-zinc-100 px-2.5 py-1 text-xs font-bold text-zinc-600',
}[status] || 'rounded bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-600')

const certificateIsPdf = computed(() => {
  const url = selectedVehicle.value?.registration_certificate_url || ''
  return url.split('?')[0].toLowerCase().endsWith('.pdf')
})

const evdashVehicle = computed(() => vehicleEvdash.value?.vehicle || null)
const evdashLatest = computed(() => vehicleEvdash.value?.latest || null)
const evdashLocation = computed(() => vehicleEvdash.value?.location || {})
const evdashSummary = computed(() => vehicleEvdash.value?.summary || null)
const evdashStatusCards = computed(() => vehicleEvdash.value?.status_cards || [])
const evdashHasLocation = computed(() => Boolean(evdashLocation.value?.has_location))
const evdashOnlineBadgeClass = computed(() => {
  const tone = evdashSummary.value?.tone
  if (tone === 'green') return 'rounded-full bg-emerald-50 px-3 py-1 text-xs font-black text-emerald-700'
  if (tone === 'amber') return 'rounded-full bg-amber-50 px-3 py-1 text-xs font-black text-amber-700'
  if (tone === 'red') return 'rounded-full bg-red-50 px-3 py-1 text-xs font-black text-red-700'
  return 'rounded-full bg-slate-100 px-3 py-1 text-xs font-black text-slate-600'
})

const formatDateTime = (value) => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('ko-KR')
}

const formatEvdashTime = (value) => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('ko-KR', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const formatAge = (seconds) => {
  const value = Number(seconds)
  if (!Number.isFinite(value)) return '-'
  if (value < 60) return `${Math.max(0, Math.round(value))}초`
  if (value < 3600) return `${Math.round(value / 60)}분`
  if (value < 86400) return `${Math.round(value / 3600)}시간`
  return `${Math.round(value / 86400)}일`
}

const formatTelemetryValue = (value, suffix = '') => {
  if (value === null || value === undefined || value === '') return '-'
  const number = Number(value)
  if (!Number.isFinite(number)) return String(value)
  return `${number.toLocaleString('ko-KR', { maximumFractionDigits: 1 })}${suffix}`
}

const fleetToCategory = (fleet) => {
  if (['서비스부문', '물류부문', 'DSV'].includes(fleet)) return 'DIRECT'
  if (['천하', '유한', '개인', '쿠팡'].includes(fleet)) return 'SUBSCRIPTION'
  if (fleet === '매각') return 'SALE'
  return ''
}

const onCategory = (code) => {
  activeCategory.value = code
  activeFleet.value = ''
  reload()
}

const mergeVehicle = (updated) => {
  const index = vehicles.value.findIndex((item) => item.id === updated.id)
  if (index >= 0) {
    vehicles.value[index] = { ...vehicles.value[index], ...updated }
  }
  if (selectedVehicle.value?.id === updated.id) {
    selectedVehicle.value = { ...selectedVehicle.value, ...updated }
  }
}

const resetEvdashMap = () => {
  try {
    evdashMap?.setTarget?.(null)
  } catch {
    // ignore VWorld cleanup errors
  }
  evdashMap = null
  evdashOl = null
  evdashMarkerLayer = null
}

const ensureEvdashMap = async () => {
  if (!evdashHasLocation.value || !evdashMapEl.value) return
  const { vw, ol } = await loadVWorld()
  evdashOl = ol
  if (!evdashMap) {
    evdashMap = new vw.ol3.Map(evdashMapId, {
      basemapType: vw.ol3.BasemapType.GRAPHIC,
      controlDensity: vw.ol3.DensityType.EMPTY,
      interactionDensity: vw.ol3.DensityType.BASIC,
      controlsAutoArrange: true,
      homePosition: vw.ol3.CameraPosition,
      initPosition: vw.ol3.CameraPosition,
    })
    evdashMarkerLayer = new ol.layer.Vector({ source: new ol.source.Vector(), zIndex: 10 })
    evdashMap.addLayer(evdashMarkerLayer)
  }
  const lon = Number(evdashLocation.value.longitude)
  const lat = Number(evdashLocation.value.latitude)
  if (!Number.isFinite(lon) || !Number.isFinite(lat)) return
  const coord = ol.proj.fromLonLat([lon, lat])
  const source = evdashMarkerLayer.getSource()
  source.clear()
  const marker = new ol.Feature({ geometry: new ol.geom.Point(coord) })
  marker.setStyle(new ol.style.Style({
    image: new ol.style.Circle({
      radius: 9,
      fill: new ol.style.Fill({ color: '#dc2626' }),
      stroke: new ol.style.Stroke({ color: '#ffffff', width: 3 }),
    }),
  }))
  source.addFeature(marker)
  evdashMap.updateSize()
  evdashMap.getView().setCenter(coord)
  evdashMap.getView().setZoom(16)
  requestAnimationFrame(() => evdashMap?.updateSize?.())
}

const loadEvdash = async (vehicle) => {
  if (!vehicle?.id) return
  evdashLoading.value = true
  evdashError.value = ''
  vehicleEvdash.value = null
  resetEvdashMap()
  try {
    const response = await fetchVehicleEvdash(vehicle.id)
    vehicleEvdash.value = response.data || null
    if (vehicleEvdash.value?.detail && !vehicleEvdash.value?.matched) {
      evdashError.value = ''
    }
    await nextTick()
    await ensureEvdashMap()
  } catch (error) {
    evdashError.value = error.response?.data?.detail || 'EV Dashboard 차량 상태 조회에 실패했습니다.'
  } finally {
    evdashLoading.value = false
  }
}

const openVehicleDetail = (vehicle) => {
  selectedVehicle.value = { ...vehicle }
  certificateError.value = ''
  loadEvdash(vehicle)
}

const handleVehicleDetailDelegatedClick = (event) => {
  const trigger = event.target?.closest?.('[data-vehicle-detail-id]')
  if (!trigger) return
  const id = String(trigger.dataset.vehicleDetailId || '')
  if (!id) return
  const vehicle = vehicles.value.find((item) => String(item.id) === id)
  if (vehicle) openVehicleDetail(vehicle)
}

const closeVehicleDetail = () => {
  selectedVehicle.value = null
  vehicleEvdash.value = null
  evdashError.value = ''
  evdashLoading.value = false
  resetEvdashMap()
  certificateError.value = ''
}

const triggerCertificateInput = () => {
  registrationFileInput.value?.click()
}

const handleCertificateUpload = async (event) => {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file || !selectedVehicle.value) return
  certificateUploading.value = true
  certificateError.value = ''
  try {
    const response = await uploadVehicleRegistrationCertificate(selectedVehicle.value.id, file)
    mergeVehicle(response.data)
  } catch (error) {
    certificateError.value = error.response?.data?.detail || '자동차등록증 업로드에 실패했습니다.'
  } finally {
    certificateUploading.value = false
  }
}

const removeCertificate = async () => {
  if (!selectedVehicle.value) return
  if (!confirm(`${selectedVehicle.value.vehicle_number} 자동차등록증을 삭제하시겠습니까?`)) return
  certificateUploading.value = true
  certificateError.value = ''
  try {
    const response = await deleteVehicleRegistrationCertificate(selectedVehicle.value.id)
    mergeVehicle(response.data)
  } catch (error) {
    certificateError.value = error.response?.data?.detail || '자동차등록증 삭제에 실패했습니다.'
  } finally {
    certificateUploading.value = false
  }
}

const updateFleet = async (vehicle, newFleet) => {
  try {
    await updateVehicle(vehicle.id, { fleet: newFleet })
    if (vehicle.placement_status === 'OPERATING') {
      const nextCategory = fleetToCategory(newFleet)
      if (nextCategory && nextCategory !== activeCategory.value) {
        onCategory(nextCategory)
        return
      }
    }
    await reload()
  } catch (error) {
    alert(`플릿 변경에 실패했습니다: ${error.response?.data?.detail || error.message}`)
  }
}

const updatePlacement = async (vehicle, newStatus) => {
  try {
    await updateVehicle(vehicle.id, { placement_status: newStatus })
    if (newStatus === 'REPAIRING') onCategory('REPAIRING')
    else if (newStatus === 'IDLE') onCategory('IDLE')
    else if (newStatus === 'NOT_SHIPPED') onCategory('NOT_SHIPPED')
    else if (newStatus === 'OPERATING') onCategory(fleetToCategory(vehicle.fleet) || '')
    else await reload()
  } catch (error) {
    alert(`배치 상태 변경에 실패했습니다: ${error.response?.data?.detail || error.message}`)
  }
}

const sendToPit = async (vehicle) => {
  if (!confirm(`${vehicle.vehicle_number} 차량을 피트 차량현황에 입고 등록하시겠습니까?`)) return
  try {
    const existing = await fetchPitRecords({
      company: vehicle.company_code,
      vehicle_number_short: vehicle.vehicle_number_short,
      in_pit: 'true',
    }).catch(() => ({ data: { results: [] } }))

    if ((existing.data?.results || existing.data || []).length > 0) {
      alert('이미 피트에 입고된 차량입니다.')
      return
    }

    await createPitRecord({
      company: vehicle.company,
      vehicle: vehicle.id,
      vehicle_number_short: vehicle.vehicle_number_short,
      in_date: new Date().toISOString().slice(0, 10),
      reason: 'REPAIR',
      note: `${vehicle.vehicle_number} (${vehicle.fleet || '미분류'}) 수리 입고`,
    })
    alert(`${vehicle.vehicle_number} 차량을 피트로 입고했습니다.`)
    await reload()
  } catch (error) {
    alert(`피트 입고 처리에 실패했습니다: ${error.response?.data?.detail || error.message}`)
  }
}

const reload = async () => {
  const params = {}
  if (props.companyCode) params.company = props.companyCode
  if (search.value) params.search = search.value
  if (activeCategory.value) params.category = activeCategory.value
  if (activeFleet.value) params.fleet = activeFleet.value
  try {
    const [vehiclesResponse, statsResponse] = await Promise.all([
      fetchVehicles(params),
      fetchVehicleStats(props.companyCode ? { company: props.companyCode } : {}),
    ])
    vehicles.value = vehiclesResponse.data?.results || vehiclesResponse.data || []
    stats.value = statsResponse.data || { total: 0, by_category: {}, by_fleet: {} }
  } catch {
    vehicles.value = []
    stats.value = { total: 0, by_category: {}, by_fleet: {} }
  }
}

const debouncedReload = () => {
  clearTimeout(debounceId)
  debounceId = setTimeout(reload, 300)
}

onMounted(() => {
  document.addEventListener('click', handleVehicleDetailDelegatedClick)
  reload()
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleVehicleDetailDelegatedClick)
  clearTimeout(debounceId)
  resetEvdashMap()
})
</script>
