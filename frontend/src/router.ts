import { createRouter, createWebHistory } from 'vue-router'
import LandingPage from './pages/LandingPage.vue'
import ConnectWhatsAppPage from './pages/ConnectWhatsAppPage.vue'
import SelectChatsPage from './pages/SelectChatsPage.vue'
import AuthTelegramPage from './pages/AuthTelegramPage.vue'
import MapChatsPage from './pages/MapChatsPage.vue'
import MigrationPage from './pages/MigrationPage.vue'
import CompletionPage from './pages/CompletionPage.vue'

const routes = [
  {
    path: '/',
    name: 'Landing',
    component: LandingPage
  },
  {
    path: '/whatsapp',
    name: 'ConnectWhatsApp',
    component: ConnectWhatsAppPage
  },
  {
    path: '/select',
    name: 'SelectChats',
    component: SelectChatsPage
  },
  {
    path: '/telegram',
    name: 'AuthTelegram',
    component: AuthTelegramPage
  },
  {
    path: '/map',
    name: 'MapChats',
    component: MapChatsPage
  },
  {
    path: '/migrate',
    name: 'Migration',
    component: MigrationPage
  },
  {
    path: '/done',
    name: 'Completion',
    component: CompletionPage
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

