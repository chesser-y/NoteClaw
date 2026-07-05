<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ChevronRight, Activity, SlidersHorizontal, Boxes } from "lucide-vue-next"
import { useUiStore } from '../stores/ui'
import { API_BASE } from '../api/http'

const router = useRouter()
const ui = useUiStore()
const { t } = useI18n()
const tab = ref<'general' | 'advanced' | 'capabilities'>('general')
</script>

<template>
  <section class="settings-view">
    <header class="topbar tight">
      <span>Settings</span>
      <span class="spacer"></span>
    </header>

    <header class="topbar tight">
      <button class="tab" :class="{ active: tab === 'general' }" @click="tab = 'general'">General</button>
      <button class="tab" :class="{ active: tab === 'advanced' }" @click="tab = 'advanced'">Advanced</button>
      <button class="tab" :class="{ active: tab === 'capabilities' }" @click="tab = 'capabilities'">Capabilities</button>
    </header>

    <div v-if="tab === 'general'" style="padding: 28px; max-width: 880px; display: flex; flex-direction: column; gap: 14px;">
      <div class="surface" style="padding: 18px;">
        <h3 style="margin: 0 0 12px; color: var(--text); font-size: 14px; font-weight: 700;">前端配置</h3>
        <div class="side-meta">
          <div class="side-row">
            <span class="label">API Base</span>
            <span class="mono">{{ API_BASE }}</span>
          </div>
          <div class="side-row">
            <span class="label">Framework</span>
            <span>Vue 3 + Vite + Tailwind</span>
          </div>
          <div class="side-row">
            <span class="label">Mode</span>
            <span>Contract-first</span>
          </div>
        </div>
      </div>

      <div class="surface" style="padding: 18px;">
        <h3 style="margin: 0 0 12px; color: var(--text); font-size: 14px; font-weight: 700;">{{ t('settings.preferences') }}</h3>
        <div class="side-meta">
          <div class="side-row">
            <span class="label">{{ t('menu.theme') }}</span>
            <div class="seg" style="display: inline-flex; background: var(--panel-2); border-radius: 6px; padding: 1px; gap: 1px;">
              <button
                type="button"
                :class="{ active: ui.theme === 'dark' }"
                style="border: 0; background: transparent; color: var(--muted); font-size: 12px; padding: 4px 10px; border-radius: 5px; cursor: pointer;"
                :style="ui.theme === 'dark' ? { background: 'var(--panel-3)', color: 'var(--text)' } : {}"
                @click="ui.setTheme('dark')"
              >{{ t('menu.theme-dark') }}</button>
              <button
                type="button"
                :class="{ active: ui.theme === 'light' }"
                style="border: 0; background: transparent; color: var(--muted); font-size: 12px; padding: 4px 10px; border-radius: 5px; cursor: pointer;"
                :style="ui.theme === 'light' ? { background: 'var(--panel-3)', color: 'var(--text)' } : {}"
                @click="ui.setTheme('light')"
              >{{ t('menu.theme-light') }}</button>
            </div>
          </div>
          <div class="side-row">
            <span class="label">{{ t('menu.language') }}</span>
            <div class="seg" style="display: inline-flex; background: var(--panel-2); border-radius: 6px; padding: 1px; gap: 1px;">
              <button
                type="button"
                :class="{ active: ui.locale === 'zh' }"
                style="border: 0; background: transparent; color: var(--muted); font-size: 12px; padding: 4px 10px; border-radius: 5px; cursor: pointer;"
                :style="ui.locale === 'zh' ? { background: 'var(--panel-3)', color: 'var(--text)' } : {}"
                @click="ui.setLocale('zh')"
              >{{ t('menu.lang-zh') }}</button>
              <button
                type="button"
                :class="{ active: ui.locale === 'en' }"
                style="border: 0; background: transparent; color: var(--muted); font-size: 12px; padding: 4px 10px; border-radius: 5px; cursor: pointer;"
                :style="ui.locale === 'en' ? { background: 'var(--panel-3)', color: 'var(--text)' } : {}"
                @click="ui.setLocale('en')"
              >{{ t('menu.lang-en') }}</button>
            </div>
          </div>
          <div class="side-row">
            <span class="label">{{ t('settings.default-retrieval') }}</span>
            <span class="mono">hybrid</span>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="tab === 'advanced'" style="padding: 28px; max-width: 880px; display: flex; flex-direction: column; gap: 14px;">
      <div
        class="card card-hover"
        style="padding: 18px; cursor: pointer;"
        @click="router.push('/settings/quality')"
      >
        <div style="display: flex; align-items: center; gap: 14px;">
          <div class="node-icon cyan"><Activity :size="14" /></div>
          <div style="flex: 1;">
            <div style="color: var(--text); font-size: 15px; font-weight: 700;">Quality & Evaluation</div>
            <div style="color: var(--muted); font-size: 12px; margin-top: 4px;">
              Recall@10 / MRR / Citation hit rate / Faithfulness / Latency 等核心指标
            </div>
          </div>
          <ChevronRight :size="16" style="color: var(--muted);" />
        </div>
      </div>

      <div class="card" style="padding: 18px;">
        <div style="display: flex; align-items: center; gap: 14px;">
          <div class="node-icon"><SlidersHorizontal :size="14" /></div>
          <div style="flex: 1;">
            <div style="color: var(--text); font-size: 15px; font-weight: 700;">Retrieval Tuning</div>
            <div style="color: var(--muted); font-size: 12px; margin-top: 4px;">
              top_k / 重排阈值 / hybrid 权重 (0.45 / 0.55)
            </div>
          </div>
          <span class="pill square">soon</span>
        </div>
      </div>

      <div class="card" style="padding: 18px;">
        <div style="display: flex; align-items: center; gap: 14px;">
          <div class="node-icon red"><Boxes :size="14" /></div>
          <div style="flex: 1;">
            <div style="color: var(--text); font-size: 15px; font-weight: 700;">Storage & Index</div>
            <div style="color: var(--muted); font-size: 12px; margin-top: 4px;">
              SQLite + FAISS 索引状态 / 重建 / 备份
            </div>
          </div>
          <span class="pill square">soon</span>
        </div>
      </div>
    </div>

    <div v-else style="padding: 28px; max-width: 880px;">
      <div class="surface" style="padding: 18px;">
        <h3 style="margin: 0 0 14px; color: var(--text); font-size: 14px; font-weight: 700;">后端能力边界</h3>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
          <span class="chip">SQLite 元数据</span>
          <span class="chip chip-blue">FAISS 向量检索</span>
          <span class="chip chip-green">OpenAI-compat LLM</span>
          <span class="chip chip-warn">OCR + Vision</span>
          <span class="chip">python-pptx PPTX</span>
          <span class="chip chip-blue">nanobot Harness</span>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.settings-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow-y: auto;
}
</style>
