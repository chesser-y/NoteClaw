<script setup lang="ts">
import { Sun, Moon } from 'lucide-vue-next'
import { useUiStore } from '../../stores/ui'

const ui = useUiStore()
</script>

<template>
  <button
    class="icon-button theme-toggle"
    type="button"
    :aria-label="ui.theme === 'dark' ? '切换到浅色' : 'Switch to dark'"
    :title="ui.theme === 'dark' ? '切换到浅色' : 'Switch to dark'"
    @click="ui.toggleTheme()"
  >
    <Sun v-if="ui.theme === 'dark'" :size="16" />
    <Moon v-else :size="16" />
  </button>
</template>

<style scoped>
.theme-toggle {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--muted);
}
.theme-toggle:hover {
  color: var(--text);
  background: var(--panel-2);
}
</style>
