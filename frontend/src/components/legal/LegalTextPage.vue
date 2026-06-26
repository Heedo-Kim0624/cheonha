<template>
  <div class="min-h-screen bg-[#f5f5f5] text-[#1a1a1a]">
    <main class="mx-auto max-w-5xl px-6 py-10 md:px-8">
      <header class="mb-8 rounded-lg border border-[#e5e5e5] bg-white p-6 md:p-8">
        <p class="mb-2 text-sm text-[#666]">문서 버전 {{ version }} · 반영일 {{ updatedAt }}</p>
        <h1 class="text-3xl font-bold">{{ title }}</h1>
        <p v-if="description" class="mt-4 leading-7 text-[#444]">{{ description }}</p>
      </header>

      <section class="rounded-lg border border-[#e5e5e5] bg-white p-6 md:p-8">
        <pre class="legal-document">{{ text }}</pre>
      </section>
    </main>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
  description: {
    type: String,
    default: '',
  },
  text: {
    type: String,
    required: true,
  },
  version: {
    type: String,
    required: true,
  },
  updatedAt: {
    type: String,
    required: true,
  },
})
</script>

<style scoped>
.legal-document {
  white-space: pre-wrap;
  word-break: keep-all;
  overflow-wrap: anywhere;
  font-family: inherit;
  font-size: 0.98rem;
  line-height: 1.85;
  color: #333;
}
</style>
