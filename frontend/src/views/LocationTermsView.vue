<template>
  <LegalTextPage
    title="위치기반서비스 이용약관"
    description="CLEVER 위치기반서비스 이용과 개인위치정보 처리에 적용되는 약관입니다."
    :text="locationTermsText"
    :version="LEGAL_DOCUMENT_VERSION"
    :updated-at="LEGAL_DOCUMENT_UPDATED_AT"
  />
</template>

<script setup>
import LegalTextPage from '@/components/legal/LegalTextPage.vue'
import {
  LEGAL_DOCUMENT_UPDATED_AT,
  LEGAL_DOCUMENT_VERSION,
  locationTermsText,
} from '@/data/legalDocuments'
</script>
