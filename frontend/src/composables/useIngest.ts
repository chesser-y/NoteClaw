import { computed, ref } from 'vue'
import { ingestContent, ingestFile } from '../api/ingest'
import type { ContentType, IngestResponse } from '../api/types'

export type IngestKind = 'text' | 'code' | 'image' | 'document' | 'unknown'

export type PreviewState = {
  kind: IngestKind
  contentType: ContentType
  title: string
  raw: string
  file?: File
  language?: string
  summary: string
  tags: string[]
  related: { id: string; title: string; type: ContentType }[]
  source: string
}

export type BatchItem = {
  file: File
  status: 'queued' | 'uploading' | 'done' | 'failed'
  error?: string
  response?: IngestResponse
}

export type BatchState = {
  items: BatchItem[]
  running: boolean
}

function detectCodeLanguage(text: string): string | undefined {
  const head = text.slice(0, 200)
  if (/^\s*(import|from|def|class)\s/m.test(head) && /:\s*$|^\s*def\s/m.test(text)) return 'python'
  if (/^\s*(import|export|const|let|function)\s/m.test(head)) return 'javascript'
  if (/^\s*(package|func|import)\s/m.test(head)) return 'go'
  if (/<\/?[a-z]+[\s>]/i.test(head)) return 'html'
  return undefined
}

function detectKind(text: string): { kind: IngestKind; contentType: ContentType; language?: string } {
  const trimmed = text.trim()
  if (!trimmed) return { kind: 'unknown', contentType: 'text' }
  const lang = detectCodeLanguage(trimmed)
  if (lang) return { kind: 'code', contentType: 'code', language: lang }
  if (/^\s*\|.*\|\s*$/.test(trimmed) && /\n.*\|.*\|/.test(trimmed)) {
    return { kind: 'text', contentType: 'table' }
  }
  return { kind: 'text', contentType: 'text' }
}

function fileContentType(file: File): ContentType {
  if (file.type.startsWith('image/')) return 'image'
  if (file.type === 'application/pdf' || file.name.endsWith('.pdf')) return 'document'
  if (/\.(md|txt|csv|json|html)$/i.test(file.name)) return 'document'
  if (/\.(py|ts|js|go|rs|java|cpp|c|sh)$/i.test(file.name)) return 'code'
  return 'document'
}

function buildStubSummary(text: string): string {
  const lines = text.split(/\n+/).filter(Boolean).slice(0, 3).join(' ')
  return lines.length > 140 ? lines.slice(0, 140) + '…' : lines || '（暂无可识别内容）'
}

function buildStubTags(contentType: ContentType, language?: string): string[] {
  const base: Record<ContentType, string[]> = {
    text: ['笔记'],
    code: ['代码', language ?? 'snippet'].filter(Boolean) as string[],
    table: ['表格'],
    image: ['图片'],
    document: ['文档'],
    webpage: ['网页'],
    repository: ['仓库'],
  }
  return base[contentType] ?? []
}

export function useIngest() {
  const preview = ref<PreviewState | null>(null)
  const saving = ref(false)
  const lastResponse = ref<IngestResponse | null>(null)
  const error = ref('')

  const batch = ref<BatchState>({ items: [], running: false })

  const batchProgress = computed(() => {
    const total = batch.value.items.length
    const done = batch.value.items.filter((i) => i.status === 'done' || i.status === 'failed').length
    return { total, done, pct: total ? Math.round((done / total) * 100) : 0 }
  })

  function fileContentTypeLocal(file: File): ContentType {
    return fileContentType(file)
  }

  async function uploadFiles(files: File[] | FileList, sourcePrefix = 'upload') {
    const list = Array.from(files)
    if (!list.length) return
    batch.value = {
      items: list.map((file) => ({ file, status: 'queued' as const })),
      running: true,
    }
    const concurrency = 4
    const queue = [...batch.value.items]
    async function worker() {
      while (queue.length) {
        const item = queue.shift()!
        item.status = 'uploading'
        try {
          const contentType = fileContentTypeLocal(item.file)
          const source = item.file.webkitRelativePath
            ? `${sourcePrefix}:${item.file.webkitRelativePath.split('/')[0]}`
            : sourcePrefix
          item.response = await ingestFile(item.file, contentType, source)
          item.status = 'done'
        } catch (e) {
          item.error = e instanceof Error ? e.message : String(e)
          item.status = 'failed'
        }
      }
    }
    await Promise.all(Array.from({ length: Math.min(concurrency, list.length) }, worker))
    batch.value.running = false
  }

  function clearBatch() {
    batch.value = { items: [], running: false }
  }

  function fromText(text: string): PreviewState | null {
    const detected = detectKind(text)
    if (detected.kind === 'unknown') return null
    return {
      kind: detected.kind,
      contentType: detected.contentType,
      title: text.trim().slice(0, 60) || '未命名片段',
      raw: text,
      language: detected.language,
      summary: buildStubSummary(text),
      tags: buildStubTags(detected.contentType, detected.language),
      related: [],
      source: 'paste',
    }
  }

  function fromFile(file: File): PreviewState {
    const contentType = fileContentType(file)
    return {
      kind: contentType === 'image' ? 'image' : 'document',
      contentType,
      title: file.name,
      raw: '',
      file,
      summary:
        contentType === 'image'
          ? '图片已就绪，可在保存后由视觉模型自动描述。'
          : '文档已就绪，可在保存后由后端抽取摘要与标签。',
      tags: buildStubTags(contentType),
      related: [],
      source: 'upload',
    }
  }

  function setPreview(state: PreviewState) {
    preview.value = state
  }

  function clear() {
    preview.value = null
    error.value = ''
    lastResponse.value = null
  }

  async function save() {
    if (!preview.value || saving.value) return
    saving.value = true
    error.value = ''
    try {
      const p = preview.value
      if (p.file) {
        lastResponse.value = await ingestFile(p.file, p.contentType, p.source)
      } else {
        lastResponse.value = await ingestContent({
          content_type: p.contentType,
          content: p.raw,
          title: p.title,
          source: p.source,
          metadata: p.language ? { language: p.language } : undefined,
        })
      }
      preview.value = null
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      saving.value = false
    }
  }

  return {
    preview,
    saving,
    error,
    lastResponse,
    batch,
    batchProgress,
    uploadFiles,
    clearBatch,
    fromText,
    fromFile,
    setPreview,
    clear,
    save,
  }
}
