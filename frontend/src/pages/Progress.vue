<template>
  <div class="progress-page">
    <div class="progress-card">
      <h2>Миграция в процессе</h2>
      
      <div class="progress-info">
        <div class="progress-bar-container">
          <div class="progress-bar" :style="{ width: progressPercent + '%' }"></div>
        </div>
        <div class="progress-text">
          {{ status.processed }} / {{ status.total }} сообщений
          ({{ progressPercent.toFixed(1) }}%)
        </div>
      </div>
      
      <div class="current-action">
        <p v-if="status.current_action">{{ status.current_action }}</p>
      </div>
      
      <div v-if="status.errors && status.errors.length > 0" class="errors-section">
        <h3>Ошибки:</h3>
        <div class="errors-list">
          <div v-for="(error, index) in status.errors" :key="index" class="error-item">
            {{ error }}
          </div>
        </div>
      </div>
      
      <div v-if="completed" class="completion-message">
        <span class="success-icon">✅</span>
        <p>Миграция завершена!</p>
        <button @click="goToDone" class="btn-primary">
          Продолжить
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { useMigrationStore } from '../store/migration'
import api from '../api/client'

export default {
  name: 'Progress',
  data() {
    return {
      status: {
        total: 0,
        processed: 0,
        percent: 0,
        current_action: '',
        errors: []
      },
      completed: false,
      pollInterval: null
    }
  },
  setup() {
    const store = useMigrationStore()
    return { store }
  },
  computed: {
    progressPercent() {
      if (this.status.total === 0) return 0
      return (this.status.processed / this.status.total) * 100
    }
  },
  mounted() {
    this.startPolling()
  },
  beforeUnmount() {
    this.stopPolling()
  },
  methods: {
    async fetchStatus() {
      try {
        const response = await api.get(`/migrate/status/${this.store.sessionId}`)
        this.status = response.data
        
        // Check if completed
        if (this.status.completed_at || this.status.processed >= this.status.total) {
          this.completed = true
          this.stopPolling()
          this.store.setMigrationStatus(this.status)
        }
      } catch (error) {
        console.error('Error fetching status:', error)
      }
    },
    
    startPolling() {
      this.fetchStatus()
      this.pollInterval = setInterval(() => {
        this.fetchStatus()
      }, 2000) // Poll every 2 seconds
    },
    
    stopPolling() {
      if (this.pollInterval) {
        clearInterval(this.pollInterval)
        this.pollInterval = null
      }
    },
    
    goToDone() {
      this.$router.push('/done')
    }
  }
}
</script>

<style scoped>
.progress-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}

.progress-card {
  background: white;
  border-radius: 16px;
  padding: 3rem;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  max-width: 600px;
  width: 100%;
  text-align: center;
}

.progress-card h2 {
  color: #333;
  font-size: 2rem;
  margin-bottom: 2rem;
}

.progress-info {
  margin-bottom: 2rem;
}

.progress-bar-container {
  width: 100%;
  height: 30px;
  background: #f0f0f0;
  border-radius: 15px;
  overflow: hidden;
  margin-bottom: 1rem;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 1.1rem;
  color: #666;
  font-weight: 600;
}

.current-action {
  margin: 2rem 0;
  padding: 1rem;
  background: #f8f9ff;
  border-radius: 8px;
}

.current-action p {
  color: #333;
  font-size: 1rem;
}

.errors-section {
  margin-top: 2rem;
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

.completion-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  margin-top: 2rem;
}

.success-icon {
  font-size: 4rem;
}

.completion-message p {
  font-size: 1.2rem;
  color: #333;
  font-weight: 600;
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
  margin-top: 1rem;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
}
</style>
