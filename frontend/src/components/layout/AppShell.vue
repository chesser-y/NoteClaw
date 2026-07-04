<script setup lang="ts">
import { Home, Library, Workflow, Sparkles, Settings, Bot, Search } from 'lucide-vue-next'
import { useUiStore } from '../../stores/ui'
import { useMagicKey } from '../../composables/useMagicKey'
import AskPanel from '../ask/AskPanel.vue'
import CommandPalette from '../command/CommandPalette.vue'

const ui = useUiStore()

const navItems = [
  { to: '/', label: '首页', sub: 'Home', icon: Home, exact: true },
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
      <div class="mb-6 flex items-center gap-2.5 px-2">
        <div class="flex h-8 w-8 items-center justify-center rounded-[10px] bg-[#4f46e5] text-white">
          <Bot :size="16" />
        </div>
        <div class="leading-tight">
          <div class="text-[15px] font-semibold text-[#111827]">NoteClaw</div>
          <div class="text-[10px] uppercase tracking-[0.18em] text-[#9ca3af]">Knowledge AI</div>
        </div>
      </div>

      <nav class="flex flex-col gap-0.5">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-link"
          :class="{ 'router-link-active': false }"
        >
          <component :is="item.icon" :size="16" />
          <span class="flex-1">{{ item.label }}</span>
          <span class="text-[10px] uppercase tracking-wider text-[#9ca3af]">{{ item.sub }}</span>
        </RouterLink>
      </nav>

      <div class="mt-auto px-2 pt-4">
        <button class="btn btn-primary w-full" type="button" @click="ui.openPalette()">
          <Search :size="14" />
          <span>命令 / 提问</span>
          <span class="kbd ml-1">⌘K</span>
        </button>
      </div>
    </aside>

    <main class="main-panel">
      <RouterView />
    </main>

    <AskPanel />
    <CommandPalette />
  </div>
</template>
