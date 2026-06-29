<template>
  <LegalTextPage
    title="CLEVER 관리자 회원 서비스 이용약관"
    description="웹 운영관리 페이지에서 회사 관리자 회원에게 적용되는 이용약관입니다."
    :text="adminTermsText"
    :version="LEGAL_DOCUMENT_VERSION"
    :updated-at="LEGAL_DOCUMENT_UPDATED_AT"
  />
</template>

<script setup>
import LegalTextPage from '@/components/legal/LegalTextPage.vue'
import {
  LEGAL_DOCUMENT_UPDATED_AT,
  LEGAL_DOCUMENT_VERSION,
  adminTermsText,
} from '@/data/legalDocuments'
</script>
