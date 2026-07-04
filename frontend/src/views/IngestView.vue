<script setup lang="ts">
import { ref } from 'vue'
import { FileUp, Send, UploadCloud } from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import { ingestContent, ingestFile } from '../api/ingest'
import type { ContentType, IngestResponse } from '../api/types'

const contentType = ref<ContentType>('text')
const title = ref('')
const source = ref('manual')
const content = ref('')
const selectedFile = ref<File | null>(null)
const loading = ref(false)
const result = ref<IngestResponse | null>(null)
const error = ref('')

async function submitContent() {
  loading.value = true
  error.value = ''
  result.value = null
  try {
    result.value = await ingestContent({
      content_type: contentType.value,
      content: content.value,
      title: title.value || null,
      source: source.value || 'manual',
      source_url: null,
      metadata: {},
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

async function submitFile() {
  if (!selectedFile.value) return
  loading.value = true
  error.value = ''
  result.value = null
  try {
    result.value = await ingestFile(selectedFile.value, contentType.value, source.value || 'upload')
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
}
</script>

<template>
  <section class="content-wrap">
    <PageHeader
      eyebrow="Ingestion"
      title="信息输入"
      description="支持文本、代码、表格和图片。图片会先 OCR，再异步调用多模态模型补充视觉理解。"
    />

    <div class="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
      <form class="surface-soft p-5" @submit.prevent="submitContent">
        <div class="mb-5 grid gap-4 md:grid-cols-3">
          <label class="block">
            <span class="mb-2 block text-sm text-[#a9b1ae]">内容类型</span>
            <select v-model="contentType" class="field">
              <option value="text">文本</option>
              <option value="code">代码</option>
              <option value="table">表格</option>
              <option value="image">图片</option>
              <option value="document">文档</option>
            </select>
          </label>
          <label class="block">
            <span class="mb-2 block text-sm text-[#a9b1ae]">标题</span>
            <input v-model="title" class="field" placeholder="可留空，后端生成" />
          </label>
          <label class="block">
            <span class="mb-2 block text-sm text-[#a9b1ae]">来源</span>
            <input v-model="source" class="field" placeholder="manual / web / upload" />
          </label>
        </div>

        <label class="block">
          <span class="mb-2 block text-sm text-[#a9b1ae]">原始内容</span>
          <textarea
            v-model="content"
            class="field textarea"
            placeholder="粘贴课程笔记、论文摘录、代码片段、Markdown 表格或网页片段"
          ></textarea>
        </label>

        <div class="mt-5 flex justify-end">
          <button class="btn btn-primary" type="submit" :disabled="loading || !content.trim()">
            <Send :size="16" />
            提交入库
          </button>
        </div>
      </form>

      <aside class="surface p-5">
        <div class="mb-4 flex items-center gap-3">
          <UploadCloud :size="20" />
          <h2 class="text-lg text-white">文件上传</h2>
        </div>
        <p class="mb-5 text-sm leading-6 text-[#8f9996]">
          上传图片、截图、PDF 或其他文件。当前接口会返回任务 ID，后续由任务中心追踪 OCR、视觉理解和索引状态。
        </p>
        <label class="mb-4 block border border-dashed border-[#424b48] bg-[#151818] p-5 text-center">
          <FileUp :size="24" class="mx-auto mb-3 text-[#9aa3a0]" />
          <span class="block text-sm text-[#c9cfcc]">
            {{ selectedFile ? selectedFile.name : '选择文件' }}
          </span>
          <input class="hidden" type="file" @change="onFileChange" />
        </label>
        <button class="btn w-full" type="button" :disabled="loading || !selectedFile" @click="submitFile">
          <UploadCloud :size="16" />
          上传并入库
        </button>

        <div v-if="result" class="mt-5 border border-[#394541] bg-[#141817] p-4 text-sm leading-6">
          <div class="text-white">已创建知识条目：{{ result.note_id }}</div>
          <div class="text-[#9aa3a0]">任务：{{ result.task_id ?? '无' }}</div>
          <div class="text-[#9aa3a0]">状态：{{ result.status }}</div>
        </div>

        <div v-if="error" class="mt-5 border border-[#70433b] bg-[#261716] p-4 text-sm text-[#f0b8ad]">
          {{ error }}
        </div>
      </aside>
    </div>
  </section>
</template>
