<template>
  <div class="select-chat-page">
    <div class="select-chat-card">
      <h2>Выберите чат для переноса</h2>
      <p class="description">
        Найдено сообщений: {{ store.parsedMessagesCount }}
      </p>
      
      <div v-if="loading" class="loading">
        <div class="spinner"></div>
        <p>Загрузка контактов...</p>
      </div>
      
      <div v-if="!loading && contacts.length > 0" class="contacts-list">
        <div 
          v-for="contact in contacts"
          :key="contact.id"
          @click="selectChat(contact)"
          class="contact-item"
          :class="{ 'selected': selectedChatId === contact.id }"
        >
          <div class="contact-avatar">
            {{ contact.name.charAt(0).toUpperCase() }}
          </div>
          <div class="contact-info">
            <div class="contact-name">{{ contact.name }}</div>
            <div class="contact-type">
              {{ getContactType(contact) }}
            </div>
          </div>
          <div v-if="selectedChatId === contact.id" class="check-icon">✓</div>
        </div>
      </div>
      
      <div v-if="!loading && contacts.length === 0" class="no-contacts">
        <p>Контакты не найдены</p>
      </div>
      
      <div v-if="error" class="error-message">
        {{ error }}
      </div>
      
      <div v-if="selectedChatId" class="actions">
        <button @click="startMigration" class="btn-primary" :disabled="migrating">
          {{ migrating ? 'Запуск...' : 'Начать миграцию' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { useMigrationStore } from '../store/migration'
import api from '../api/client'

export default {
  name: 'SelectChat',
  data() {
    return {
      contacts: [],
      loading: true,
      selectedChatId: null,
      selectedChatName: '',
      error: null,
      migrating: false
    }
  },
  setup() {
    const store = useMigrationStore()
    return { store }
  },
  async mounted() {
    await this.loadContacts()
  },
  methods: {
    async loadContacts() {
      this.loading = true
      this.error = null
      
      try {
        const response = await api.post('/telegram/contacts', {
          user_id: this.store.userTelegramId
        })
        
        this.contacts = response.data.contacts
        this.loading = false
      } catch (error) {
        this.error = error.response?.data?.detail || 'Ошибка загрузки контактов'
        this.loading = false
      }
    },
    
    selectChat(contact) {
      this.selectedChatId = contact.id
      this.selectedChatName = contact.name
      this.store.setSelectedChat(contact.id, contact.name)
    },
    
    getContactType(contact) {
      if (contact.is_user) return 'Пользователь'
      if (contact.is_group) return 'Группа'
      if (contact.is_channel) return 'Канал'
      return 'Чат'
    },
    
    async startMigration() {
      if (!this.selectedChatId) {
        this.error = 'Выберите чат'
        return
      }
      
      this.migrating = true
      this.error = null
      
      try {
        await api.post('/migrate/start', {
          session_id: this.store.sessionId,
          user_id: this.store.userTelegramId,
          target_chat_id: this.selectedChatId
        })
        
        this.$router.push('/progress')
      } catch (error) {
        this.error = error.response?.data?.detail || 'Ошибка запуска миграции'
        this.migrating = false
      }
    }
  }
}
</script>

<style scoped>
.select-chat-page {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  min-height: 60vh;
  padding: 2rem 0;
}

.select-chat-card {
  background: white;
  border-radius: 16px;
  padding: 2rem;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  max-width: 600px;
  width: 100%;
}

.select-chat-card h2 {
  color: #333;
  font-size: 2rem;
  margin-bottom: 0.5rem;
  text-align: center;
}

.description {
  color: #666;
  text-align: center;
  margin-bottom: 2rem;
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 2rem;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.contacts-list {
  max-height: 500px;
  overflow-y: auto;
  margin-bottom: 2rem;
}

.contact-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  border: 2px solid #f0f0f0;
  border-radius: 8px;
  margin-bottom: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;
}

.contact-item:hover {
  border-color: #667eea;
  background: #f8f9ff;
}

.contact-item.selected {
  border-color: #667eea;
  background: #f0f4ff;
}

.contact-avatar {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  font-weight: 600;
}

.contact-info {
  flex: 1;
}

.contact-name {
  font-weight: 600;
  color: #333;
  margin-bottom: 0.25rem;
}

.contact-type {
  font-size: 0.9rem;
  color: #666;
}

.check-icon {
  color: #667eea;
  font-size: 1.5rem;
  font-weight: 600;
}

.no-contacts {
  text-align: center;
  padding: 2rem;
  color: #666;
}

.actions {
  margin-top: 2rem;
  text-align: center;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 1rem 2rem;
  font-size: 1.1rem;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
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
</style>
