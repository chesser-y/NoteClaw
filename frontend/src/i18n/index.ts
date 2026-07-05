import { createI18n } from 'vue-i18n'
import zh from './locales/zh.json'
import en from './locales/en.json'

export type Locale = 'zh' | 'en'

const STORAGE_KEY = 'noteclaw.locale'

function readPersisted(): Locale {
  const stored = localStorage.getItem(STORAGE_KEY)
  return stored === 'en' ? 'en' : 'zh'
}

export const i18n = createI18n({
  legacy: false,
  locale: readPersisted(),
  fallbackLocale: 'zh',
  messages: { zh, en },
})

export function setLocale(locale: Locale) {
  i18n.global.locale.value = locale
  localStorage.setItem(STORAGE_KEY, locale)
  document.documentElement.lang = locale
}

export function getLocale(): Locale {
  return i18n.global.locale.value as Locale
}
