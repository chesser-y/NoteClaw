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
import { useUiStore } from '../../stores/ui'
import { useMagicKey } from '../../composables/useMagicKey'
import AskPanel from '../ask/AskPanel.vue'
import CommandPalette from '../command/CommandPalette.vue'

const ui = useUiStore()

const mainItems = [
  { to: '/', label: 'Inbox', icon: Inbox },
  { to: '/library', label: 'Library', icon: Library },
  { to: '/research', label: 'Research', icon: Telescope },
  { to: '/tasks', label: 'Tasks', icon: Workflow },
]

const workspaceItems = [
  { to: '/timeline', label: 'Timeline', icon: Clock },
  { to: '/map', label: 'Map', icon: MapIcon },
  { to: '/studio', label: 'Studio', icon: Sparkles },
  { to: '/review', label: 'Review', icon: CheckCircle },
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
        <div class="brand-avatar">NC</div>
        <div class="brand-name">
          <span>NoteClaw</span>
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M4 6l4 4 4-4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </div>
        <div class="brand-actions">
          <button class="icon-button" type="button" aria-label="Search" @click="ui.openPalette()">
            <Search :size="16" />
          </button>
          <button class="icon-button filled" type="button" aria-label="Compose" @click="ui.openPalette()">
            <Plus :size="16" />
          </button>
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
              <span>{{ item.label }}</span>
            </RouterLink>
          </div>
        </div>

        <div class="nav-section">
          <div class="nav-heading">
            <span>Workspace</span>
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
              <span>{{ item.label }}</span>
            </RouterLink>
          </div>
        </div>

        <div class="nav-section">
          <div class="nav-heading">
            <span>Favorites</span>
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
              <span>Settings</span>
            </RouterLink>
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
</style>
