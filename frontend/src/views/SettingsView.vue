<script setup lang="ts">
import { API_BASE } from '../api/http'
import PageHeader from '../components/PageHeader.vue'
</script>

<template>
  <section class="content-wrap">
    <PageHeader
      eyebrow="Settings"
      title="系统设置"
      description="当前页面展示前端对接配置和后端能力边界。真实模型密钥仍由后端 .env 管理，不在浏览器保存。"
    />

    <div class="grid gap-6 xl:grid-cols-2">
      <div class="surface-soft p-5">
        <h2 class="mb-4 text-lg text-white">前端配置</h2>
        <div class="space-y-3 text-sm">
          <div class="flex justify-between gap-4 border-b border-[#303534] pb-3">
            <span class="text-[#8f9996]">API Base</span>
            <span class="text-right text-white">{{ API_BASE }}</span>
          </div>
          <div class="flex justify-between gap-4 border-b border-[#303534] pb-3">
            <span class="text-[#8f9996]">Framework</span>
            <span class="text-white">Vue 3 + Vite + Tailwind</span>
          </div>
          <div class="flex justify-between gap-4">
            <span class="text-[#8f9996]">Mode</span>
            <span class="text-white">Contract-first</span>
          </div>
        </div>
      </div>

      <div class="surface p-5">
        <h2 class="mb-4 text-lg text-white">后端能力边界</h2>
        <div class="grid gap-3 text-sm text-[#c9cfcc]">
          <div class="chip w-fit">SQLite 元数据</div>
          <div class="chip w-fit">FAISS 向量检索</div>
          <div class="chip w-fit">OpenAI-compatible LLM</div>
          <div class="chip w-fit">OCR + Vision 异步理解</div>
          <div class="chip w-fit">python-pptx 真实 PPTX</div>
          <div class="chip w-fit">nanobot Harness 预留</div>
        </div>
      </div>
    </div>
  </section>
</template>
