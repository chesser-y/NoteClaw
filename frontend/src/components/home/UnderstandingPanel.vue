<script setup lang="ts">
import { Save, MessageSquareText, X, Sparkles } from 'lucide-vue-next'
import type { PreviewState } from '../../composables/useIngest'

const props = defineProps<{
  preview: PreviewState
  saving: boolean
  error: string
}>()

const emit = defineEmits<{
  save: []
  cancel: []
  ask: []
}>()
</script>

<template>
  <div class="surface flex flex-col gap-4 p-4">
    <div class="flex items-center gap-2">
      <Sparkles :size="16" class="text-[#626be6]" />
      <span class="text-xs font-medium uppercase tracking-wide text-[#929399]">Understanding</span>
    </div>

    <div>
      <div class="mb-1 text-xs text-[#73747a]">简要摘要</div>
      <p class="rounded-lg border border-[#24262a] bg-[#151618] p-3 text-sm leading-6 text-[#f0f1f2]">
        {{ props.preview.summary }}
      </p>
    </div>

    <div>
      <div class="mb-1.5 text-xs text-[#73747a]">自动标签</div>
      <div class="flex flex-wrap gap-1.5">
        <span v-for="tag in props.preview.tags" :key="tag" class="chip">{{ tag }}</span>
      </div>
    </div>

    <div>
      <div class="mb-1 text-xs text-[#73747a]">关联内容</div>
      <p v-if="!props.preview.related.length" class="text-xs text-[#73747a]">暂未发现关联笔记（保存后会自动检索）。</p>
      <ul v-else class="space-y-1 text-xs text-[#f0f1f2]">
        <li v-for="r in props.preview.related" :key="r.id">· {{ r.title }}</li>
      </ul>
    </div>

    <div>
      <div class="mb-1 text-xs text-[#73747a]">来源信息</div>
      <div class="text-xs text-[#f0f1f2]">
        Source: <span class="font-medium">{{ props.preview.source }}</span>
        <span v-if="props.preview.language"> · {{ props.preview.language }}</span>
      </div>
    </div>

    <p v-if="props.error" class="rounded-lg border border-[#5a2520] bg-[#2a1614] px-3 py-2 text-xs text-[#f0b8ad]">
      {{ props.error }}
    </p>

    <div class="mt-auto flex items-center gap-2 pt-2">
      <button class="btn btn-primary h-9 flex-1" type="button" :disabled="props.saving" @click="emit('save')">
        <Save :size="14" />
        {{ props.saving ? '保存中…' : '保存' }}
      </button>
      <button class="btn h-9" type="button" @click="emit('ask')">
        <MessageSquareText :size="14" />
        继续追问
      </button>
      <button class="btn btn-ghost h-9 w-9 p-0" type="button" @click="emit('cancel')" aria-label="Cancel">
        <X :size="14" />
      </button>
    </div>
  </div>
</template>
