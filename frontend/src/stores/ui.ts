import { defineStore } from 'pinia'
import { setLocale as applyLocale } from '../i18n'
import type { Locale } from '../i18n'

export type AskScope = {
  noteIds: string[]
  title?: string
}

export type Theme = 'dark' | 'light'

const THEME_KEY = 'noteclaw.theme'
const LOCALE_KEY = 'noteclaw.locale'

function readPersistedTheme(): Theme {
  const stored = localStorage.getItem(THEME_KEY)
  return stored === 'light' ? 'light' : 'dark'
}

function readPersistedLocale(): Locale {
  const stored = localStorage.getItem(LOCALE_KEY)
  return stored === 'en' ? 'en' : 'zh'
}

function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme
  localStorage.setItem(THEME_KEY, theme)
}

export const useUiStore = defineStore('ui', {
  state: () => ({
    paletteOpen: false,
    askOpen: false,
    askScope: null as AskScope | null,
    askPrefill: '',
    theme: readPersistedTheme(),
    locale: readPersistedLocale(),
  }),
  actions: {
    initTheme() {
      applyTheme(this.theme)
    },
    setTheme(theme: Theme) {
      this.theme = theme
      applyTheme(theme)
    },
    toggleTheme() {
      this.setTheme(this.theme === 'dark' ? 'light' : 'dark')
    },
    setLocale(locale: Locale) {
      this.locale = locale
      applyLocale(locale)
    },
    toggleLocale() {
      this.setLocale(this.locale === 'zh' ? 'en' : 'zh')
    },
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
