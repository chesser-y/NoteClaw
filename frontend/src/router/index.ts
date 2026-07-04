import { createRouter, createWebHistory } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import HomeView from '../views/HomeView.vue'
import LibraryView from '../views/LibraryView.vue'
import TasksView from '../views/TasksView.vue'
import StudioView from '../views/StudioView.vue'
import SettingsView from '../views/SettingsView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: AppShell,
      children: [
        { path: '', name: 'home', component: HomeView },
        { path: 'library', name: 'library', component: LibraryView },
        { path: 'tasks', name: 'tasks', component: TasksView },
        { path: 'studio', name: 'studio', component: StudioView },
        { path: 'settings', name: 'settings', component: SettingsView },
        { path: 'generate', redirect: { name: 'studio' } },
        { path: 'ingest', redirect: { name: 'home' } },
      ],
    },
  ],
})
