<script setup lang="ts">
import {
  Inbox,
  Library,
  Telescope,
  Workflow,
  Clock,
  Map as MapIcon,
  Sparkles,
  CheckCircle,
  Settings,
  Search,
  Plus,
} from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useUiStore } from '../../stores/ui'
import { useMagicKey } from '../../composables/useMagicKey'
import AskPanel from '../ask/AskPanel.vue'
import CommandPalette from '../command/CommandPalette.vue'
import ThemeToggle from './ThemeToggle.vue'
import WorkspaceMenu from './WorkspaceMenu.vue'

const ui = useUiStore()
const { t } = useI18n()

const mainItems = [
  { to: '/', label: 'nav.inbox', icon: Inbox },
  { to: '/library', label: 'nav.library', icon: Library },
  { to: '/research', label: 'nav.research', icon: Telescope },
  { to: '/tasks', label: 'nav.tasks', icon: Workflow },
]

const workspaceItems = [
  { to: '/timeline', label: 'nav.timeline', icon: Clock },
  { to: '/map', label: 'nav.map', icon: MapIcon },
  { to: '/studio', label: 'nav.studio', icon: Sparkles },
  { to: '/review', label: 'nav.review', icon: CheckCircle },
]

useMagicKey((e) => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    ui.togglePalette()
  }
})
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <WorkspaceMenu />
        <div class="brand-actions">
          <button class="icon-button" type="button" aria-label="Search" @click="ui.openPalette()">
            <Search :size="16" />
          </button>
          <RouterLink to="/" class="icon-button filled" aria-label="Compose">
            <Plus :size="16" />
          </RouterLink>
        </div>
      </div>

      <nav>
        <div class="nav-section">
          <div class="nav-list">
            <RouterLink
              v-for="item in mainItems"
              :key="item.to"
              :to="item.to"
              class="nav-link"
            >
              <component :is="item.icon" :size="16" />
              <span>{{ t(item.label) }}</span>
            </RouterLink>
          </div>
        </div>

        <div class="nav-section">
          <div class="nav-heading">
            <span>{{ t('nav.workspace') }}</span>
            <svg width="10" height="10" viewBox="0 0 16 16" fill="none" aria-hidden="true" style="margin-left: auto;">
              <path d="M4 6l4 5 4-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </div>
          <div class="nav-list">
            <RouterLink
              v-for="item in workspaceItems"
              :key="item.to"
              :to="item.to"
              class="nav-link"
            >
              <component :is="item.icon" :size="16" />
              <span>{{ t(item.label) }}</span>
            </RouterLink>
          </div>
        </div>

        <div class="nav-section">
          <div class="nav-heading">
            <span>{{ t('nav.favorites') }}</span>
            <svg width="10" height="10" viewBox="0 0 16 16" fill="none" aria-hidden="true" style="margin-left: auto;">
              <path d="M4 6l4 5 4-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </div>
          <div class="nav-list">
            <div class="nav-link muted-static">
              <span class="status-ring gray" style="width: 14px; height: 14px; border-width: 2px;"></span>
              <span style="color: #7b8089; font-size: 13px;">Star topics to pin</span>
            </div>
          </div>
        </div>

        <div class="nav-section" style="margin-top: auto;">
          <div class="nav-list">
            <RouterLink to="/settings" class="nav-link">
              <Settings :size="16" />
              <span>{{ t('nav.settings') }}</span>
            </RouterLink>
            <div class="nav-link theme-row" style="cursor: default;">
              <span style="flex: 1;"></span>
              <ThemeToggle />
            </div>
          </div>
        </div>
      </nav>
    </aside>

    <main class="main-panel">
      <RouterView />
    </main>

    <AskPanel />
    <CommandPalette />
  </div>
</template>

<style scoped>
.muted-static {
  cursor: default;
  pointer-events: none;
  opacity: 0.6;
}
.muted-static:hover {
  background: transparent;
  color: #929399;
}
.theme-row {
  padding-right: 4px;
}
.theme-row:hover {
  background: transparent;
}
</style>
