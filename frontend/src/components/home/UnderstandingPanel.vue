<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Save, MessageSquareText, X, Sparkles } from 'lucide-vue-next'
import type { PreviewState } from '../../composables/useIngest'

const { t } = useI18n()

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
      <span class="text-xs font-medium uppercase tracking-wide text-[#929399]">{{ t('understanding.title') }}</span>
    </div>

    <div>
      <div class="mb-1 text-xs text-[#73747a]">{{ t('understanding.summary-label') }}</div>
      <p class="rounded-lg border border-[#24262a] bg-[#151618] p-3 text-sm leading-6 text-[#f0f1f2]">
        {{ props.preview.summary }}
      </p>
    </div>

    <div>
      <div class="mb-1.5 text-xs text-[#73747a]">{{ t('understanding.tags-label') }}</div>
      <div class="flex flex-wrap gap-1.5">
        <span v-for="tag in props.preview.tags" :key="tag" class="chip">{{ tag }}</span>
      </div>
    </div>

    <div>
      <div class="mb-1 text-xs text-[#73747a]">{{ t('understanding.related-label') }}</div>
      <p v-if="!props.preview.related.length" class="text-xs text-[#73747a]">{{ t('understanding.no-related') }}</p>
      <ul v-else class="space-y-1 text-xs text-[#f0f1f2]">
        <li v-for="r in props.preview.related" :key="r.id">· {{ r.title }}</li>
      </ul>
    </div>

    <div>
      <div class="mb-1 text-xs text-[#73747a]">{{ t('understanding.source-label') }}</div>
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
        {{ props.saving ? t('understanding.saving') : t('understanding.save') }}
      </button>
      <button class="btn h-9" type="button" @click="emit('ask')">
        <MessageSquareText :size="14" />
        {{ t('understanding.follow-up') }}
      </button>
      <button class="btn btn-ghost h-9 w-9 p-0" type="button" @click="emit('cancel')" aria-label="Cancel">
        <X :size="14" />
      </button>
    </div>
  </div>
</template>
