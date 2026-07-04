<script setup lang="ts">
import { onMounted, onUnmounted, watch } from 'vue'
import { X } from 'lucide-vue-next'

const props = withDefaults(
  defineProps<{
    open: boolean
    title?: string
    width?: string
  }>(),
  {
    title: '',
    width: '440px',
  },
)

const emit = defineEmits<{ close: [] }>()

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.open) {
    emit('close')
  }
}

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))

watch(
  () => props.open,
  (v) => {
    if (typeof document !== 'undefined') {
      document.body.style.overflow = v ? 'hidden' : ''
    }
  },
)
</script>

<template>
  <Teleport to="body">
    <template v-if="open">
      <div class="drawer-backdrop" @click="emit('close')"></div>
      <aside class="drawer-panel" :style="{ width }" role="dialog" aria-modal="true">
        <header class="flex items-center justify-between border-b border-[#24262a] px-5 py-4">
          <h2 class="text-sm font-semibold text-[#f0f1f2]">{{ title }}</h2>
          <button class="btn btn-ghost h-8 w-8 p-0" type="button" @click="emit('close')" aria-label="Close">
            <X :size="16" />
          </button>
        </header>
        <div class="min-h-0 flex-1 overflow-y-auto px-5 py-4">
          <slot />
        </div>
        <footer v-if="$slots.footer" class="border-t border-[#24262a] px-5 py-3">
          <slot name="footer" />
        </footer>
      </aside>
    </template>
  </Teleport>
</template>
