<template>
  <div class="page">
    <div class="card">
      <h2>Выбор чатов</h2>
      <p class="description">Выберите чаты для переноса:</p>
      
      <div v-if="loading" class="empty-state">
        <p>Загрузка чатов...</p>
      </div>

      <div v-else-if="error" class="error-message">
        {{ error }}
      </div>

      <div v-else-if="store.whatsappChats.length > 0" class="chats-list">
        <div 
          v-for="chat in store.whatsappChats" 
          :key="chat.id"
          class="chat-item"
          :class="{ selected: isSelected(chat.id) }"
          @click="toggleChat(chat.id)"
        >
          <div class="chat-avatar">
            {{ chat.name.charAt(0).toUpperCase() }}
          </div>
          <div class="chat-info">
            <div class="chat-name">{{ chat.name }}</div>
            <div class="chat-meta">
              <span class="chat-type">{{ chat.type === 'personal' ? 'Личный' : 'Группа' }}</span>
              <span class="chat-count">{{ chat.messageCount || 0 }} сообщений</span>
            </div>
          </div>
          <div class="chat-checkbox">
            <input 
              type="checkbox" 
              :checked="isSelected(chat.id)"
              @change="toggleChat(chat.id)"
            />
          </div>
        </div>
      </div>
      
      <div v-else class="empty-state">
        <p>Чаты не найдены</p>
      </div>

      <div class="nav-buttons">
        <button @click="goBack" class="btn btn-secondary">Назад</button>
        <button 
          @click="handleNext" 
          class="btn btn-primary" 
          :disabled="store.selectedWhatsAppChats.length === 0"
        >
          Далее
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { store } from '../store'
import api from '../api/client'

const router = useRouter()
const loading = ref(false)
const error = ref<string | null>(null)

async function loadChats() {
  if (!store.whatsappSessionId) {
    error.value = 'Сессия WhatsApp не найдена'
    return
  }

  loading.value = true
  error.value = null

  try {
    const response = await api.get(`/whatsapp/chats/${store.whatsappSessionId}`)
    // Transform API response to match store interface
    const chats = response.data.chats.map((chat: any) => ({
      id: chat.id,
      name: chat.name,
      type: chat.type,
      messageCount: chat.message_count || 0,
      avatar: chat.avatar,
    }))
    store.setWhatsAppChats(chats)
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Ошибка загрузки чатов'
  } finally {
    loading.value = false
  }
}

function isSelected(chatId: string): boolean {
  return store.selectedWhatsAppChats.includes(chatId)
}

function toggleChat(chatId: string) {
  const index = store.selectedWhatsAppChats.indexOf(chatId)
  if (index > -1) {
    store.selectedWhatsAppChats.splice(index, 1)
  } else {
    store.selectedWhatsAppChats.push(chatId)
  }
}

function goBack() {
  router.push('/whatsapp')
}

function handleNext() {
  if (store.selectedWhatsAppChats.length > 0) {
    router.push('/telegram')
  }
}

onMounted(() => {
  if (store.whatsappChats.length === 0) {
    loadChats()
  }
})
</script>

<style scoped>
.description {
  color: var(--text-secondary);
  margin-bottom: var(--spacing-md);
}

.chats-list {
  max-height: 400px;
  overflow-y: auto;
  margin: var(--spacing-md) 0;
}

.chat-item {
  display: flex;
  align-items: center;
  padding: var(--spacing-sm);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  margin-bottom: var(--spacing-sm);
  cursor: pointer;
  transition: background 0.2s;
}

.chat-item:hover {
  background: var(--secondary-color);
}

.chat-item.selected {
  border-color: var(--primary-color);
  background: rgba(102, 126, 234, 0.1);
}

.chat-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  color: var(--white);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  margin-right: var(--spacing-sm);
  flex-shrink: 0;
}

.chat-info {
  flex: 1;
}

.chat-name {
  font-weight: 600;
  margin-bottom: var(--spacing-xs);
}

.chat-meta {
  display: flex;
  gap: var(--spacing-sm);
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.chat-checkbox {
  margin-left: var(--spacing-sm);
}

.empty-state {
  text-align: center;
  padding: var(--spacing-lg);
  color: var(--text-secondary);
}

.error-message {
  color: var(--error-color, #e74c3c);
  padding: var(--spacing-md);
  background: rgba(231, 76, 60, 0.1);
  border-radius: var(--border-radius);
  margin-bottom: var(--spacing-md);
}
</style>

