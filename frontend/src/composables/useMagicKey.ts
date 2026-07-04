import { onMounted, onUnmounted } from 'vue'

export function useMagicKey(handler: (e: KeyboardEvent) => void) {
  function listener(e: KeyboardEvent) {
    handler(e)
  }
  onMounted(() => window.addEventListener('keydown', listener))
  onUnmounted(() => window.removeEventListener('keydown', listener))
}
