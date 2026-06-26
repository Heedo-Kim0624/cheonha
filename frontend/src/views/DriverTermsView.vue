<template>
  <LegalTextPage
    title="CLEVER 배송원 회원 서비스 이용약관"
    description="기사용 앱 회원가입과 이용에 적용되는 배송원 회원 서비스 이용약관입니다."
    :text="driverTermsText"
    :version="LEGAL_DOCUMENT_VERSION"
    :updated-at="LEGAL_DOCUMENT_UPDATED_AT"
  />
</template>

<script setup>
import LegalTextPage from '@/components/legal/LegalTextPage.vue'
import {
  LEGAL_DOCUMENT_UPDATED_AT,
  LEGAL_DOCUMENT_VERSION,
  driverTermsText,
} from '@/data/legalDocuments'
</script>
