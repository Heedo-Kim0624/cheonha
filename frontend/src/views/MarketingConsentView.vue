<template>
  <LegalTextPage
    title="마케팅 및 이벤트 정보 수신 동의"
    description="서비스 안내, 이벤트 혜택, 공지 알림 수신에 관한 선택 동의입니다."
    :text="marketingConsentText"
    :version="LEGAL_DOCUMENT_VERSION"
    :updated-at="LEGAL_DOCUMENT_UPDATED_AT"
  />
</template>

<script setup>
import LegalTextPage from '@/components/legal/LegalTextPage.vue'
import {
  LEGAL_DOCUMENT_UPDATED_AT,
  LEGAL_DOCUMENT_VERSION,
  marketingConsentText,
} from '@/data/legalDocuments'
</script>
