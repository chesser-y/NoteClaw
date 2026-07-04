<script setup lang="ts">
import { computed, ref } from 'vue'
import { FileText, Image, Network, Presentation, Sparkles, Video } from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import { createGenerationTask, previewGeneration } from '../api/generate'
import { createHarnessJob } from '../api/harness'
import type { GenerationPreviewResponse, GenerationTaskResponse, GenerationType } from '../api/types'

const generationTypes: Array<{
  value: GenerationType
  label: string
  description: string
  icon: typeof FileText
}> = [
  { value: 'learning_note', label: '学习笔记', description: '按课程笔记结构整理知识点', icon: FileText },
  { value: 'technical_summary', label: '技术总结', description: '输出工程视角的技术摘要', icon: Sparkles },
  { value: 'report_draft', label: '报告草稿', description: '生成技术报告或项目文档', icon: FileText },
  { value: 'ppt_outline', label: 'PPT 大纲', description: '返回结构化 slide JSON', icon: Presentation },
  { value: 'pptx', label: '真实 PPTX', description: '异步生成 .pptx 和配图', icon: Presentation },
  { value: 'mind_map', label: '思维导图', description: '生成 Mermaid mindmap', icon: Network },
  { value: 'image', label: '图片', description: '基于知识库调用生图 API', icon: Image },
  { value: 'diagram', label: '图示', description: '生成架构图或流程图', icon: Network },
  { value: 'video_script', label: '视频脚本', description: '生成讲解脚本和分镜', icon: Video },
]

const selectedType = ref<GenerationType>('ppt_outline')
const prompt = ref('基于知识库生成项目介绍 PPT 大纲')
const tags = ref('rag,hackathon')
const slideCount = ref(6)
const includeImages = ref(true)
const loading = ref(false)
const preview = ref<GenerationPreviewResponse | null>(null)
const task = ref<GenerationTaskResponse | null>(null)
const harnessTask = ref('')
const error = ref('')

const selectedMeta = computed(() => generationTypes.find((type) => type.value === selectedType.value))

function scope() {
  return {
    note_ids: [],
    tags: tags.value
      .split(',')
      .map((tag) => tag.trim())
      .filter(Boolean),
    content_types: [],
  }
}

async function runPreview() {
  loading.value = true
  error.value = ''
  preview.value = null
  task.value = null
  try {
    preview.value = await previewGeneration({
      generation_type: selectedType.value,
      prompt: prompt.value,
      scope: scope(),
      options: {
        slide_count: slideCount.value,
        theme: 'dark_academic',
        include_generated_images: includeImages.value,
      },
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

async function runAsyncGeneration() {
  loading.value = true
  error.value = ''
  preview.value = null
  task.value = null
  try {
    task.value = await createGenerationTask({
      generation_type: selectedType.value,
      prompt: prompt.value,
      scope: scope(),
      options: {
        slide_count: slideCount.value,
        theme: 'dark_academic',
        include_generated_images: includeImages.value,
        output_format: selectedType.value === 'pptx' ? 'pptx' : null,
      },
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

async function runHarnessResearch() {
  loading.value = true
  error.value = ''
  harnessTask.value = ''
  try {
    const response = await createHarnessJob({
      job_type: 'web_research',
      instruction: '围绕当前生成主题自动搜集网页、论文、新闻或代码仓库资料。',
      inputs: { query: prompt.value, tags: scope().tags },
    })
    harnessTask.value = response.task_id
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="content-wrap">
    <PageHeader
      eyebrow="Generation"
      title="内容生成"
      description="基于知识库生成学习笔记、技术总结、报告草稿、PPT 大纲、PPTX、图示、图片和视频脚本。耗时任务统一进入任务中心。"
    />

    <div class="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
      <aside class="surface-soft p-5">
        <h2 class="mb-4 text-lg text-white">生成类型</h2>
        <div class="space-y-2">
          <button
            v-for="type in generationTypes"
            :key="type.value"
            class="w-full border p-3 text-left transition"
            :class="
              selectedType === type.value
                ? 'border-[#d9d2bf] bg-[#202320]'
                : 'border-[#303534] bg-[#141717] hover:border-[#4c5652]'
            "
            type="button"
            @click="selectedType = type.value"
          >
            <div class="mb-1 flex items-center gap-2 text-white">
              <component :is="type.icon" :size="16" />
              {{ type.label }}
            </div>
            <div class="text-sm text-[#8f9996]">{{ type.description }}</div>
          </button>
        </div>
      </aside>

      <div class="space-y-6">
        <form class="surface-soft p-5" @submit.prevent="runPreview">
          <div class="mb-4 flex items-center justify-between gap-4">
            <div>
              <h2 class="text-lg text-white">{{ selectedMeta?.label }}</h2>
              <p class="text-sm text-[#8f9996]">{{ selectedMeta?.description }}</p>
            </div>
            <span class="chip">{{ selectedType }}</span>
          </div>

          <label class="mb-4 block">
            <span class="mb-2 block text-sm text-[#a9b1ae]">生成要求</span>
            <textarea v-model="prompt" class="field textarea min-h-[140px]"></textarea>
          </label>

          <div class="mb-5 grid gap-4 md:grid-cols-3">
            <label>
              <span class="mb-2 block text-sm text-[#a9b1ae]">标签范围</span>
              <input v-model="tags" class="field" placeholder="rag,hackathon" />
            </label>
            <label>
              <span class="mb-2 block text-sm text-[#a9b1ae]">页数 / 段落数</span>
              <input v-model.number="slideCount" class="field" min="1" max="20" type="number" />
            </label>
            <label class="flex items-end gap-3 pb-3 text-sm text-[#c9cfcc]">
              <input v-model="includeImages" type="checkbox" />
              生成配图
            </label>
          </div>

          <div class="flex flex-wrap justify-end gap-3">
            <button class="btn" type="button" :disabled="loading" @click="runHarnessResearch">
              <Network :size="16" />
              nanobot 搜集资料
            </button>
            <button class="btn" type="button" :disabled="loading" @click="runAsyncGeneration">
              <Sparkles :size="16" />
              创建异步任务
            </button>
            <button class="btn btn-primary" type="submit" :disabled="loading">
              <Presentation :size="16" />
              生成预览
            </button>
          </div>
        </form>

        <div v-if="error" class="border border-[#70433b] bg-[#261716] p-4 text-sm text-[#f0b8ad]">
          {{ error }}
        </div>

        <div v-if="task" class="surface p-5">
          <h3 class="mb-2 text-lg text-white">异步任务已创建</h3>
          <p class="text-sm text-[#9aa3a0]">任务 ID：{{ task.task_id }} / 状态：{{ task.status }}</p>
        </div>

        <div v-if="harnessTask" class="surface p-5">
          <h3 class="mb-2 text-lg text-white">Nanobot 搜集任务已创建</h3>
          <p class="text-sm text-[#9aa3a0]">任务 ID：{{ harnessTask }}</p>
        </div>

        <div v-if="preview" class="surface p-5">
          <h3 class="mb-4 text-lg text-white">预览结果</h3>
          <pre class="overflow-auto border border-[#303534] bg-[#0e1010] p-4 text-sm leading-6 text-[#dce2df]">{{
            typeof preview.content === 'string' ? preview.content : JSON.stringify(preview.content, null, 2)
          }}</pre>
        </div>
      </div>
    </div>
  </section>
</template>
