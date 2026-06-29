<template>
  <section class="min-w-0 space-y-4 overflow-x-hidden">
    <div class="rounded-xl border border-slate-200 bg-white px-5 py-4">
      <div class="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div class="min-w-0">
          <h3 class="text-xl font-bold text-slate-950">차량관리</h3>
          <p class="mt-1 text-sm text-slate-500">차량 상태, 일정, 구독 요청을 확인하고 처리합니다.</p>
        </div>

        <nav class="flex flex-wrap gap-1 rounded-lg border border-slate-200 bg-slate-50 p-1" aria-label="차량관리 하위 탭">
          <RouterLink
            v-for="tab in subtabs"
            :key="tab.key"
            :to="tab.to"
            class="rounded-md px-4 py-2 text-sm font-semibold transition-colors"
            :class="resolvedSubtab === tab.key
              ? 'border border-slate-200 bg-white text-slate-950 shadow-sm'
              : 'text-slate-500 hover:bg-white hover:text-slate-900'"
            :title="tab.description"
          >
            {{ tab.label }}
          </RouterLink>
        </nav>
      </div>
    </div>

    <VehicleStatusPanel
      v-if="resolvedSubtab === 'status' || !resolvedSubtab"
      :company-code="resolvedCompanyCode"
    />
    <VehicleCalendarPanel
      v-else-if="resolvedSubtab === 'calendar'"
      :company-code="resolvedCompanyCode"
    />
    <SubscriptionListPanel
      v-else-if="resolvedSubtab === 'subscription'"
      :company-code="resolvedCompanyCode"
    />
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import SubscriptionListPanel from './SubscriptionListPanel.vue'
import VehicleCalendarPanel from './VehicleCalendarPanel.vue'
import VehicleStatusPanel from './VehicleStatusPanel.vue'

const props = defineProps({
  subtab: {
    type: String,
    default: 'status',
  },
  companyCode: {
    type: String,
    default: '',
  },
})

const subtabs = [
  {
    key: 'status',
    label: '전체 차량현황',
    description: '차량 상태 수정과 피트 입고 처리',
    to: { name: 'CleverPortalVehicleVehicles' },
  },
  {
    key: 'calendar',
    label: '캘린더',
    description: '차량 일정과 반납 일정 확인',
    to: { name: 'CleverPortalVehicleDashboard' },
  },
  {
    key: 'subscription',
    label: '구독관리',
    description: '구독 승인, 반려, 사진 검수',
    to: { name: 'CleverPortalVehicleSubscriptions' },
  },
]

const resolvedSubtab = computed(() => props.subtab || 'status')
const resolvedCompanyCode = computed(() => props.companyCode || '')
</script>
