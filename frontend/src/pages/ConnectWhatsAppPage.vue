<template>
  <div class="page">
    <div class="card">
      <h2>Подключение WhatsApp</h2>
      <p class="instruction">
        Откройте WhatsApp → Связанные устройства → Связать устройство
      </p>

      <div v-if="status === 'qr' && qrCode" class="qr-container">
        <img :src="`data:image/png;base64,${qrCode}`" alt="QR Code" class="qr-image" />
        <p class="hint">Отсканируйте QR-код в WhatsApp</p>
        <button @click="resetAndRetry" class="btn btn-secondary btn-small" :disabled="loading">
          Обновить QR-код
        </button>
      </div>

      <div v-else-if="status === 'connecting'" class="state-box">
        <div class="spinner" />
        <p>QR-код отсканирован</p>
        <p class="hint">Ожидание завершения подключения...</p>
        <p v-if="connectingTime > 0" class="timeout-info">
          Ожидание: {{ formatTime(connectingTime) }}
        </p>
        <button @click="resetAndRetry" class="btn btn-secondary btn-small" :disabled="loading">
          Начать заново
        </button>
      </div>

      <div v-else-if="status === 'connected'" class="state-box success">
        <span class="success-icon">✅</span>
        <p>WhatsApp Web подключен</p>
      </div>

      <div v-else class="qr-container placeholder">
        <div class="qr-placeholder">
          <p>QR-код будет отображен здесь</p>
          <p v-if="timeRemaining > 0" class="timeout-info">
            Ожидание: {{ formatTime(timeRemaining) }}
          </p>
        </div>
      </div>

      <div v-if="error" class="error">{{ error }}</div>

      <p class="note">
        После сканирования QR-кода сайт получит временную сессию WhatsApp Web.
        Данные не покидают ваш браузер.
      </p>
      <div class="nav-buttons">
        <button @click="goBack" class="btn btn-secondary">Назад</button>
        <button
          @click="continueNext"
          class="btn btn-primary"
          :disabled="status !== 'connected'"
        >
          Далее
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'
import { store } from '../store'
import api from '../api/client'

const router = useRouter()

const status = ref<'idle' | 'qr' | 'connecting' | 'connected'>('idle')
const qrCode = ref<string | null>(null)
const error = ref<string | null>(null)
const loading = ref(false)
const sessionId = ref<string | null>(null)

// Try to restore session_id from localStorage or store
function restoreSessionId() {
  // First check store
  if (store.whatsappSessionId) {
    sessionId.value = store.whatsappSessionId
    return
  }
  
  // Then check localStorage
  const saved = localStorage.getItem('whatsapp_session_id')
  if (saved) {
    sessionId.value = saved
    store.setWhatsAppSessionId(saved)
  }
}

function saveSessionId(id: string | null) {
  // Store handles localStorage automatically
  store.setWhatsAppSessionId(id)
}
const timeRemaining = ref(0)
const connectingTime = ref(0)
const QR_TIMEOUT_MS = 30000 // 30 seconds, matching backend
const CONNECTING_TIMEOUT_MS = 120000 // 2 minutes for connection
let intervalHandle: number | undefined
let timeoutHandle: number | undefined
let connectingTimerHandle: number | undefined

async function tryReuseExistingSession() {
  try {
    // Check for existing sessions
    const sessionsResponse = await api.get('/whatsapp/sessions')
    const sessions = sessionsResponse.data.sessions || []
    
    if (sessions.length === 0) {
      return null
    }
    
    // Try to reuse the most recent session (last one)
    const lastSessionId = sessions[sessions.length - 1]
    
    try {
      const reuseResponse = await api.post(`/whatsapp/sessions/${lastSessionId}/reuse`)
      
      if (reuseResponse.data.reused) {
        return {
          sessionId: lastSessionId,
          status: reuseResponse.data.status?.status || 'ready'
        }
      }
    } catch (e) {
      // Reuse failed, continue to create new session
      console.log('Failed to reuse session, creating new one')
    }
    
    return null
  } catch (e) {
    // If listing sessions fails, continue to create new session
    console.log('Failed to list sessions, creating new one')
    return null
  }
}

async function createSession() {
  loading.value = true
  error.value = null
  status.value = 'connecting'
  startTimeoutTimer()
  
  try {
    // First, try to reuse existing session
    const reused = await tryReuseExistingSession()
    
    if (reused && reused.status === 'ready') {
      // Session successfully reused and ready
      sessionId.value = reused.sessionId
      saveSessionId(reused.sessionId)
      store.whatsappSessionActive = true
      status.value = 'connected'
      clearTimeoutTimer()
      loading.value = false
      return
    }
    
    // If reuse failed or session not ready, create new session
    // If we have a session_id from reuse attempt, try to use it
    const requestBody = reused?.sessionId ? { session_id: reused.sessionId } : {}
    
    const response = await api.post('/whatsapp/connect', requestBody)
    sessionId.value = response.data.session_id
    saveSessionId(response.data.session_id)
    
    if (response.data.qr_code) {
      qrCode.value = response.data.qr_code
      status.value = 'qr'
      clearTimeoutTimer()
    } else if (response.data.status === 'ready') {
      // Session is ready (might have been reused)
      status.value = 'connected'
      store.whatsappSessionActive = true
      clearTimeoutTimer()
    } else {
      status.value = 'connecting'
    }
    
    startPolling()
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Ошибка создания сессии'
    clearTimeoutTimer()
    status.value = 'idle'
  } finally {
    loading.value = false
  }
}

async function pollStatus() {
  if (!sessionId.value) return
  try {
    const response = await api.get(`/whatsapp/status/${sessionId.value}`)
    const data = response.data

    if (data.status === 'ready' || data.connected) {
      status.value = 'connected'
      store.whatsappSessionActive = true
      clearPolling()
      clearTimeoutTimer()
      clearConnectingTimer()
    } else if (data.status === 'waiting_qr' && data.qr_code) {
      status.value = 'qr'
      qrCode.value = data.qr_code
      clearTimeoutTimer()
    } else if (data.status === 'waiting_qr' && !data.qr_code) {
      // QR was scanned, waiting for connection
      status.value = 'connecting'
      startConnectingTimer()
    } else if (data.status === 'expired') {
      error.value = 'QR истёк, пробуем обновить...'
      clearTimeoutTimer()
      await createSession()
    } else if (data.status === 'failed') {
      error.value = data.error || 'Ошибка подключения'
      status.value = 'idle'
      clearPolling()
      clearTimeoutTimer()
      clearConnectingTimer()
    }
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Ошибка проверки статуса'
    clearTimeoutTimer()
  }
}

function formatTime(ms: number): string {
  const seconds = Math.ceil(ms / 1000)
  return `${seconds} сек`
}

function startTimeoutTimer() {
  clearTimeoutTimer()
  timeRemaining.value = QR_TIMEOUT_MS
  
  timeoutHandle = window.setInterval(() => {
    timeRemaining.value -= 1000
    if (timeRemaining.value <= 0) {
      clearTimeoutTimer()
    }
  }, 1000)
}

function clearTimeoutTimer() {
  if (timeoutHandle) {
    clearInterval(timeoutHandle)
    timeoutHandle = undefined
  }
  timeRemaining.value = 0
}

function startPolling() {
  clearPolling()
  intervalHandle = window.setInterval(pollStatus, 2000)
}

function clearPolling() {
  if (intervalHandle) {
    clearInterval(intervalHandle)
    intervalHandle = undefined
  }
}

function startConnectingTimer() {
  clearConnectingTimer()
  connectingTime.value = 0
  
  connectingTimerHandle = window.setInterval(() => {
    connectingTime.value += 1000
    if (connectingTime.value >= CONNECTING_TIMEOUT_MS) {
      clearConnectingTimer()
    }
  }, 1000)
}

function clearConnectingTimer() {
  if (connectingTimerHandle) {
    clearInterval(connectingTimerHandle)
    connectingTimerHandle = undefined
  }
  connectingTime.value = 0
}

function goBack() {
  router.push('/')
}

function continueNext() {
  if (status.value === 'connected') {
    router.push('/select')
  }
}

async function resetAndRetry() {
  // Stop polling and timers
  clearPolling()
  clearTimeoutTimer()
  clearConnectingTimer()
  
  // Cleanup old session if exists
  if (sessionId.value) {
    try {
      await api.delete(`/whatsapp/session/${sessionId.value}`)
    } catch (e) {
      // Ignore errors during cleanup
      console.warn('Failed to cleanup session:', e)
    }
  }
  
  // Reset state
  sessionId.value = null
  qrCode.value = null
  error.value = null
  status.value = 'idle'
  connectingTime.value = 0
  saveSessionId(null)
  
  // Create new session
  await createSession()
}

onMounted(async () => {
  // Try to restore session_id first
  restoreSessionId()
  
  // If we have a session_id, check its status first
  if (sessionId.value) {
    try {
      const statusResponse = await api.get(`/whatsapp/status/${sessionId.value}`)
      const data = statusResponse.data
      
      if (data.status === 'ready' || data.connected) {
        // Session is still active
        status.value = 'connected'
        store.whatsappSessionActive = true
        return
      }
    } catch (e) {
      // Status check failed, continue to create/reuse session
      console.log('Failed to check session status, continuing...')
    }
  }
  
  // Create or reuse session
  await createSession()
})

onBeforeUnmount(() => {
  clearPolling()
  clearTimeoutTimer()
  clearConnectingTimer()
})
</script>

<style scoped>
.instruction {
  color: var(--text-secondary);
  margin-bottom: var(--spacing-md);
  text-align: center;
}

.qr-container {
  margin: var(--spacing-md) 0;
  display: flex;
  justify-content: center;
  align-items: center;
}

.qr-image {
  width: 280px;
  height: 280px;
  border: 2px solid var(--primary-color);
  border-radius: 12px;
  background: white;
}

.qr-placeholder {
  width: 300px;
  height: 300px;
  border: 2px dashed var(--border-color);
  border-radius: var(--border-radius);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--secondary-color);
}

.qr-placeholder p {
  color: var(--text-light);
  text-align: center;
}

.note {
  color: var(--text-light);
  font-size: 0.9rem;
  text-align: center;
  margin-bottom: var(--spacing-md);
}

.hint {
  text-align: center;
  color: var(--text-secondary);
}

.state-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  margin: var(--spacing-md) 0;
}

.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid var(--border-color);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error {
  color: var(--danger-color, #c0392b);
  text-align: center;
  margin-bottom: var(--spacing-md);
}

.success-icon {
  font-size: 2rem;
}

.timeout-info {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin-top: 0.5rem;
  font-weight: 500;
}

.btn-small {
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  margin-top: 1rem;
}

.state-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: var(--spacing-lg);
}
</style>

