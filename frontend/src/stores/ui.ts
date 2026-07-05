import { defineStore } from 'pinia'
import { setLocale as applyLocale } from '../i18n'
import type { Locale } from '../i18n'
import { router } from '../router'

export type AskScope = {
  noteIds: string[]
  title?: string
}

export type Theme = 'dark' | 'light'

const THEME_KEY = 'noteclaw.theme'
const LOCALE_KEY = 'noteclaw.locale'
const SIDEBAR_KEY = 'noteclaw.sidebarOpen'

function readPersistedTheme(): Theme {
  const stored = localStorage.getItem(THEME_KEY)
  return stored === 'light' ? 'light' : 'dark'
}

function readPersistedLocale(): Locale {
  const stored = localStorage.getItem(LOCALE_KEY)
  return stored === 'en' ? 'en' : 'zh'
}

function readInitialSidebarOpen(): boolean {
  const stored = localStorage.getItem(SIDEBAR_KEY)
  if (stored === 'true') return true
  if (stored === 'false') return false
  if (typeof window !== 'undefined') {
    return window.matchMedia('(min-width: 921px)').matches
  }
  return true
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
    askPrefillNonce: 0,
    sidebarOpen: readInitialSidebarOpen(),
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
      this.askPrefillNonce += 1
      this.askOpen = true
      if (router.currentRoute.value.path !== '/') {
        router.push('/')
      }
    },
    closeAsk() {
      this.askOpen = false
      this.askScope = null
      this.askPrefill = ''
    },
    openSidebar() {
      this.sidebarOpen = true
      localStorage.setItem(SIDEBAR_KEY, 'true')
    },
    closeSidebar() {
      this.sidebarOpen = false
      localStorage.setItem(SIDEBAR_KEY, 'false')
    },
    toggleSidebar() {
      this.sidebarOpen = !this.sidebarOpen
      localStorage.setItem(SIDEBAR_KEY, String(this.sidebarOpen))
    },
  },
})
