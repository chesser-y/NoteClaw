<script setup lang="ts">
import {
  Bot,
  Database,
  FilePlus2,
  LayoutDashboard,
  Library,
  MessageSquareText,
  Search,
  Settings,
  Sparkles,
  Workflow,
} from 'lucide-vue-next'
import { useRouter } from 'vue-router'

const router = useRouter()

const navItems = [
  { to: '/library', label: '知识库', icon: Library },
  { to: '/ingest', label: '信息输入', icon: FilePlus2 },
  { to: '/chat', label: '知识问答', icon: MessageSquareText },
  { to: '/generate', label: '内容生成', icon: Sparkles },
  { to: '/tasks', label: '任务中心', icon: Workflow },
  { to: '/settings', label: '系统设置', icon: Settings },
]

function goIngest() {
  router.push('/ingest')
}
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="mb-8 flex items-center gap-3">
        <div class="flex h-10 w-10 items-center justify-center border border-[#3a4240] bg-[#181b1b]">
          <Bot :size="20" />
        </div>
        <div>
          <div class="serif text-xl leading-tight text-white">NoteClaw</div>
          <div class="text-xs uppercase tracking-[0.18em] text-[#78817e]">Knowledge AI</div>
        </div>
      </div>

      <nav class="flex flex-col gap-2">
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to" class="nav-link">
          <component :is="item.icon" :size="18" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="mt-auto surface p-4">
        <div class="mb-3 flex items-center gap-2 text-sm text-white">
          <Database :size="16" />
          <span>本地知识库</span>
        </div>
        <p class="mb-4 text-sm leading-6 text-[#8f9996]">
          SQLite 保存元数据，FAISS 负责语义索引，nanobot 预留为执行 harness。
        </p>
        <button class="btn btn-primary w-full" type="button" @click="goIngest">
          <FilePlus2 :size="16" />
          新增资料
        </button>
      </div>
    </aside>

    <main class="main-panel">
      <header class="topbar">
        <div class="flex min-w-0 flex-1 items-center gap-3 border border-[#303534] bg-[#151818] px-3 py-2">
          <Search :size="18" class="text-[#89928f]" />
          <input
            class="min-w-0 flex-1 bg-transparent text-sm text-white outline-none placeholder:text-[#68716e]"
            placeholder="搜索知识、标签、任务或生成内容"
          />
        </div>

        <div class="hidden items-center gap-2 border border-[#303534] px-3 py-2 text-sm text-[#c9cfcc] md:flex">
          <span class="status-dot"></span>
          API 合约模式
        </div>

        <button class="btn btn-ghost" type="button" title="工作台">
          <LayoutDashboard :size="18" />
        </button>
      </header>

      <RouterView />
    </main>
  </div>
</template>
