<script setup lang="ts">
import { ref } from 'vue'
import { CheckCircle2, X, Clock } from "lucide-vue-next"

type ReviewItem = {
  id: string
  type: 'duplicate' | 'tag-suggest' | 'low-ocr' | 'conflict' | 'pending-gen'
  title: string
  body: string
  actions: { label: string; kind: 'primary' | 'ghost' | 'danger' }[]
}

const items = ref<ReviewItem[]>([])

function dismiss(id: string) {
  items.value = items.value.filter((i) => i.id !== id)
}

function act(id: string) {
  items.value = items.value.filter((i) => i.id !== id)
}

const typeColor: Record<ReviewItem['type'], string> = {
  duplicate: 'var(--pink)',
  'tag-suggest': 'var(--blue)',
  'low-ocr': 'var(--orange)',
  conflict: 'var(--pink)',
  'pending-gen': 'var(--green)',
}

const typeLabel: Record<ReviewItem['type'], string> = {
  duplicate: 'Duplicate',
  'tag-suggest': 'Tag',
  'low-ocr': 'OCR',
  conflict: 'Conflict',
  'pending-gen': 'Generated',
}
</script>

<template>
  <section class="review-view">
    <header class="topbar tight">
      <span>Review</span>
      <span class="spacer"></span>
    </header>

    <header class="topbar tight">
      <span style="font-size: 13px; color: var(--muted);">Needs review</span>
      <span class="pill square">{{ items.length }}</span>
      <span class="spacer"></span>
      <button class="btn btn-ghost" style="height: 28px; font-size: 12px;">
        <CheckCircle2 :size="14" />
        全部已处理
      </button>
    </header>

    <div class="review-list">
      <div v-if="!items.length" class="placeholder">
        <CheckCircle2 :size="32" style="color: var(--green);" />
        <div style="margin-top: 12px;">所有内容已确认 ✨</div>
      </div>

      <div
        v-for="item in items"
        :key="item.id"
        class="review-item"
      >
        <div class="review-title">
          <span class="pill square" :style="{ color: typeColor[item.type] }">
            {{ typeLabel[item.type] }}
          </span>
          <span>{{ item.title }}</span>
          <button class="icon-button" style="margin-left: auto; width: 28px; height: 28px;" @click="dismiss(item.id)">
            <X :size="14" />
          </button>
        </div>
        <div class="review-body">{{ item.body }}</div>
        <div class="review-actions">
          <button
            v-for="(a, ai) in item.actions"
            :key="ai"
            class="btn"
            :class="{
              'btn-primary': a.kind === 'primary',
              'btn-ghost': a.kind === 'ghost',
            }"
            :style="a.kind === 'danger' ? { color: 'var(--pink)', borderColor: 'rgba(232,91,134,.4)' } : {}"
            style="height: 28px; padding: 0 12px; font-size: 12px;"
            @click="act(item.id)"
          >
            {{ a.label }}
          </button>
          <button
            class="btn btn-ghost"
            style="height: 28px; padding: 0 10px; font-size: 12px; margin-left: auto;"
            @click="dismiss(item.id)"
          >
            <Clock :size="12" />
            稍后
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.review-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow-y: auto;
}
</style>
