<template>
  <LegalTextPage
    title="제3자 정보제공 동의"
    description="배송 운영, 정산 검증, 서비스 개선 및 공동 연구를 위한 제3자 정보제공 안내입니다."
    :text="dataProcessingConsentText"
    :version="LEGAL_DOCUMENT_VERSION"
    :updated-at="LEGAL_DOCUMENT_UPDATED_AT"
  />
</template>

<script setup>
import LegalTextPage from '@/components/legal/LegalTextPage.vue'
import {
  LEGAL_DOCUMENT_UPDATED_AT,
  LEGAL_DOCUMENT_VERSION,
  dataProcessingConsentText,
} from '@/data/legalDocuments'
</script>
