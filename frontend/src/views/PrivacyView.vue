<template>
  <LegalTextPage
    title="개인정보 처리방침"
    description="CLEVER 웹과 앱에서 처리하는 개인정보의 수집, 이용, 제공, 보관 및 파기 기준입니다."
    :text="privacyPolicyText"
    :version="LEGAL_DOCUMENT_VERSION"
    :updated-at="LEGAL_DOCUMENT_UPDATED_AT"
  />
</template>

<script setup>
import LegalTextPage from '@/components/legal/LegalTextPage.vue'
import {
  LEGAL_DOCUMENT_UPDATED_AT,
  LEGAL_DOCUMENT_VERSION,
  privacyPolicyText,
} from '@/data/legalDocuments'
</script>
