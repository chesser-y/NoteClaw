<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ChevronDown, MessageSquare, Command, Settings, Activity, Sun, Moon, Languages } from 'lucide-vue-next'
import { useUiStore } from '../../stores/ui'

const ui = useUiStore()
const router = useRouter()
const { t } = useI18n()
const open = ref(false)
const root = ref<HTMLElement | null>(null)

function toggle() {
  open.value = !open.value
}

function close() {
  open.value = false
}

function onClickOutside(e: MouseEvent) {
  if (!open.value) return
  if (root.value && !root.value.contains(e.target as Node)) close()
}

function go(path: string) {
  close()
  router.push(path)
}

function newChat() {
  close()
  router.push('/').then(() => ui.openAsk(null))
}

function openPalette() {
  close()
  ui.openPalette()
}

onMounted(() => document.addEventListener('mousedown', onClickOutside))
onUnmounted(() => document.removeEventListener('mousedown', onClickOutside))
</script>

<template>
  <div ref="root" class="workspace-menu-host">
    <button
      class="brand-trigger"
      type="button"
      :aria-expanded="open"
      @click="toggle"
    >
      <span class="brand-name">NoteClaw</span>
      <ChevronDown :size="12" class="brand-chevron" :class="{ open }" />
    </button>

    <div v-if="open" class="workspace-popover">
      <div class="popover-section">
        <button class="popover-item" type="button" @click="newChat">
          <MessageSquare :size="14" />
          <span>{{ t('action.new-chat') }}</span>
        </button>
        <button class="popover-item" type="button" @click="openPalette">
          <Command :size="14" />
          <span>{{ t('action.open-palette') }}</span>
          <span class="hint">⌘K</span>
        </button>
      </div>

      <div class="popover-divider"></div>

      <div class="popover-section">
        <button class="popover-item" type="button" @click="go('/settings')">
          <Settings :size="14" />
          <span>{{ t('nav.settings') }}</span>
        </button>
        <button class="popover-item" type="button" @click="go('/settings/quality')">
          <Activity :size="14" />
          <span>{{ t('view.quality') }}</span>
        </button>
      </div>

      <div class="popover-divider"></div>

      <div class="popover-section">
        <div class="popover-row">
          <Sun v-if="ui.theme === 'dark'" :size="14" />
          <Moon v-else :size="14" />
          <span>{{ t('menu.theme') }}</span>
          <div class="seg">
            <button
              type="button"
              :class="{ active: ui.theme === 'dark' }"
              @click="ui.setTheme('dark')"
            >{{ t('menu.theme-dark') }}</button>
            <button
              type="button"
              :class="{ active: ui.theme === 'light' }"
              @click="ui.setTheme('light')"
            >{{ t('menu.theme-light') }}</button>
          </div>
        </div>
        <div class="popover-row">
          <Languages :size="14" />
          <span>{{ t('menu.language') }}</span>
          <div class="seg">
            <button
              type="button"
              :class="{ active: ui.locale === 'zh' }"
              @click="ui.setLocale('zh')"
            >{{ t('menu.lang-zh') }}</button>
            <button
              type="button"
              :class="{ active: ui.locale === 'en' }"
              @click="ui.setLocale('en')"
            >{{ t('menu.lang-en') }}</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.workspace-menu-host {
  position: relative;
}

.brand-trigger {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: transparent;
  border: 0;
  padding: 4px 6px;
  border-radius: var(--r-sm);
  cursor: pointer;
  color: var(--text);
}
.brand-trigger:hover {
  background: var(--panel-2);
}

.brand-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.2px;
}

.brand-chevron {
  color: var(--muted);
  transition: transform 160ms ease;
}
.brand-chevron.open {
  transform: rotate(180deg);
}

.workspace-popover {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  width: 260px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.35);
  z-index: 100;
  padding: 6px;
}

.popover-section {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.popover-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 10px;
  border: 0;
  background: transparent;
  border-radius: 6px;
  color: var(--text);
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  width: 100%;
}
.popover-item:hover {
  background: var(--panel-2);
}
.popover-item .hint {
  margin-left: auto;
  font-size: 10px;
  color: var(--muted);
  font-family: var(--mono, monospace);
}

.popover-divider {
  height: 1px;
  background: var(--line);
  margin: 6px 4px;
}

.popover-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  color: var(--text);
  font-size: 13px;
}
.popover-row > span {
  flex: 1;
}

.seg {
  display: inline-flex;
  background: var(--panel-2);
  border-radius: 6px;
  padding: 1px;
  gap: 1px;
}
.seg button {
  border: 0;
  background: transparent;
  color: var(--muted);
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 5px;
  cursor: pointer;
}
.seg button.active {
  background: var(--panel-3);
  color: var(--text);
}
</style>
