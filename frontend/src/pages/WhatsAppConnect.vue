<template>
  <div class="whatsapp-connect-page">
    <div class="connect-card">
      <h2>Подключение WhatsApp</h2>
      <p class="description">
        Откройте WhatsApp → Связанные устройства → Подключить устройство → Отсканируйте QR
      </p>
      
      <div v-if="status === 'qr_code' && qrCode" class="qr-container">
        <img :src="`data:image/png;base64,${qrCode}`" alt="QR Code" class="qr-code" />
        <p class="qr-hint">Отсканируйте QR-код в WhatsApp</p>
      </div>
      
      <div v-if="status === 'connecting'" class="connecting">
        <div class="spinner"></div>
        <p>Подключение...</p>
      </div>
      
      <div v-if="status === 'connected'" class="connected">
        <span class="success-icon">✅</span>
        <p>WhatsApp Web подключен!</p>
        <p class="info-text">
          Никакие данные не отправляются третьим лицам<br>
          Соединение временное
        </p>
        <button @click="continueToSelectChats" class="btn-primary">
          Далее
        </button>
      </div>
      
      <div v-if="status === 'disconnected'" class="disconnected">
        <button @click="createSession" class="btn-primary" :disabled="loading">
          {{ loading ? 'Создание сессии...' : 'Подключить WhatsApp Web' }}
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
  name: 'WhatsAppConnect',
  data() {
    return {
      status: 'disconnected',
      qrCode: null,
      loading: false,
      error: null,
      statusCheckInterval: null
    }
  },
  setup() {
    const store = useMigrationStore()
    return { store }
  },
  mounted() {
    this.createSession()
  },
  beforeUnmount() {
    if (this.statusCheckInterval) {
      clearInterval(this.statusCheckInterval)
    }
  },
  methods: {
    async createSession() {
      this.loading = true
      this.error = null
      
      try {
        const response = await api.post('/whatsapp/connect')
        this.store.setWhatsAppSessionId(response.data.session_id)
        await this.getQRCode(response.data.session_id)
        this.startStatusCheck(response.data.session_id)
      } catch (error) {
        this.error = error.response?.data?.detail || 'Ошибка создания сессии'
        this.loading = false
      }
    },
    
    async getQRCode(sessionId) {
      try {
        const response = await api.get(`/whatsapp/${sessionId}/qr`)
        this.qrCode = response.data.qr_code
        this.status = 'qr_code'
        this.loading = false
      } catch (error) {
        this.error = error.response?.data?.detail || 'Ошибка получения QR-кода'
        this.loading = false
      }
    },
    
    async checkStatus(sessionId) {
      try {
        const response = await api.get(`/whatsapp/${sessionId}/status`)
        const statusData = response.data
        
        if (statusData.connected) {
          this.status = 'connected'
          this.store.setWhatsAppConnected(true)
          if (this.statusCheckInterval) {
            clearInterval(this.statusCheckInterval)
          }
        } else if (statusData.status === 'qr_code' && statusData.qr_code) {
          this.qrCode = statusData.qr_code
          this.status = 'qr_code'
        } else if (statusData.status === 'connecting') {
          this.status = 'connecting'
        }
      } catch (error) {
        console.error('Error checking status:', error)
      }
    },
    
    startStatusCheck(sessionId) {
      // Check status every 2 seconds
      this.statusCheckInterval = setInterval(() => {
        this.checkStatus(sessionId)
      }, 2000)
    },
    
    continueToSelectChats() {
      this.$router.push('/select-whatsapp-chats')
    }
  }
}
</script>

<style scoped>
.whatsapp-connect-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}

.connect-card {
  background: white;
  border-radius: 16px;
  padding: 3rem;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  max-width: 500px;
  width: 100%;
  text-align: center;
}

.connect-card h2 {
  color: #333;
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.description {
  color: #666;
  margin-bottom: 2rem;
  line-height: 1.6;
}

.qr-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  margin: 2rem 0;
}

.qr-code {
  width: 300px;
  height: 300px;
  border: 4px solid #25D366;
  border-radius: 8px;
  padding: 1rem;
  background: white;
}

.qr-hint {
  color: #666;
  font-size: 0.9rem;
}

.connecting {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  margin: 2rem 0;
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

.connected {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  margin: 2rem 0;
}

.success-icon {
  font-size: 4rem;
}

.info-text {
  color: #666;
  font-size: 0.9rem;
  line-height: 1.6;
}

.disconnected {
  margin: 2rem 0;
}

.btn-primary {
  background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
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
  box-shadow: 0 5px 20px rgba(37, 211, 102, 0.4);
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

