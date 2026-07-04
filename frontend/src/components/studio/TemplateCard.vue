<script setup lang="ts">
defineProps<{
  label: string
  sub: string
  icon: typeof import('lucide-vue-next').Sparkles
  active?: boolean
}>()
</script>

<template>
  <button
    type="button"
    class="card card-hover flex items-start gap-3 text-left transition"
    :class="active ? 'border-[#626be6] shadow-[0_0_0_3px_rgba(98,107,230,0.22)]' : ''"
  >
    <div
      class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg"
      :class="active ? 'bg-[#626be6] text-white' : 'bg-[rgba(98, 107, 230, 0.16)] text-[#626be6]'"
    >
      <component :is="icon" :size="18" />
    </div>
    <div class="min-w-0 flex-1">
      <div class="text-[15px] font-semibold text-[#f0f1f2]">{{ label }}</div>
      <div class="mt-0.5 text-xs text-[#929399]">{{ sub }}</div>
    </div>
  </button>
</template>
