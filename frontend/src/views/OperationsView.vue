<template>
  <AppLayout>
    <div class="w-full min-w-0 max-w-full overflow-x-hidden">
      <OperationReportPanel :show-heading="false" :show-company-select="false" />
    </div>
  </AppLayout>
</template>

<script setup>
import AppLayout from '@/components/common/AppLayout.vue'
import OperationReportPanel from '@/components/operations/OperationReportPanel.vue'
</script>
