<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { FileText, Image as ImageIcon, Code2, Table as TableIcon, Send, MoreHorizontal } from "lucide-vue-next"
import { useUiStore } from '../stores/ui'
import { useChatStore } from '../stores/chat'
import { useIngest } from '../composables/useIngest'
import { useHorizontalDrag } from '../composables/useDrag'
import { listKnowledge } from '../api/knowledge'
import { listTasks } from '../api/tasks'
import type { NoteListItem, TaskRead } from '../api/types'
import SourcePreview from '../components/home/SourcePreview.vue'
import UnderstandingPanel from '../components/home/UnderstandingPanel.vue'
import HomeHero from '../components/home/HomeHero.vue'
import AgentTracePanel from '../components/chat/AgentTracePanel.vue'

const { t } = useI18n()

type Mode = 'hero' | 'split' | 'chat'

const ui = useUiStore()
const chat = useChatStore()
const ingest = useIngest()

const splitWidth = useHorizontalDrag({ initial: 482, min: 320, max: 760, storageKey: 'noteclaw.inbox-split' })

const mode = ref<Mode>('hero')
const recent = ref<NoteListItem[]>([])
const tasks = ref<TaskRead[]>([])
const loadingRecent = ref(false)
const draftsQuestion = ref('')
const tab = ref<'ask' | 'browse'>('ask')

const prompts = computed(() => [
  t('inbox.suggestion-summarize'),
  t('inbox.suggestion-related'),
  t('inbox.suggestion-ppt'),
  t('inbox.suggestion-compare'),
])

const chatPlaceholder = computed(() => {
  if (chat.mode === 'agent') return t('inbox.ask-agent')
  if (chat.mode === 'web') return t('inbox.ask-web')
  return t('inbox.ask-normal')
})

const chatThinking = computed(() => {
  if (chat.mode === 'agent') return t('inbox.thinking-agent')
  if (chat.mode === 'web') return t('inbox.thinking-web')
  return t('inbox.thinking-normal')
})

async function loadRecent() {
  loadingRecent.value = true
  try {
    const [k, t] = await Promise.allSettled([
      listKnowledge({ limit: 8 }),
      listTasks({ limit: 6 }),
    ])
    if (k.status === 'fulfilled') recent.value = k.value.items
    if (t.status === 'fulfilled') tasks.value = t.value.items
  } finally {
    loadingRecent.value = false
  }
}

onMounted(() => {
  loadRecent()
  if (ui.askPrefill) {
    const q = ui.askPrefill
    ui.askPrefill = ''
    submitQuestion(q)
  }
})

async function submitQuestion(q?: string) {
  const text = (q ?? draftsQuestion.value).trim()
  if (!text) return
  if (q) draftsQuestion.value = ''
  mode.value = 'split'
  await chat.ask(text)
}

async function submitInline() {
  const text = draftsQuestion.value.trim()
  if (!text) return
  draftsQuestion.value = ''
  await chat.ask(text)
}

async function onHeroAsk(question: string) {
  draftsQuestion.value = ''
  mode.value = 'split'
  await chat.ask(question)
}

function focusChat() {
  if (mode.value === 'split') mode.value = 'chat'
  else mode.value = 'split'
}

function backToHero() {
  mode.value = 'hero'
  chat.reset()
}

function onIngestAsk() {
  ui.openAsk(null)
}

const iconFor = (t: string) => {
  if (t === 'image') return ImageIcon
  if (t === 'code') return Code2
  if (t === 'table') return TableIcon
  return FileText
}

const relativeTime = (iso: string) => {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)}d`
  return new Date(iso).toLocaleDateString()
}

const hasConversation = chat.turns.length > 0 || ingest.preview.value
void hasConversation
</script>

<template>
  <section class="inbox-view">
    <header class="topbar">
      <span>{{ t('inbox.title') }}</span>
      <button
        class="icon-button"
        type="button"
        :aria-pressed="mode !== 'hero'"
        :title="mode === 'hero' ? t('inbox.open-history') : t('inbox.back-hero')"
        @click="mode === 'hero' ? (mode = 'split') : backToHero()"
      >
        <MoreHorizontal :size="16" />
      </button>
      <span class="spacer"></span>
      <div class="tabs" v-if="mode !== 'hero'">
        <button class="tab" :class="{ active: tab === 'ask' }" @click="tab = 'ask'">{{ t('tabs.ask') }}</button>
        <button class="tab" :class="{ active: tab === 'browse' }" @click="tab = 'browse'">{{ t('tabs.browse') }}</button>
        <button class="tab" @click="focusChat">{{ mode === 'chat' ? t('tabs.split') : t('tabs.focus') }}</button>
        <button class="tab" @click="backToHero">{{ t('tabs.new') }}</button>
      </div>
    </header>

    <!-- HERO MODE -->
    <div v-if="mode === 'hero'" class="inbox-hero">
      <h1>{{ t('inbox.hero-title') }}</h1>
      <p class="hero-sub">{{ t('inbox.hero-sub') }}</p>

      <div v-if="ingest.preview.value" style="width: min(880px, 100%); display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
        <SourcePreview :preview="ingest.preview.value" />
        <UnderstandingPanel
          :preview="ingest.preview.value"
          :saving="ingest.saving.value"
          :error="ingest.error.value"
          @save="ingest.save"
          @cancel="ingest.clear"
          @ask="onIngestAsk"
        />
      </div>

      <HomeHero v-else @preview="ingest.setPreview" @ask="onHeroAsk" />

      <div v-if="!ingest.preview.value" class="hero-prompts">
        <button v-for="p in prompts" :key="p" class="chip" @click="submitQuestion(p)">
          {{ p }}
        </button>
      </div>
    </div>

    <!-- SPLIT MODE -->
    <div
      v-else-if="mode === 'split'"
      class="inbox-layout"
      :style="{ gridTemplateColumns: splitWidth.size.value + 'px 4px 1fr' }"
    >
      <div class="inbox-list">
        <div class="inbox-items">
          <div class="section-title" style="font-size: 13px; padding: 6px 14px; color: #6f7480; font-weight: 700;">
            {{ t('inbox.recent') }}
          </div>
          <div
            v-for="item in recent"
            :key="item.id"
            class="inbox-card"
            style="cursor: pointer;"
            @click="ui.openAsk({ noteIds: [item.id], title: item.title })"
          >
            <component :is="iconFor(item.content_type)" :size="16" style="color: #747983;" />
            <div>
              <strong>{{ item.title }}</strong>
              <span class="sub">{{ (item.tags || []).slice(0, 2).join(' · ') || item.content_type }}</span>
            </div>
            <div class="time">{{ relativeTime(item.created_at) }}</div>
          </div>

          <div v-if="tasks.length" class="section-title" style="font-size: 13px; padding: 14px 14px 6px; color: #6f7480; font-weight: 700;">
            {{ t('inbox.recent-tasks') }}
          </div>
          <div
            v-for="t in tasks"
            :key="t.id"
            class="inbox-card"
            style="cursor: pointer;"
            @click="ui.openAsk({ noteIds: [], title: t.type })"
          >
            <span class="status-ring" :class="{ green: t.status === 'succeeded', gray: t.status === 'failed' }"></span>
            <div>
              <strong>{{ t.type }}</strong>
              <span class="sub">{{ t.message || t.status }}</span>
            </div>
            <div class="time">{{ Math.round(t.progress * 100) }}%</div>
          </div>

          <div v-if="!recent.length && !tasks.length && !loadingRecent" class="placeholder" style="padding: 40px 16px; font-size: 13px;">
            {{ t('empty.inbox-recent') }}
          </div>
        </div>
      </div>

      <div class="split-handle" @mousedown="splitWidth.start"></div>

      <div class="chat-panel">
        <div class="chat-messages">
          <div v-if="ingest.preview.value" style="margin-bottom: 16px;">
            <UnderstandingPanel
              :preview="ingest.preview.value"
              :saving="ingest.saving.value"
              :error="ingest.error.value"
              @save="ingest.save"
              @cancel="ingest.clear"
              @ask="onIngestAsk"
            />
          </div>

          <div v-if="!chat.turns.length && !ingest.preview.value" class="placeholder">
            {{ t('inbox.empty-chat') }}
          </div>

          <div v-for="(turn, i) in chat.turns" :key="i" class="chat-msg" :class="turn.role">
            <div class="avatar">{{ turn.role === 'user' ? 'U' : 'NC' }}</div>
            <div style="flex: 1; min-width: 0;">
              <div class="bubble">{{ turn.content }}</div>
              <AgentTracePanel
                v-if="turn.role === 'assistant' && turn.trace?.steps?.length"
                :trace="turn.trace"
              />
              <div v-if="turn.citations && turn.citations.length" class="chat-citations">
                <span
                  v-for="(c, idx) in turn.citations.slice(0, 5)"
                  :key="idx"
                  class="pill square"
                  :title="c.snippet"
                >
                  [{{ idx + 1 }}] {{ c.title.slice(0, 24) }}
                </span>
              </div>
            </div>
          </div>

          <div v-if="chat.sending" class="chat-msg assistant">
            <div class="avatar">NC</div>
            <div class="bubble muted">{{ chatThinking }}</div>
          </div>
        </div>

        <div class="chat-input-bar">
          <div class="mode-seg">
            <button
              type="button"
              :class="{ active: chat.mode === 'normal' }"
              @click="chat.setMode('normal')"
            >Normal</button>
            <button
              type="button"
              :class="{ active: chat.mode === 'web' }"
              @click="chat.setMode('web')"
            >NanoBot Web</button>
            <button
              type="button"
              :class="{ active: chat.mode === 'agent' }"
              @click="chat.setMode('agent')"
            >Agent</button>
          </div>
          <textarea
            v-model="draftsQuestion"
            :placeholder="chatPlaceholder"
            @keydown.enter.meta.prevent="submitInline"
            @keydown.enter.ctrl.prevent="submitInline"
          ></textarea>
          <button class="btn btn-primary" :disabled="!draftsQuestion.trim() || chat.sending" @click="submitInline()">
            <Send :size="14" />
          </button>
        </div>
      </div>
    </div>

    <!-- CHAT-ONLY MODE -->
    <div v-else class="chat-panel" style="flex: 1;">
      <div class="chat-messages">
        <div v-for="(turn, i) in chat.turns" :key="i" class="chat-msg" :class="turn.role">
          <div class="avatar">{{ turn.role === 'user' ? 'U' : 'NC' }}</div>
          <div style="flex: 1; min-width: 0;">
            <div class="bubble">{{ turn.content }}</div>
            <AgentTracePanel
              v-if="turn.role === 'assistant' && turn.trace?.steps?.length"
              :trace="turn.trace"
            />
            <div v-if="turn.citations && turn.citations.length" class="chat-citations">
              <span
                v-for="(c, idx) in turn.citations.slice(0, 5)"
                :key="idx"
                class="pill square"
                :title="c.snippet"
              >
                [{{ idx + 1 }}] {{ c.title.slice(0, 24) }}
              </span>
            </div>
          </div>
        </div>

        <div v-if="!chat.turns.length" class="placeholder">{{ t('inbox.no-conversation') }}</div>
      </div>

      <div class="chat-input-bar">
        <div class="mode-seg">
          <button
            type="button"
            :class="{ active: chat.mode === 'normal' }"
            @click="chat.setMode('normal')"
          >Normal</button>
          <button
            type="button"
            :class="{ active: chat.mode === 'web' }"
            @click="chat.setMode('web')"
          >NanoBot Web</button>
          <button
            type="button"
            :class="{ active: chat.mode === 'agent' }"
            @click="chat.setMode('agent')"
          >Agent</button>
        </div>
        <textarea
          v-model="draftsQuestion"
          :placeholder="chatPlaceholder"
          @keydown.enter.meta.prevent="submitInline"
          @keydown.enter.ctrl.prevent="submitInline"
        ></textarea>
        <button class="btn btn-primary" :disabled="!draftsQuestion.trim() || chat.sending" @click="submitInline()">
          <Send :size="14" />
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.inbox-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.tabs {
  display: flex;
  gap: 4px;
}

.mode-seg {
  display: inline-flex;
  background: var(--panel-2);
  border-radius: 6px;
  padding: 1px;
  gap: 1px;
  flex-shrink: 0;
}
.mode-seg button {
  border: 0;
  background: transparent;
  color: var(--muted);
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 5px;
  white-space: nowrap;
  cursor: pointer;
  font-weight: 500;
}
.mode-seg button.active {
  background: rgba(98, 107, 230, 0.32);
  color: var(--text);
}
.mode-seg button:hover:not(.active) {
  color: var(--text);
}
</style>
