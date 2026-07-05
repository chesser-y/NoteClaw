import { createRouter, createWebHistory } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import InboxView from '../views/InboxView.vue'
import LibraryView from '../views/LibraryView.vue'
import ResearchView from '../views/ResearchView.vue'
import TasksView from '../views/TasksView.vue'
import TimelineView from '../views/TimelineView.vue'
import StudioView from '../views/StudioView.vue'
import ReviewView from '../views/ReviewView.vue'
import SettingsView from '../views/SettingsView.vue'
import QualityView from '../views/QualityView.vue'
import KnowledgeGraphView from '../views/KnowledgeGraphView.vue'
import FavoritesView from '../views/FavoritesView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: AppShell,
      children: [
        { path: '', name: 'inbox', component: InboxView },
        { path: 'library', name: 'library', component: LibraryView },
        { path: 'research', name: 'research', component: ResearchView },
        { path: 'tasks', name: 'tasks', component: TasksView },
        { path: 'timeline', name: 'timeline', component: TimelineView },
        { path: 'studio', name: 'studio', component: StudioView },
        { path: 'review', name: 'review', component: ReviewView },
        { path: 'favorites', name: 'favorites', component: FavoritesView },
        { path: 'settings', name: 'settings', component: SettingsView },
        { path: 'settings/quality', name: 'quality', component: QualityView },
        { path: 'graph', name: 'graph', component: KnowledgeGraphView },
        { path: 'home', redirect: { name: 'inbox' } },
        { path: 'generate', redirect: { name: 'studio' } },
        { path: 'ingest', redirect: { name: 'inbox' } },
        { path: 'chat/:id?', redirect: { name: 'inbox' } },
      ],
    },
  ],
})
