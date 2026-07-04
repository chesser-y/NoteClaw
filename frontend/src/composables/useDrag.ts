import { onUnmounted, ref } from 'vue'

type Options = {
  initial?: number
  min?: number
  max?: number
  storageKey?: string
}

export function useHorizontalDrag(opts: Options = {}) {
  const initial = opts.initial ?? 482
  const min = opts.min ?? 280
  const max = opts.max ?? 720

  const persisted = opts.storageKey
    ? Number(localStorage.getItem(opts.storageKey)) || initial
    : initial

  const size = ref(Math.min(Math.max(persisted, min), max))
  let dragging = false
  let originLeft = 0

  function onMove(e: MouseEvent) {
    if (!dragging) return
    e.preventDefault()
    const next = Math.min(Math.max(e.clientX - originLeft, min), max)
    size.value = next
  }

  function onUp() {
    if (!dragging) return
    dragging = false
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
    if (opts.storageKey) {
      localStorage.setItem(opts.storageKey, String(size.value))
    }
  }

  function start(e: MouseEvent) {
    e.preventDefault()
    dragging = true
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
    const parent = (e.currentTarget as HTMLElement).parentElement
    const rect = parent?.getBoundingClientRect()
    originLeft = rect?.left ?? 0
  }

  if (typeof window !== 'undefined') {
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }

  onUnmounted(() => {
    if (typeof window !== 'undefined') {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  })

  return { size, start }
}
