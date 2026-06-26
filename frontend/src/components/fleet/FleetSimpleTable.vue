<template>
  <div class="table-wrap">
    <table class="fleet-table">
      <thead>
        <tr>
          <th
            v-for="column in columns"
            :key="column.key"
            :class="{ right: column.align === 'right' }"
          >
            {{ column.label }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="!rows.length">
          <td class="empty-cell" :colspan="columns.length">{{ emptyText }}</td>
        </tr>
        <tr v-for="(row, rowIndex) in rows" v-else :key="row.id || rowIndex">
          <td
            v-for="column in columns"
            :key="column.key"
            :class="{ right: column.align === 'right' }"
          >
            {{ row[column.key] ?? '-' }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
defineProps({
  columns: { type: Array, required: true },
  rows: { type: Array, required: true },
  emptyText: { type: String, default: '데이터가 없습니다.' },
})
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

.fleet-table tr:hover td {
  background: #f6f8ec;
}

.fleet-table .right,
.fleet-table th.right {
  text-align: right;
  font-weight: 900;
  color: #1f2937;
}

.empty-cell {
  padding: 42px 12px;
  color: #9ca3af;
  text-align: center;
}
</style>
