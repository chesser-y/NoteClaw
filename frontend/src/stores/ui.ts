import { defineStore } from 'pinia'

export type AskScope = {
  noteIds: string[]
  title?: string
}

export const useUiStore = defineStore('ui', {
  state: () => ({
    paletteOpen: false,
    askOpen: false,
    askScope: null as AskScope | null,
    askPrefill: '',
  }),
  actions: {
    openPalette() {
      this.paletteOpen = true
    },
    closePalette() {
      this.paletteOpen = false
    },
    togglePalette() {
      this.paletteOpen = !this.paletteOpen
    },
    openAsk(scope: AskScope | null = null, prefill = '') {
      this.askScope = scope
      this.askPrefill = prefill
      this.askOpen = true
    },
    closeAsk() {
      this.askOpen = false
      this.askScope = null
      this.askPrefill = ''
    },
  },
})
