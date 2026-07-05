<script setup lang="ts">
import {
  Inbox,
  Library,
  Telescope,
  Workflow,
  Clock,
  Sparkles,
  CheckCircle,
  Settings,
  Search,
  Plus,
  Network,
  Menu,
  PanelLeftClose,
} from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useUiStore } from '../../stores/ui'
import { useMagicKey } from '../../composables/useMagicKey'
import AskPanel from '../ask/AskPanel.vue'
import CommandPalette from '../command/CommandPalette.vue'
import ThemeToggle from './ThemeToggle.vue'
import WorkspaceMenu from './WorkspaceMenu.vue'

const ui = useUiStore()
const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const mainItems = [
  { to: '/', label: 'nav.inbox', icon: Inbox },
  { to: '/library', label: 'nav.library', icon: Library },
  { to: '/research', label: 'nav.research', icon: Telescope },
  { to: '/tasks', label: 'nav.tasks', icon: Workflow },
]

const workspaceItems = [
  { to: '/timeline', label: 'nav.timeline', icon: Clock },
  { to: '/graph', label: 'nav.graph', icon: Network },
  { to: '/studio', label: 'nav.studio', icon: Sparkles },
  { to: '/review', label: 'nav.review', icon: CheckCircle },
]

useMagicKey((e) => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    ui.togglePalette()
  }
})

function navTo(to: string) {
  if (route.fullPath !== to) router.push(to)
}
</script>

<template>
  <div class="app-shell" :class="{ 'sidebar-collapsed': !ui.sidebarOpen }">
    <button
      v-if="!ui.sidebarOpen"
      class="hamburger"
      type="button"
      :aria-label="t('nav.menu')"
      :aria-expanded="ui.sidebarOpen"
      @click="ui.toggleSidebar()"
    >
      <Menu :size="18" />
    </button>

    <div
      v-if="ui.sidebarOpen"
      class="sidebar-backdrop"
      @click="ui.closeSidebar()"
    ></div>

    <aside class="sidebar" :class="{ open: ui.sidebarOpen }">
      <div class="brand">
        <WorkspaceMenu />
        <div class="brand-actions">
          <RouterLink to="/" class="icon-button filled" aria-label="Compose" :title="t('action.new-chat')">
            <Plus :size="16" />
          </RouterLink>
          <button
            class="icon-button collapse-btn"
            type="button"
            :aria-label="t('nav.menu')"
            :title="t('nav.menu')"
            @click="ui.closeSidebar()"
          >
            <PanelLeftClose :size="16" />
          </button>
        </div>
      </div>

      <nav>
        <div class="nav-section">
          <div class="nav-list">
            <a
              v-for="item in mainItems"
              :key="item.to"
              class="nav-link"
              :class="{ active: route.path === item.to }"
              @click="navTo(item.to)"
            >
              <component :is="item.icon" :size="16" />
              <span>{{ t(item.label) }}</span>
            </a>
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
            <a
              v-for="item in workspaceItems"
              :key="item.to"
              class="nav-link"
              :class="{ active: route.path === item.to }"
              @click="navTo(item.to)"
            >
              <component :is="item.icon" :size="16" />
              <span>{{ t(item.label) }}</span>
            </a>
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
              <span class="status-ring gray"></span>
              <span style="color: #7b8089; font-size: 13px;">Star topics to pin</span>
            </div>
          </div>
        </div>

        <div class="nav-section" style="margin-top: auto;">
          <div class="nav-list">
            <a
              class="nav-link"
              :class="{ active: route.path === '/settings' }"
              @click="navTo('/settings')"
            >
              <Settings :size="16" />
              <span>{{ t('nav.settings') }}</span>
            </a>
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

    <div class="topbar-actions">
      <button
        class="icon-button topbar-action"
        type="button"
        :aria-label="t('action.open-palette')"
        :title="t('action.open-palette')"
        @click="ui.openPalette()"
      >
        <Search :size="16" />
      </button>
    </div>

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

.hamburger {
  position: fixed;
  top: 12px;
  left: 12px;
  z-index: 60;
  width: 38px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  color: var(--text);
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
}
.hamburger:hover {
  background: var(--panel-3);
}

.topbar-actions {
  position: fixed;
  top: 10px;
  right: 14px;
  z-index: 30;
  display: inline-flex;
  gap: 6px;
}
.topbar-action {
  width: 34px;
  height: 34px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  color: var(--text);
  cursor: pointer;
}
.topbar-action:hover {
  background: var(--panel-3);
}

.collapse-btn {
  display: inline-flex;
}

.sidebar-backdrop {
  display: none;
}

.sidebar {
  transform: translateX(0);
  transition: transform 200ms ease;
}

.sidebar:not(.open) {
  transform: translateX(-100%);
}

@media (max-width: 920px) {
  .collapse-btn {
    display: none;
  }

  .sidebar-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 40;
    backdrop-filter: blur(2px);
  }

  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    z-index: 50;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  }
}
</style>
