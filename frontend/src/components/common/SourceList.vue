<script setup lang="ts">
import type { Citation } from '../../api/types'
import SourceChip from './SourceChip.vue'

defineProps<{
  sources: Citation[]
  contentTypes?: Record<string, string>
}>()
</script>

<template>
  <div class="flex flex-wrap gap-2">
    <SourceChip
      v-for="source in sources"
      :key="source.note_id + (source.chunk_id ?? '')"
      :type="contentTypes?.[source.note_id] ?? 'document'"
      :title="source.title"
      :score="source.score ?? null"
    />
    <p v-if="!sources.length" class="text-xs text-[#73747a]">尚未引用任何资料。</p>
  </div>
</template>
