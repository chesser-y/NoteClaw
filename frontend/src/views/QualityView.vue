<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ChevronLeft } from "lucide-vue-next"

const router = useRouter()
</script>

<template>
  <section class="quality-view">
    <header class="topbar tight">
      <button class="btn btn-ghost" style="height: 32px; padding: 0 10px;" @click="router.push('/settings')">
        <ChevronLeft :size="14" />
        Settings
      </button>
      <span>Quality & Evaluation</span>
      <span class="spacer"></span>
    </header>

    <div class="insights">
      <div class="placeholder" style="padding: 80px 16px; font-size: 13px;">
        暂无评测数据
      </div>
    </div>
  </section>
</template>

<style scoped>
.quality-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow-y: auto;
}
</style>
