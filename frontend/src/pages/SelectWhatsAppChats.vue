<template>
  <div class="select-chats-page">
    <div class="chats-card">
      <h2>Выбор чатов для переноса</h2>
      <p class="description">
        Выберите один или несколько чатов для переноса в Telegram
      </p>
      
      <div v-if="loading" class="loading">
        <div class="spinner"></div>
        <p>Загрузка чатов...</p>
      </div>
      
      <div v-if="!loading && chats.length === 0" class="no-chats">
        <p>Чаты не найдены</p>
      </div>
      
      <div v-if="!loading && chats.length > 0" class="chats-list">
        <div 
          v-for="chat in chats" 
          :key="chat.id"
          class="chat-item"
          :class="{ selected: isSelected(chat.id) }"
          @click="toggleChat(chat.id)"
        >
          <div class="chat-avatar">
            <span v-if="!chat.avatar" class="avatar-placeholder">
              {{ chat.name.charAt(0).toUpperCase() }}
            </span>
            <img v-else :src="chat.avatar" :alt="chat.name" />
          </div>
          <div class="chat-info">
            <div class="chat-name">{{ chat.name }}</div>
            <div class="chat-meta">
              <span class="chat-type">{{ chat.type === 'group' ? 'Группа' : 'Личный чат' }}</span>
              <span class="chat-separator">•</span>
              <span class="chat-count">{{ formatMessageCount(chat.message_count) }} сообщений</span>
            </div>
          </div>
          <div class="chat-checkbox">
            <input 
              type="checkbox" 
              :checked="isSelected(chat.id)"
              @change="toggleChat(chat.id)"
              @click.stop
            />
          </div>
        </div>
      </div>
      
      <div v-if="selectedChats.length > 0" class="selected-info">
        <p>Выбрано чатов: {{ selectedChats.length }}</p>
      </div>
      
      <div class="actions">
        <button 
          @click="continueToMapChats" 
          class="btn-primary"
          :disabled="selectedChats.length === 0"
        >
          Далее
        </button>
      </div>
      
      <div v-if="error" class="error-message">
        {{ error }}
      </div>
    </div>
  </div>
</template>

<script>
import { useMigrationStore } from '../store/migration'
import api from '../api/client'

export default {
  name: 'SelectWhatsAppChats',
  data() {
    return {
      chats: [],
      selectedChats: [],
      loading: true,
      error: null
    }
  },
  setup() {
    const store = useMigrationStore()
    return { store }
  },
  mounted() {
    this.loadChats()
  },
  methods: {
    async loadChats() {
      this.loading = true
      this.error = null
      
      try {
        const response = await api.get(`/whatsapp/${this.store.whatsappSessionId}/chats`)
        this.chats = response.data.chats
        this.store.setWhatsAppChats(this.chats)
      } catch (error) {
        this.error = error.response?.data?.detail || 'Ошибка загрузки чатов'
      } finally {
        this.loading = false
      }
    },
    
    toggleChat(chatId) {
      const index = this.selectedChats.indexOf(chatId)
      if (index > -1) {
        this.selectedChats.splice(index, 1)
      } else {
        this.selectedChats.push(chatId)
      }
      this.store.setSelectedWhatsAppChats(this.selectedChats)
    },
    
    isSelected(chatId) {
      return this.selectedChats.includes(chatId)
    },
    
    formatMessageCount(count) {
      if (count >= 1000) {
        return `${(count / 1000).toFixed(1)}k`
      }
      return count.toString()
    },
    
    continueToMapChats() {
      if (this.selectedChats.length === 0) {
        this.error = 'Выберите хотя бы один чат'
        return
      }
      this.$router.push('/auth')
    }
  }
}
</script>

<style scoped>
.select-chats-page {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  min-height: 60vh;
  padding: 2rem 0;
}

.chats-card {
  background: white;
  border-radius: 16px;
  padding: 2rem;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  max-width: 800px;
  width: 100%;
}

.chats-card h2 {
  color: #333;
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.description {
  color: #666;
  margin-bottom: 2rem;
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 3rem;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #25D366;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.chats-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 500px;
  overflow-y: auto;
  margin-bottom: 1rem;
}

.chat-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.chat-item:hover {
  border-color: #25D366;
  background: #f5f5f5;
}

.chat-item.selected {
  border-color: #25D366;
  background: #e8f5e9;
}

.chat-avatar {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
}

.avatar-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
  color: white;
  font-size: 1.5rem;
  font-weight: 600;
}

.chat-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.chat-info {
  flex: 1;
  min-width: 0;
}

.chat-name {
  font-size: 1.1rem;
  font-weight: 600;
  color: #333;
  margin-bottom: 0.25rem;
}

.chat-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  color: #666;
}

.chat-separator {
  color: #999;
}

.chat-checkbox {
  flex-shrink: 0;
}

.chat-checkbox input[type="checkbox"] {
  width: 20px;
  height: 20px;
  cursor: pointer;
}

.selected-info {
  padding: 1rem;
  background: #e8f5e9;
  border-radius: 8px;
  margin-bottom: 1rem;
  text-align: center;
  font-weight: 600;
  color: #2e7d32;
}

.actions {
  display: flex;
  justify-content: flex-end;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 1rem 2rem;
  font-size: 1.1rem;
  border-radius: 8px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  font-weight: 600;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-message {
  margin-top: 1rem;
  padding: 1rem;
  background: #fee;
  color: #c33;
  border-radius: 8px;
  text-align: center;
}

.no-chats {
  text-align: center;
  padding: 3rem;
  color: #666;
}
</style>

