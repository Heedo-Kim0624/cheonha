<template>
  <section class="min-w-0 space-y-4 overflow-x-hidden">
    <div class="rounded-xl border border-slate-200 bg-white px-5 py-4">
      <div class="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div class="min-w-0">
          <h3 class="text-xl font-bold text-slate-950">피트</h3>
          <p class="mt-1 text-sm text-slate-500">입고, 출고, 배정, A/S 진행 상태를 확인하고 처리합니다.</p>
        </div>

        <nav class="flex flex-wrap gap-1 rounded-lg border border-slate-200 bg-slate-50 p-1" aria-label="피트 하위 탭">
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

    <PitVehicleStatusPanel
      v-if="resolvedSubtab === 'status' || !resolvedSubtab"
      :company-code="resolvedCompanyCode"
    />
    <VehicleCalendarPanel
      v-else-if="resolvedSubtab === 'calendar'"
      :company-code="resolvedCompanyCode"
    />
    <SubscriptionAssignmentPanel
      v-else-if="resolvedSubtab === 'assignment'"
      :company-code="resolvedCompanyCode"
    />
    <ASListPanel
      v-else-if="resolvedSubtab === 'as'"
      :company-code="resolvedCompanyCode"
    />
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import ASListPanel from './ASListPanel.vue'
import PitVehicleStatusPanel from './PitVehicleStatusPanel.vue'
import SubscriptionAssignmentPanel from './SubscriptionAssignmentPanel.vue'
import VehicleCalendarPanel from './VehicleCalendarPanel.vue'

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
    label: '피트 차량현황',
    description: '입고/출고와 상태 관리',
    to: { name: 'CleverPortalPitStatus' },
  },
  {
    key: 'calendar',
    label: '캘린더',
    description: '작업 일정 확인',
    to: { name: 'CleverPortalPitCalendar' },
  },
  {
    key: 'assignment',
    label: '차량 배정',
    description: '승인 요청 차량 배정',
    to: { name: 'CleverPortalPitAssignment' },
  },
  {
    key: 'as',
    label: 'A/S관리',
    description: 'A/S 상태와 메모 관리',
    to: { name: 'CleverPortalPitAS' },
  },
]

const resolvedSubtab = computed(() => props.subtab || 'status')
const resolvedCompanyCode = computed(() => props.companyCode || '')
</script>
