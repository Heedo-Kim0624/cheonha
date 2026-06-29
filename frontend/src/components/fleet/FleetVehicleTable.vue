<template>
  <div class="table-wrap">
    <table class="fleet-table">
      <thead>
        <tr>
          <th>차량번호</th>
          <th>운영 상태</th>
          <th>호기번호</th>
          <th>현재 구독자</th>
          <th>TS검사</th>
          <th>보험료 일정</th>
          <th>서류 상태</th>
          <th>차대번호</th>
          <th>모델</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="!groups.length">
          <td class="empty-cell" colspan="9">차량 데이터가 없습니다.</td>
        </tr>
        <tr
          v-for="group in groups"
          v-else
          :key="group.plate"
          :class="{ selected: selectedPlate === group.plate }"
          @click="$emit('select', group)"
        >
          <td>
            <strong>{{ group.plate }}</strong>
            <small v-if="currentRecord(group)?.owner">{{ currentRecord(group)?.owner }}</small>
          </td>
          <td>
            <select
              class="status-select"
              :value="fleetState(group)"
              @click.stop
              @change="$emit('status', group, $event.target.value)"
            >
              <option v-for="status in statusChoices" :key="status" :value="status">
                {{ status }}
              </option>
            </select>
          </td>
          <td>{{ currentRecord(group)?.unitNumber || currentRecord(group)?.hgi || '-' }}</td>
          <td>
            <strong>{{ activeSubscription(group)?.customer || '미구독' }}</strong>
            <small>{{ activeSubscription(group)?.status || '-' }}</small>
          </td>
          <td>
            <span :class="['pill', inspectionTone(group)]">{{ inspectionText(group) }}</span>
          </td>
          <td>
            <span :class="['pill', insuranceTone(group)]">{{ insuranceText(group) }}</span>
          </td>
          <td>
            <span :class="['pill', docsReady(group) ? 'ok' : 'warn']">{{ docsText(group) }}</span>
          </td>
          <td>{{ shortVin(currentRecord(group)?.vin) }}</td>
          <td>{{ currentRecord(group)?.model || '-' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
defineProps({
  groups: { type: Array, required: true },
  selectedPlate: { type: String, default: '' },
  statusChoices: { type: Array, required: true },
})

defineEmits(['select', 'status'])

function currentRecord(group) {
  const records = group?.records || []
  return records.find((record) => !record.end) || records[records.length - 1] || null
}

function fleetState(group) {
  const record = currentRecord(group)
  if (record?.status) return record.status
  if ((group?.subscriptions || []).some((item) => String(item.status || '').includes('구독'))) return '구독'
  return '유휴'
}

function activeSubscription(group) {
  const rows = group?.subscriptions || []
  return rows.find((item) => String(item.status || '').includes('구독'))
    || rows.find((item) => !String(item.status || '').includes('종료'))
    || null
}

function docsReady(group) {
  const types = new Set((group?.documents || []).map((doc) => doc.type || doc.documentType || doc.document_type))
  return types.has('registration_certificate') && types.has('insurance_application')
}

function docsText(group) {
  return docsReady(group) ? '완료' : '미비'
}

function latestInspection(group) {
  return [...(group?.inspections || [])]
    .sort((a, b) => String(a.scheduled || '').localeCompare(String(b.scheduled || '')))
    .at(-1) || null
}

function inspectionText(group) {
  const item = latestInspection(group)
  if (!item) return '미등록'
  return item.completed ? `완료 ${dateShort(item.completed)}` : `예정 ${dateShort(item.scheduled)}`
}

function inspectionTone(group) {
  const item = latestInspection(group)
  if (!item) return 'warn'
  if (item.completed) return 'ok'
  return isPast(item.scheduled) ? 'danger' : 'info'
}

function latestInsurance(group) {
  return [...(group?.insurances || [])]
    .sort((a, b) => String(a.end || '').localeCompare(String(b.end || '')))
    .at(-1) || null
}

function insuranceText(group) {
  const item = latestInsurance(group)
  if (!item) return '미등록'
  return `${item.status || '등록'} ${dateShort(item.end)}`
}

function insuranceTone(group) {
  const item = latestInsurance(group)
  if (!item) return 'warn'
  return isPast(item.end) ? 'danger' : 'ok'
}

function isPast(value) {
  if (!value) return false
  const parsed = new Date(String(value).slice(0, 10))
  if (Number.isNaN(parsed.getTime())) return false
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return parsed < today
}

function dateShort(value) {
  if (!value) return '-'
  const text = String(value).slice(0, 10)
  return text.replace(/-/g, '.')
}

function shortVin(value) {
  if (!value) return '-'
  const text = String(value)
  return text.length > 7 ? `...${text.slice(-7)}` : text
}
</script>

<style scoped>
.table-wrap {
  overflow: auto;
  border: 1px solid #e8edf5;
  border-radius: 12px;
}

.fleet-table {
  width: 100%;
  min-width: 1180px;
  border-collapse: collapse;
  font-size: 14px;
}

.fleet-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #101827;
  color: #fff;
  padding: 12px;
  text-align: left;
  white-space: nowrap;
}

.fleet-table td {
  border-right: 1px solid #edf1f7;
  border-bottom: 1px solid #edf1f7;
  padding: 11px 12px;
  color: #475467;
  white-space: nowrap;
  vertical-align: middle;
}

.fleet-table td strong,
.fleet-table td small {
  display: block;
}

.fleet-table td strong {
  color: #1f2937;
  font-weight: 900;
}

.fleet-table td small {
  margin-top: 3px;
  color: #8a94a6;
  font-size: 12px;
}

.fleet-table tr:hover td,
.fleet-table tr.selected td {
  background: #f6f8ec;
}

.status-select {
  min-width: 104px;
  padding: 7px 9px;
}

.pill {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  border-radius: 999px;
  padding: 4px 9px;
  font-size: 12px;
  font-weight: 900;
}

.pill.ok {
  background: #ecfdf3;
  color: #247a4d;
}

.pill.info {
  background: #eef4ff;
  color: #3554c8;
}

.pill.warn {
  background: #fff8e6;
  color: #9a6700;
}

.pill.danger {
  background: #fff1f0;
  color: #b42318;
}

.empty-cell {
  padding: 42px 12px;
  color: #9ca3af;
  text-align: center;
}
</style>
