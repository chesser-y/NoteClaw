<script setup lang="ts">
import { ref } from 'vue'
import { Eye, MessageSquareText, Smile, Flame } from "lucide-vue-next"

const tab = ref<'for-me' | 'active' | 'recent'>('for-me')

type Finding = {
  topic: string
  status: 'on-track' | 'at-risk'
  author: string
  time: string
  body: string
  bullets?: string[]
  reactions: { icon: string; count: number }[]
}

const groups: { date: string; items: Finding[] }[] = []

const iconFor = (id: string) => {
  if (id === 'flame') return Flame
  if (id === 'eyes') return Eye
  return Smile
}

function react(item: Finding, idx: number) {
  item.reactions[idx].count += 1
}
</script>

<template>
  <section class="research-view">
    <header class="topbar tight">
      <span>Research</span>
      <span class="spacer"></span>
    </header>

    <header class="topbar tight">
      <button class="tab" :class="{ active: tab === 'for-me' }" @click="tab = 'for-me'">For me</button>
      <button class="tab" :class="{ active: tab === 'active' }" @click="tab = 'active'">Active</button>
      <button class="tab" :class="{ active: tab === 'recent' }" @click="tab = 'recent'">Recent</button>
    </header>

    <div class="feed">
      <div v-if="!groups.length" class="placeholder" style="padding: 60px 16px; font-size: 13px;">
        暂无研究动态
      </div>
      <div v-for="group in groups" :key="group.date">
        <div class="date-rule">{{ group.date }}</div>
        <article
          v-for="(item, i) in group.items"
          :key="i"
          class="pulse-item"
        >
          <span class="dot-menu" style="position: absolute; top: 0; right: 6px;">...</span>
          <h2>{{ item.topic }}</h2>
          <div class="pulse-status">
            <span :class="['health', { risk: item.status === 'at-risk' }]">
              {{ item.status === 'on-track' ? '↗ On track' : '↗ At risk' }}
            </span>
            <span>{{ item.author }}</span>
            <span>{{ item.time }}</span>
          </div>
          <p>{{ item.body }}</p>
          <ul v-if="item.bullets">
            <li v-for="(b, bi) in item.bullets" :key="bi">{{ b }}</li>
          </ul>
          <div class="reaction-row">
            <span style="cursor: pointer;">▢</span>
            <button
              v-for="(r, ri) in item.reactions"
              :key="ri"
              class="pill square"
              style="cursor: pointer; text-transform: none;"
              @click="react(item, ri)"
            >
              <component :is="iconFor(r.icon)" :size="11" />
              {{ r.count }}
            </button>
            <MessageSquareText :size="14" style="cursor: pointer;" />
          </div>
          <div class="pulse-actions">
            <button class="btn btn-ghost" style="height: 28px; padding: 0 10px; font-size: 12px;">查看来源</button>
            <button class="btn btn-ghost" style="height: 28px; padding: 0 10px; font-size: 12px;">生成对比表</button>
            <button class="btn btn-ghost" style="height: 28px; padding: 0 10px; font-size: 12px;">加入 Timeline</button>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>

<style scoped>
.research-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow-y: auto;
}
</style>
