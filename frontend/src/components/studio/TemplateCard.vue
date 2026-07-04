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
    :class="active ? 'border-[#4f46e5] shadow-[0_0_0_3px_rgba(79,70,229,0.15)]' : ''"
  >
    <div
      class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg"
      :class="active ? 'bg-[#4f46e5] text-white' : 'bg-[#eef2ff] text-[#4f46e5]'"
    >
      <component :is="icon" :size="18" />
    </div>
    <div class="min-w-0 flex-1">
      <div class="text-[15px] font-semibold text-[#111827]">{{ label }}</div>
      <div class="mt-0.5 text-xs text-[#6b7280]">{{ sub }}</div>
    </div>
  </button>
</template>
