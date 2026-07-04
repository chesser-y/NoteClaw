<script setup lang="ts">
import { Home, Library, Workflow, Sparkles, Settings, Bot, Search, Plus } from 'lucide-vue-next'
import { useUiStore } from '../../stores/ui'
import { useMagicKey } from '../../composables/useMagicKey'
import AskPanel from '../ask/AskPanel.vue'
import CommandPalette from '../command/CommandPalette.vue'

const ui = useUiStore()

const workspaceItems = [
  { to: '/', label: '首页', sub: 'Home', icon: Home },
  { to: '/library', label: '资料库', sub: 'Library', icon: Library },
  { to: '/tasks', label: '任务', sub: 'Tasks', icon: Workflow },
  { to: '/studio', label: '创作台', sub: 'Studio', icon: Sparkles },
  { to: '/settings', label: '设置', sub: 'Settings', icon: Settings },
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
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M4 6l4 4 4-4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </div>
        <div class="brand-actions">
          <button class="icon-button" type="button" aria-label="Search" @click="ui.openPalette()">
            <Search :size="18" />
          </button>
          <button class="icon-button filled" type="button" aria-label="Compose" @click="ui.openPalette()">
            <Plus :size="18" />
          </button>
        </div>
      </div>

      <nav>
        <div class="nav-section">
          <div class="nav-heading">
            <Bot :size="16" />
            <span>工作区</span>
          </div>
          <div class="nav-list">
            <RouterLink
              v-for="item in workspaceItems"
              :key="item.to"
              :to="item.to"
              class="nav-link"
            >
              <component :is="item.icon" :size="18" />
              <span>{{ item.label }}</span>
              <span class="count">{{ item.sub }}</span>
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
