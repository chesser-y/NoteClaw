<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { CheckCircle2, X, Clock, RefreshCw, Download, Loader2 } from 'lucide-vue-next'
import {
  listReviewItems,
  actOnReviewItem,
  runDuplicateDetection,
  type DraftItem,
  type LowConfidenceItem,
  type DuplicateItem,
} from '../api/review'

const { t } = useI18n()

type Tab = 'drafts' | 'low_confidence' | 'duplicates'
const tab = ref<Tab>('drafts')

const drafts = ref<DraftItem[]>([])
const lowConfidence = ref<LowConfidenceItem[]>([])
const duplicates = ref<DuplicateItem[]>([])
const loading = ref(false)
const runningDup = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await listReviewItems()
    drafts.value = data.drafts.items
    lowConfidence.value = data.low_confidence.items
    duplicates.value = data.duplicates.items
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function act(
  list: 'drafts' | 'low_confidence' | 'duplicates',
  id: string,
  action: 'approve' | 'reject' | 'defer',
) {
  try {
    await actOnReviewItem(id, action)
    if (list === 'drafts') drafts.value = drafts.value.filter((i) => i.id !== id)
    if (list === 'low_confidence') lowConfidence.value = lowConfidence.value.filter((i) => i.id !== id)
    if (list === 'duplicates') duplicates.value = duplicates.value.filter((i) => i.id !== id)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

async function runDups() {
  runningDup.value = true
  error.value = ''
  try {
    await runDuplicateDetection()
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    runningDup.value = false
  }
}

const totalPending = computed(() => drafts.value.length + lowConfidence.value.length + duplicates.value.length)
const tabIndex = computed(() => ({ drafts: 0, low_confidence: 1, duplicates: 2 }[tab.value]))
</script>

<template>
  <section class="review-view">
    <header class="topbar tight">
      <span>{{ t('view.review') }}</span>
      <span class="pill square">{{ totalPending }}</span>
      <span class="spacer"></span>
      <button class="btn btn-ghost" type="button" :disabled="runningDup" @click="runDups">
        <Loader2 v-if="runningDup" :size="13" class="spin" />
        <RefreshCw v-else :size="13" />
        {{ t('review.run-duplicates') }}
      </button>
    </header>

    <header class="topbar tight tab-row">
      <button
        v-for="(opt, i) in [
          { id: 'drafts', n: drafts.length, label: t('review.tab-drafts') },
          { id: 'low_confidence', n: lowConfidence.length, label: t('review.tab-low-conf') },
          { id: 'duplicates', n: duplicates.length, label: t('review.tab-duplicates') },
        ]"
        :key="opt.id"
        class="tab"
        :class="{ active: tabIndex === i }"
        @click="tab = opt.id as Tab"
      >
        {{ opt.label }}
        <span class="count">{{ opt.n }}</span>
      </button>
    </header>

    <p v-if="error" class="err">{{ error }}</p>

    <div class="review-list">
      <div v-if="loading" class="placeholder">
        <Loader2 :size="20" class="spin" />
      </div>

      <template v-else>
        <!-- DRAFTS -->
        <template v-if="tab === 'drafts'">
          <div v-if="!drafts.length" class="placeholder">
            <CheckCircle2 :size="32" style="color: var(--green);" />
            <div style="margin-top: 12px;">{{ t('review.empty') }}</div>
          </div>
          <article v-for="d in drafts" :key="d.id" class="review-card">
            <header class="card-head">
              <span class="badge gen">{{ d.generation_type || 'gen' }}</span>
              <strong>{{ d.title }}</strong>
              <button class="icon-button x-btn" :title="t('review.defer')" @click="act('drafts', d.id, 'defer')">
                <Clock :size="13" />
              </button>
            </header>
            <div class="card-body">
              <p v-if="d.prompt" class="muted small">"{{ d.prompt.slice(0, 180) }}"</p>
              <p v-if="d.summary" class="muted">{{ d.summary.slice(0, 240) }}</p>
            </div>
            <footer class="card-actions">
              <a v-if="d.download_url" :href="`/api${d.download_url}`" download class="btn btn-ghost mini">
                <Download :size="12" /> {{ t('action.download') }}
              </a>
              <span class="spacer" />
              <button class="btn btn-ghost mini" @click="act('drafts', d.id, 'reject')">
                <X :size="12" /> {{ t('review.reject') }}
              </button>
              <button class="btn btn-primary mini" @click="act('drafts', d.id, 'approve')">
                <CheckCircle2 :size="12" /> {{ t('review.approve') }}
              </button>
            </footer>
          </article>
        </template>

        <!-- LOW CONFIDENCE -->
        <template v-else-if="tab === 'low_confidence'">
          <div v-if="!lowConfidence.length" class="placeholder">
            <CheckCircle2 :size="32" style="color: var(--green);" />
            <div style="margin-top: 12px;">{{ t('review.empty') }}</div>
          </div>
          <article v-for="lc in lowConfidence" :key="lc.id" class="review-card">
            <header class="card-head">
              <span class="badge low" :class="{ ok: (lc.confidence ?? 0) >= 0.4 }">
                {{ Math.round((lc.confidence ?? 0) * 100) }}%
              </span>
              <strong>{{ lc.question.slice(0, 80) }}</strong>
              <button class="icon-button x-btn" :title="t('review.defer')" @click="act('low_confidence', lc.id, 'defer')">
                <Clock :size="13" />
              </button>
            </header>
            <div class="card-body">
              <p class="answer">{{ lc.answer.slice(0, 360) }}</p>
              <p v-if="lc.risks?.length" class="muted small">
                ⚠ {{ lc.risks.slice(0, 3).join(' · ') }}
              </p>
            </div>
            <footer class="card-actions">
              <span class="spacer" />
              <button class="btn btn-ghost mini" @click="act('low_confidence', lc.id, 'reject')">
                <X :size="12" /> {{ t('review.reject') }}
              </button>
              <button class="btn btn-primary mini" @click="act('low_confidence', lc.id, 'approve')">
                <CheckCircle2 :size="12" /> {{ t('review.approve') }}
              </button>
            </footer>
          </article>
        </template>

        <!-- DUPLICATES -->
        <template v-else>
          <div v-if="!duplicates.length" class="placeholder">
            <CheckCircle2 :size="32" style="color: var(--green);" />
            <div style="margin-top: 12px;">{{ t('review.empty-dup') }}</div>
          </div>
          <article v-for="d in duplicates" :key="d.id" class="review-card dup-card">
            <header class="card-head">
              <span class="badge dup">{{ Math.round(d.payload.score * 100) }}% similar</span>
              <strong>{{ t('review.duplicate-title') }}</strong>
            </header>
            <div class="dup-pair">
              <RouterLink :to="`/library?id=${d.payload.note_a}`" class="dup-side">
                <strong>{{ d.payload.title_a || d.payload.note_a.slice(0, 8) }}</strong>
                <span class="muted small">{{ d.payload.note_a.slice(0, 12) }}…</span>
              </RouterLink>
              <span class="dup-vs">vs</span>
              <RouterLink :to="`/library?id=${d.payload.note_b}`" class="dup-side">
                <strong>{{ d.payload.title_b || d.payload.note_b.slice(0, 8) }}</strong>
                <span class="muted small">{{ d.payload.note_b.slice(0, 12) }}…</span>
              </RouterLink>
            </div>
            <footer class="card-actions">
              <span class="spacer" />
              <button class="btn btn-ghost mini" @click="act('duplicates', d.id, 'defer')">
                <Clock :size="12" /> {{ t('review.defer') }}
              </button>
              <button class="btn btn-primary mini" @click="act('duplicates', d.id, 'approve')">
                <CheckCircle2 :size="12" /> {{ t('review.resolve') }}
              </button>
            </footer>
          </article>
        </template>
      </template>
    </div>
  </section>
</template>

<style scoped>
.review-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.tab-row {
  gap: 4px;
  height: 40px;
}
.tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: transparent;
  border: 0;
  color: var(--muted);
  font-size: 12px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
}
.tab.active {
  color: var(--text);
  border-bottom-color: var(--blue);
}
.tab .count {
  font-size: 10px;
  background: var(--panel-2);
  padding: 1px 5px;
  border-radius: 8px;
  color: var(--muted);
}
.tab.active .count {
  background: rgba(98, 107, 230, 0.2);
  color: var(--text);
}

.err {
  border: 1px solid #5a2520;
  background: #2a1614;
  color: #f0b8ad;
  padding: 8px 14px;
  font-size: 12px;
  margin: 0 24px;
  border-radius: 6px;
}

.review-list {
  flex: 1;
  overflow-y: auto;
  padding: 18px 24px 32px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 16px;
  color: var(--muted);
  font-size: 13px;
}

.review-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.card-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.card-head strong {
  flex: 1;
  font-size: 13px;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.x-btn {
  width: 24px;
  height: 24px;
  border-radius: 4px;
}

.badge {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  padding: 2px 7px;
  border-radius: 4px;
  background: var(--panel-2);
  color: var(--text);
}
.badge.gen { background: rgba(98, 107, 230, 0.18); }
.badge.low { background: rgba(232, 91, 134, 0.18); color: var(--pink); }
.badge.low.ok { background: rgba(232, 159, 60, 0.18); color: var(--orange); }
.badge.dup { background: rgba(74, 174, 255, 0.18); color: var(--blue); }

.card-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.card-body .answer {
  font-size: 12px;
  color: var(--text);
  line-height: 1.55;
  background: var(--panel-2);
  border-radius: 4px;
  padding: 8px 10px;
  margin: 0;
}
.muted { color: var(--muted); }
.small { font-size: 11px; }

.card-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}
.card-actions .spacer { flex: 1; }
.mini {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 26px;
  padding: 0 10px;
  font-size: 11px;
  text-decoration: none;
}

.dup-pair {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 10px;
  align-items: center;
  background: var(--panel-2);
  padding: 8px 10px;
  border-radius: 6px;
}
.dup-side {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 4px 6px;
  border-radius: 4px;
  text-decoration: none;
}
.dup-side:hover {
  background: var(--panel-3);
}
.dup-side strong {
  font-size: 12px;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.dup-vs {
  color: var(--muted);
  font-size: 11px;
}

.spin { animation: spin 1s linear infinite; }
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
