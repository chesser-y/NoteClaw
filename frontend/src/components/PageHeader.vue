<script setup lang="ts">
defineProps<{
  eyebrow?: string
  title: string
  description?: string
}>()
</script>

<template>
  <div class="mb-8">
    <div v-if="eyebrow" class="mb-3 text-xs uppercase tracking-[0.18em] text-[#8f9996]">
      {{ eyebrow }}
    </div>
    <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <h1 class="section-title text-white">{{ title }}</h1>
        <p v-if="description" class="mt-3 max-w-3xl leading-7 text-[#9aa3a0]">
          {{ description }}
        </p>
      </div>
      <div class="accent-line"></div>
    </div>
  </div>
</template>
