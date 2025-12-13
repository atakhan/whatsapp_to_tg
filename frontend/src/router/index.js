import { createRouter, createWebHistory } from 'vue-router'
import Welcome from '../pages/Welcome.vue'
import Upload from '../pages/Upload.vue'
import Auth from '../pages/Auth.vue'
import SelectChat from '../pages/SelectChat.vue'
import Progress from '../pages/Progress.vue'
import Done from '../pages/Done.vue'

const routes = [
  {
    path: '/',
    name: 'Welcome',
    component: Welcome
  },
  {
    path: '/upload',
    name: 'Upload',
    component: Upload
  },
  {
    path: '/auth',
    name: 'Auth',
    component: Auth
  },
  {
    path: '/select-chat',
    name: 'SelectChat',
    component: SelectChat
  },
  {
    path: '/progress',
    name: 'Progress',
    component: Progress
  },
  {
    path: '/done',
    name: 'Done',
    component: Done
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
