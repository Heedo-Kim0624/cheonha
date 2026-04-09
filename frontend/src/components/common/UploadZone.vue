<template>
  <div
    @drop="handleDrop"
    @dragover.prevent="isDragging = true"
    @dragleave="isDragging = false"
    :class="{
      'border-primary bg-primary-light': isDragging,
      'border-border bg-bg': !isDragging
    }"
    class="border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer"
  >
    <input
      ref="fileInput"
      type="file"
      class="hidden"
      @change="handleFileSelect"
      :accept="accept"
      :multiple="multiple"
    />

    <div
      @click="$refs.fileInput?.click()"
      class="space-y-2"
    >
      <div v-html="IconUpload" class="w-12 h-12 mx-auto text-primary"></div>
      <p class="text-text font-medium">파일을 드래그하거나 클릭하여 선택</p>
      <p class="text-sm text-text2">지원 형식: {{ accept }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { IconUpload } from '@/utils/icons'

const props = defineProps({
  accept: {
    type: String,
    default: '.xlsx,.xls'
  },
  multiple: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['files-selected'])

const isDragging = ref(false)
const fileInput = ref(null)

const handleFileSelect = (event) => {
  const files = event.target.files
  if (files) {
    emit('files-selected', Array.from(files))
    event.target.value = ''
  }
}

const handleDrop = (event) => {
  event.preventDefault()
  isDragging.value = false
  const files = event.dataTransfer.files
  if (files) {
    emit('files-selected', Array.from(files))
  }
}
</script>
