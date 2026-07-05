<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  Search,
  Home,
  Library,
  Workflow,
  Sparkles,
  Settings,
  FileText,
  Layers,
  Presentation,
  Boxes,
  Github,
  CornerDownLeft,
} from 'lucide-vue-next'
import { useUiStore } from '../../stores/ui'
import { useMagicKey } from '../../composables/useMagicKey'
import { createHarnessJob } from '../../api/harness'

const ui = useUiStore()
const router = useRouter()

const query = ref('')
const activeIndex = ref(0)
const inputEl = ref<HTMLInputElement | null>(null)

type Action = {
  id: string
  label: string
  hint?: string
  icon: typeof Search
  keywords?: string
  section: 'navigate' | 'ask' | 'generate' | 'harness'
  run: () => unknown | Promise<unknown>
}

const actions: Action[] = [
  { id: 'nav-home', label: '前往首页', hint: 'Home', icon: Home, section: 'navigate', run: () => router.push('/') },
  { id: 'nav-library', label: '前往资料库', hint: 'Library', icon: Library, section: 'navigate', run: () => router.push('/library') },
  { id: 'nav-tasks', label: '前往任务', hint: 'Tasks', icon: Workflow, section: 'navigate', run: () => router.push('/tasks') },
  { id: 'nav-studio', label: '前往创作台', hint: 'Studio', icon: Sparkles, section: 'navigate', run: () => router.push('/studio') },
  { id: 'nav-settings', label: '前往设置', hint: 'Settings', icon: Settings, section: 'navigate', run: () => router.push('/settings') },

  {
    id: 'ask-all',
    label: '提问 NoteClaw',
    hint: 'Ask',
    icon: FileText,
    keywords: 'ask question 问 提问',
    section: 'ask',
    run: () => ui.openAsk(null),
  },
  {
    id: 'ask-recent',
    label: '总结最近保存的内容',
    hint: 'Summarize',
    icon: Layers,
    keywords: '总结 最近 summarize recent',
    section: 'ask',
    run: () => ui.openAsk(null, '总结我最近保存的内容'),
  },
  {
    id: 'ask-related',
    label: '找出相关笔记',
    hint: 'Related',
    icon: Layers,
    keywords: 'related 相关 找 note',
    section: 'ask',
    run: () => ui.openAsk(null, '帮我找出与这个主题相关的笔记'),
  },

  {
    id: 'gen-ppt',
    label: '生成 PPT 大纲',
    hint: 'Slides',
    icon: Presentation,
    keywords: 'ppt outline slides 幻灯片 大纲',
    section: 'generate',
    run: () => router.push({ path: '/studio', query: { prompt: '根据最近保存的资料生成一份 PPT 大纲' } }),
  },
  {
    id: 'gen-brief',
    label: '生成简报 Brief',
    hint: 'Brief',
    icon: FileText,
    keywords: 'brief report 简报 汇报',
    section: 'generate',
    run: () => router.push({ path: '/studio', query: { template: 'brief' } }),
  },
  {
    id: 'gen-notes',
    label: '生成学习笔记',
    hint: 'Notes',
    icon: FileText,
    keywords: 'notes 学习 笔记',
    section: 'generate',
    run: () => router.push({ path: '/studio', query: { template: 'notes' } }),
  },

  {
    id: 'harness-organize',
    label: '整理最近保存的内容',
    hint: 'nanobot',
    icon: Boxes,
    keywords: 'organize 整理 nanobot harness',
    section: 'harness',
    run: async () => {
      await router.push('/tasks')
      await runHarness('整理最近保存的内容', '整理我最近保存的资料，按主题归类并生成一份索引。')
    },
  },
  {
    id: 'harness-github',
    label: '搜索 GitHub 相关项目',
    hint: 'nanobot',
    icon: Github,
    keywords: 'github search 项目 搜索',
    section: 'harness',
    run: async () => {
      await router.push('/tasks')
      await runHarness('GitHub 项目调研', '搜索与本知识库主题相关的 GitHub 项目，整理 Top 5 仓库的简介与链接。')
    },
  },
]

async function runHarness(jobType: string, instruction: string) {
  try {
    await createHarnessJob({ job_type: jobType, instruction })
  } catch (e) {
    console.error('harness job failed', e)
  }
}

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return actions
  return actions.filter((a) => {
    const haystack = [a.label, a.hint ?? '', a.keywords ?? ''].join(' ').toLowerCase()
    return haystack.includes(q)
  })
})

const grouped = computed(() => {
  const order: Action['section'][] = ['navigate', 'ask', 'generate', 'harness']
  const labels: Record<Action['section'], string> = {
    navigate: 'Navigate',
    ask: 'Ask NoteClaw',
    generate: 'Generate',
    harness: 'nanobot',
  }
  return order
    .map((section) => ({ section, label: labels[section], items: filtered.value.filter((a) => a.section === section) }))
    .filter((g) => g.items.length)
})

watch(filtered, () => {
  activeIndex.value = 0
})

watch(
  () => ui.paletteOpen,
  async (open) => {
    if (open) {
      query.value = ''
      activeIndex.value = 0
      await nextTick()
      inputEl.value?.focus()
    }
  },
)

const flatItems = computed(() => grouped.value.flatMap((g) => g.items))

async function selectAt(i: number) {
  const action = flatItems.value[i]
  if (!action) return
  ui.closePalette()
  await action.run()
}

function onKey(e: KeyboardEvent) {
  if (!ui.paletteOpen) return
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    activeIndex.value = (activeIndex.value + 1) % Math.max(flatItems.value.length, 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    activeIndex.value = (activeIndex.value - 1 + flatItems.value.length) % Math.max(flatItems.value.length, 1)
  } else if (e.key === 'Enter') {
    e.preventDefault()
    void selectAt(activeIndex.value)
  } else if (e.key === 'Escape') {
    ui.closePalette()
  }
}

useMagicKey((e) => {
  if (e.key === 'Escape' && ui.paletteOpen) ui.closePalette()
})

function isActive(idx: number) {
  return idx === activeIndex.value
}
</script>

<template>
  <Teleport to="body">
    <template v-if="ui.paletteOpen">
      <div class="command-backdrop" @click="ui.closePalette()">
        <div class="command-panel" @click.stop>
          <div class="flex items-center gap-2 border-b border-[#24262a] px-4 py-3">
            <Search :size="16" class="text-[#73747a]" />
            <input
              ref="inputEl"
              v-model="query"
              class="min-w-0 flex-1 bg-transparent text-sm outline-none"
              :class="`text-[var(--text)] placeholder:text-[var(--muted-2)]`"
              placeholder="搜索命令或提问…"
              type="text"
              @keydown="onKey"
            />
            <span class="kbd">Esc</span>
          </div>

          <div class="max-h-[52vh] overflow-y-auto py-2">
            <template v-for="group in grouped" :key="group.section">
              <div class="px-4 pb-1 pt-3 text-[10px] font-semibold uppercase tracking-wider text-[#73747a]">
                {{ group.label }}
              </div>
              <template v-for="action in group.items" :key="action.id">
                <button
                  class="cmd-item flex w-full items-center gap-3 px-4 py-2 text-left text-sm"
                  :class="{ active: isActive(flatItems.indexOf(action)) }"
                  type="button"
                  @click="selectAt(flatItems.indexOf(action))"
                >
                  <component :is="action.icon" :size="15" />
                  <span class="flex-1">{{ action.label }}</span>
                  <span v-if="action.hint" class="text-[11px] text-[#73747a]">{{ action.hint }}</span>
                </button>
              </template>
            </template>
            <p v-if="!flatItems.length" class="px-4 py-6 text-center text-xs text-[#73747a]">
              没有匹配的命令
            </p>
          </div>

          <div class="flex items-center justify-between border-t border-[#24262a] px-4 py-2 text-[11px] text-[#73747a]">
            <div class="flex items-center gap-3">
              <span class="flex items-center gap-1"><span class="kbd">↑</span><span class="kbd">↓</span> 选择</span>
              <span class="flex items-center gap-1"><span class="kbd"><CornerDownLeft :size="10" /></span> 执行</span>
            </div>
            <span>NoteClaw Command</span>
          </div>
        </div>
      </div>
    </template>
  </Teleport>
</template>

<style scoped>
.cmd-item {
  color: var(--text);
  border-left: 2px solid transparent;
}
.cmd-item:hover {
  background: var(--panel-2);
}
.cmd-item.active {
  background: rgba(98, 107, 230, 0.24);
  color: var(--text);
  border-left-color: var(--blue);
}
</style>
