import { createRouter, createWebHistory } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import LibraryView from '../views/LibraryView.vue'
import IngestView from '../views/IngestView.vue'
import ChatView from '../views/ChatView.vue'
import GenerateView from '../views/GenerateView.vue'
import TasksView from '../views/TasksView.vue'
import SettingsView from '../views/SettingsView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: AppShell,
      redirect: '/library',
      children: [
        { path: 'library', name: 'library', component: LibraryView },
        { path: 'ingest', name: 'ingest', component: IngestView },
        { path: 'chat', name: 'chat', component: ChatView },
        { path: 'generate', name: 'generate', component: GenerateView },
        { path: 'tasks', name: 'tasks', component: TasksView },
        { path: 'settings', name: 'settings', component: SettingsView },
      ],
    },
  ],
})
