<template>
  <div class="done-page">
    <div class="done-card">
      <span class="success-icon">✅</span>
      <h2>Миграция завершена!</h2>
      
      <div class="summary">
        <div class="summary-item">
          <span class="label">Обработано сообщений:</span>
          <span class="value">{{ status?.processed || 0 }} / {{ status?.total || 0 }}</span>
        </div>
        
        <div v-if="status?.errors && status.errors.length > 0" class="summary-item error">
          <span class="label">Ошибок:</span>
          <span class="value">{{ status.errors.length }}</span>
        </div>
      </div>
      
      <div v-if="status?.errors && status.errors.length > 0" class="errors-section">
        <h3>Список ошибок:</h3>
        <div class="errors-list">
          <div v-for="(error, index) in status.errors" :key="index" class="error-item">
            {{ error }}
          </div>
        </div>
      </div>
      
      <div class="actions">
        <button @click="openTelegram" class="btn-primary">
          Открыть чат в Telegram
        </button>
        <button @click="startNew" class="btn-secondary">
          Начать новую миграцию
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { useMigrationStore } from '../store/migration'

export default {
  name: 'Done',
  setup() {
    const store = useMigrationStore()
    return { store }
  },
  computed: {
    status() {
      return this.store.migrationStatus
    }
  },
  methods: {
    openTelegram() {
      // Open Telegram chat
      const chatId = this.store.selectedChatId
      if (chatId) {
        window.open(`https://t.me/c/${chatId.toString().replace('-100', '')}`, '_blank')
      } else {
        window.open('https://t.me', '_blank')
      }
    },
    
    startNew() {
      this.store.reset()
      this.$router.push('/')
    }
  }
}
</script>

<style scoped>
.done-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}

.done-card {
  background: white;
  border-radius: 16px;
  padding: 3rem;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  max-width: 600px;
  width: 100%;
  text-align: center;
}

.success-icon {
  font-size: 5rem;
  display: block;
  margin-bottom: 1rem;
}

.done-card h2 {
  color: #333;
  font-size: 2rem;
  margin-bottom: 2rem;
}

.summary {
  margin: 2rem 0;
  text-align: left;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  padding: 1rem;
  background: #f8f9ff;
  border-radius: 8px;
  margin-bottom: 0.5rem;
}

.summary-item.error {
  background: #fee;
}

.label {
  color: #666;
  font-weight: 600;
}

.value {
  color: #333;
  font-weight: 600;
}

.errors-section {
  margin: 2rem 0;
  text-align: left;
}

.errors-section h3 {
  color: #c33;
  margin-bottom: 1rem;
  font-size: 1.2rem;
}

.errors-list {
  max-height: 200px;
  overflow-y: auto;
}

.error-item {
  padding: 0.5rem;
  background: #fee;
  color: #c33;
  border-radius: 4px;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 2rem;
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

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
}

.btn-secondary {
  background: transparent;
  color: #667eea;
  border: 2px solid #667eea;
  padding: 1rem 2rem;
  font-size: 1.1rem;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
}

.btn-secondary:hover {
  background: #f8f9ff;
}
</style>
