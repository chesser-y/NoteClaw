<script setup lang="ts">
import { Inbox } from 'lucide-vue-next'

defineProps<{
  title: string
  description: string
}>()
</script>

<template>
  <div class="surface flex min-h-[220px] flex-col items-center justify-center p-8 text-center">
    <Inbox :size="28" class="mb-4 text-[#8f9996]" />
    <h3 class="mb-2 text-lg text-white">{{ title }}</h3>
    <p class="max-w-md text-sm leading-6 text-[#8f9996]">{{ description }}</p>
  </div>
</template>
