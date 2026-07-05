<script setup lang="ts">
import { MessageSquareText } from 'lucide-vue-next'
import { useUiStore } from '../../stores/ui'

const props = defineProps<{
  noteIds?: string[]
  title?: string
  label?: string
}>()

const ui = useUiStore()

function open() {
  ui.openAsk(
    props.noteIds && props.noteIds.length ? { noteIds: props.noteIds, title: props.title } : null,
  )
}
</script>

<template>
  <button class="btn btn-ghost h-8 px-2 text-xs" type="button" @click="open">
    <MessageSquareText :size="14" />
    <slot>{{ label ?? '继续追问' }}</slot>
  </button>
</template>
