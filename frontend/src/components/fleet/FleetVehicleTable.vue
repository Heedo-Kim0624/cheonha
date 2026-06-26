<template>
  <div class="table-wrap">
    <table class="fleet-table">
      <thead>
        <tr>
          <th>차량번호</th>
          <th>운영 상태</th>
          <th>호기번호</th>
          <th>차대번호</th>
          <th>모델</th>
          <th>구독</th>
          <th>반납/수리</th>
          <th>보험</th>
          <th>사고</th>
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
          <td class="strong">{{ group.plate }}</td>
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
          <td>{{ currentRecord(group)?.unitNumber || '-' }}</td>
          <td>{{ currentRecord(group)?.vin || '-' }}</td>
          <td>{{ currentRecord(group)?.model || '-' }}</td>
          <td>{{ group.subscriptions?.length || 0 }}건</td>
          <td>{{ group.returns?.length || 0 }}건</td>
          <td>{{ group.insurances?.length || 0 }}건</td>
          <td>{{ group.accidents?.length || 0 }}건</td>
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
  if ((group?.subscriptions || []).some((item) => item.status?.includes('구독'))) return '구독'
  return '유휴'
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
  min-width: 980px;
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
}

.fleet-table tr:hover td,
.fleet-table tr.selected td {
  background: #f6f8ec;
}

.fleet-table .strong {
  font-weight: 900;
  color: #1f2937;
}

.status-select {
  min-width: 112px;
  padding: 7px 9px;
}

.empty-cell {
  padding: 42px 12px;
  color: #9ca3af;
  text-align: center;
}
</style>
