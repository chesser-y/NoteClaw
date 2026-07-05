<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Send, MoreHorizontal, Plus, Trash2, MessageSquare, Star } from "lucide-vue-next"
import { useUiStore } from '../stores/ui'
import { useChatStore } from '../stores/chat'
import { useIngest } from '../composables/useIngest'
import { useHorizontalDrag } from '../composables/useDrag'
import { listChatSessions, deleteChatSession, setSessionFavorite } from '../api/chat'
import type { ChatSessionRead } from '../api/types'
import SourcePreview from '../components/home/SourcePreview.vue'
import UnderstandingPanel from '../components/home/UnderstandingPanel.vue'
import HomeHero from '../components/home/HomeHero.vue'
import AgentTracePanel from '../components/chat/AgentTracePanel.vue'
import MarkdownView from '../components/common/MarkdownView.vue'

const { t } = useI18n()

type Mode = 'hero' | 'split' | 'chat'

const ui = useUiStore()
const chat = useChatStore()
const ingest = useIngest()

const splitWidth = useHorizontalDrag({ initial: 320, min: 260, max: 520, storageKey: 'noteclaw.inbox-split' })

const mode = ref<Mode>('hero')
const sessions = ref<ChatSessionRead[]>([])
const loadingSessions = ref(false)
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

async function loadSessions() {
  loadingSessions.value = true
  try {
    sessions.value = await listChatSessions(50)
  } catch (e) {
    console.error('failed to load sessions', e)
    sessions.value = []
  } finally {
    loadingSessions.value = false
  }
}

onMounted(() => {
  loadSessions()
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
  await loadSessions()
}

async function submitInline() {
  const text = draftsQuestion.value.trim()
  if (!text) return
  draftsQuestion.value = ''
  await chat.ask(text)
  await loadSessions()
}

async function onHeroAsk(question: string) {
  draftsQuestion.value = ''
  mode.value = 'split'
  await chat.ask(question)
  await loadSessions()
}

async function openSession(s: ChatSessionRead) {
  mode.value = 'split'
  await chat.loadSession(s.id)
}

async function removeSession(id: string, ev: Event) {
  ev.stopPropagation()
  try {
    await deleteChatSession(id)
    sessions.value = sessions.value.filter((s) => s.id !== id)
    if (chat.sessionId === id) chat.reset()
  } catch (e) {
    console.error(e)
  }
}

async function toggleSessionFav(s: ChatSessionRead, ev: Event) {
  ev.stopPropagation()
  const next = !s.is_favorite
  const before = s.is_favorite
  s.is_favorite = next
  try {
    await setSessionFavorite(s.id, next)
  } catch {
    s.is_favorite = before
  }
}

function focusChat() {
  if (mode.value === 'split') mode.value = 'chat'
  else mode.value = 'split'
}

function backToHero() {
  mode.value = 'hero'
  chat.reset()
}

function startNewChat() {
  mode.value = 'hero'
  chat.reset()
}

function onIngestAsk() {
  ui.openAsk(null)
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
        <div class="inbox-list-header">
          <span class="section-title">{{ t('inbox.recent') }}</span>
          <button class="icon-button new-chat-btn" type="button" :title="t('inbox.new-chat')" @click="startNewChat">
            <Plus :size="14" />
          </button>
        </div>
        <div class="inbox-items">
          <div
            v-for="s in sessions"
            :key="s.id"
            class="inbox-card session-card"
            :class="{ active: chat.sessionId === s.id }"
            @click="openSession(s)"
          >
            <MessageSquare :size="14" class="session-icon" />
            <div class="session-text">
              <strong>{{ s.title || 'Untitled' }}</strong>
              <span class="sub">
                {{ (s.message_count ?? 0) + t('inbox.messages-suffix') }}
                · {{ relativeTime(s.updated_at || s.created_at) }}
              </span>
            </div>
            <button
              class="icon-button session-star"
              :class="{ active: s.is_favorite }"
              type="button"
              :title="t('favorites.title')"
              @click="toggleSessionFav(s, $event)"
            >
              <Star :size="12" :fill="s.is_favorite ? 'currentColor' : 'none'" />
            </button>
            <button
              class="icon-button session-delete"
              type="button"
              :title="t('inbox.delete-chat')"
              @click="removeSession(s.id, $event)"
            >
              <Trash2 :size="12" />
            </button>
          </div>

          <div v-if="!sessions.length && !loadingSessions" class="placeholder" style="padding: 40px 16px; font-size: 13px; text-align: center;">
            {{ t('inbox.recent-empty') }}
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
              <div class="bubble">
                <MarkdownView v-if="turn.content" :content="turn.content" />
              </div>
              <AgentTracePanel
                v-if="turn.role === 'assistant' && (turn.streaming || (((turn.trace?.metadata as any)?.steps?.length) ?? 0) > 0)"
                :trace="turn.trace"
                :live="!!turn.streaming && chat.sending && i === chat.turns.length - 1"
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

          <div v-if="chat.sending && (!chat.turns.length || chat.turns[chat.turns.length - 1]?.role !== 'assistant')" class="chat-msg assistant">
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
            <div class="bubble">
              <MarkdownView v-if="turn.content" :content="turn.content" />
            </div>
            <AgentTracePanel
              v-if="turn.role === 'assistant' && (turn.streaming || (((turn.trace?.metadata as any)?.steps?.length) ?? 0) > 0)"
              :trace="turn.trace"
              :live="!!turn.streaming && chat.sending && i === chat.turns.length - 1"
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

.inbox-list-header {
  display: flex;
  align-items: center;
  padding: 8px 12px 4px;
  border-bottom: 1px solid var(--line-soft);
}
.inbox-list-header .section-title {
  flex: 1;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--muted);
}
.new-chat-btn {
  width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
}

.session-card {
  cursor: pointer;
  position: relative;
}
.session-card:hover .session-delete {
  opacity: 1;
}
.session-card.active {
  background: rgba(98, 107, 230, 0.14);
}
.session-icon {
  color: var(--muted);
  flex-shrink: 0;
  align-self: flex-start;
  margin-top: 3px;
}
.session-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.session-text strong {
  font-size: 12px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.session-delete {
  opacity: 0;
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: opacity 120ms ease;
}
.session-delete:hover {
  background: rgba(232, 91, 134, 0.18);
  color: var(--pink);
}
.session-star {
  opacity: 0;
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  color: var(--orange, #f5a524);
  transition: opacity 120ms ease;
}
.session-card:hover .session-star {
  opacity: 1;
}
.session-star.active {
  opacity: 1;
}
.session-star:hover {
  background: rgba(245, 165, 36, 0.18);
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
