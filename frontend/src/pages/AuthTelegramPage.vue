<template>
  <div class="page">
    <div class="card">
      <h2>Авторизация Telegram</h2>
      <p class="description">
        Войдите в Telegram, чтобы получить доступ к вашим чатам
      </p>
      
      <div v-if="loading" class="auth-container">
        <div class="spinner" />
        <p>Загрузка...</p>
      </div>

      <div v-else-if="!isAuthorized" class="auth-container">
        <!-- Phone Auth Form -->
        <div v-if="authStep === 'phone'" class="phone-auth-form">
          <h3>Авторизация по телефону</h3>
          <p class="hint">Введите номер телефона в международном формате (например, +79991234567)</p>
          
          <div class="form-group">
            <label for="phone">Номер телефона</label>
            <input
              id="phone"
              v-model="phone"
              type="tel"
              placeholder="+79991234567"
              class="form-input"
              :disabled="loading"
            />
          </div>
          
          <button @click="startPhoneAuth" class="btn btn-primary" :disabled="!phone || loading">
            Отправить код
          </button>
        </div>

        <!-- Code Verification Form -->
        <div v-else-if="authStep === 'code'" class="phone-auth-form">
          <h3>Введите код подтверждения</h3>
          <p class="hint">Код отправлен на номер {{ phone }}</p>
          
          <div class="form-group">
            <label for="code">Код подтверждения</label>
            <input
              id="code"
              v-model="code"
              type="text"
              placeholder="12345"
              class="form-input"
              maxlength="5"
              :disabled="loading"
            />
          </div>
          
          <button @click="verifyCode" class="btn btn-primary" :disabled="!code || loading">
            Подтвердить
          </button>
          <button @click="authStep = 'phone'" class="btn btn-secondary" :disabled="loading">
            Назад
          </button>
        </div>

        <!-- 2FA Password Form -->
        <div v-else-if="authStep === 'password'" class="phone-auth-form">
          <h3>Введите пароль 2FA</h3>
          <p class="hint">У вас включена двухфакторная аутентификация</p>
          
          <div class="form-group">
            <label for="password">Пароль 2FA</label>
            <input
              id="password"
              v-model="password"
              type="password"
              placeholder="Пароль"
              class="form-input"
              :disabled="loading"
            />
          </div>
          
          <button @click="verifyCode" class="btn btn-primary" :disabled="!password || loading">
            Подтвердить
          </button>
          <button @click="authStep = 'code'" class="btn btn-secondary" :disabled="loading">
            Назад
          </button>
        </div>

        <!-- Telegram Login Widget (optional, if bot is configured) -->
        <div v-else-if="authStep === 'widget' && !botUsernameMissing" class="widget-container">
          <div id="telegram-login-container"></div>
        </div>

        <p v-if="error" class="error-message">{{ error }}</p>
      </div>

      <div v-else-if="isAuthorized && loadingChats" class="auth-container">
        <div class="spinner" />
        <p>Загрузка чатов...</p>
      </div>

      <div v-else-if="isAuthorized" class="auth-success">
        <span class="success-icon">✅</span>
        <p>Авторизация успешна!</p>
        <p class="user-info" v-if="userInfo">
          {{ userInfo.first_name }} {{ userInfo.last_name || '' }}
        </p>
      </div>

      <p class="note">
        После успешной авторизации будет получен список ваших чатов в Telegram
        для сопоставления с чатами WhatsApp.
      </p>

      <div class="nav-buttons">
        <button @click="goBack" class="btn btn-secondary">Назад</button>
        <button @click="handleNext" class="btn btn-primary" :disabled="!isAuthorized || loadingChats">
          Далее
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { store } from '../store'
import api from '../api/client'

const router = useRouter()
const isAuthorized = ref(false)
const loading = ref(false)
const loadingChats = ref(false)
const error = ref<string | null>(null)
const userInfo = ref<any>(null)
const telegramUserId = ref<number | null>(null)
const botUsernameMissing = ref(false)

// Phone auth state
const authStep = ref<'phone' | 'code' | 'password' | 'widget'>('phone')
const phone = ref('')
const code = ref('')
const password = ref('')
const phoneCodeHash = ref<string | null>(null)
const telegramSessionId = ref<string | null>(null)

// Telegram Login Widget callback
declare global {
  interface Window {
    onTelegramAuth?: (user: any) => void
  }
}

function goBack() {
  router.push('/select')
}

async function startPhoneAuth() {
  if (!phone.value) {
    error.value = 'Введите номер телефона'
    return
  }

  loading.value = true
  error.value = null

  try {
    // Generate session ID for Telegram auth
    if (!telegramSessionId.value) {
      telegramSessionId.value = crypto.randomUUID()
    }

    const response = await api.post('/auth/telegram-phone-auth', {
      session_id: telegramSessionId.value,
      phone: phone.value
    })

    phoneCodeHash.value = response.data.phone_code_hash
    authStep.value = 'code'
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Ошибка отправки кода'
  } finally {
    loading.value = false
  }
}

async function verifyCode() {
  if (!code.value && !password.value) {
    error.value = 'Введите код или пароль'
    return
  }

  loading.value = true
  error.value = null

  try {
    const requestData: any = {
      session_id: telegramSessionId.value,
      phone: phone.value,
      phone_code_hash: phoneCodeHash.value,
    }

    if (code.value) {
      requestData.code = code.value
    }
    if (password.value) {
      requestData.password = password.value
    }

    const response = await api.post('/auth/telegram-verify-code', requestData)

    if (response.data.authenticated) {
      telegramUserId.value = response.data.user_id
      isAuthorized.value = true
      userInfo.value = response.data.user_info
      // Store user_id for future use
      store.setTelegramUserId(response.data.user_id)
      await loadTelegramChats()
    }
  } catch (e: any) {
    const errorDetail = e?.response?.data?.detail || 'Ошибка верификации'
    
    if (errorDetail.includes('2FA') || errorDetail.includes('password')) {
      authStep.value = 'password'
      error.value = 'Требуется пароль 2FA'
    } else {
      error.value = errorDetail
    }
  } finally {
    loading.value = false
  }
}

async function handleTelegramAuth(authData: any) {
  loading.value = true
  error.value = null

  try {
    // Send auth data to backend for verification
    const response = await api.post('/auth/telegram-login', {
      auth_data: authData
    })

    telegramUserId.value = response.data.user_id
    store.setTelegramUserId(response.data.user_id)

    if (response.data.session_exists) {
      // Session exists, user is authorized
      isAuthorized.value = true
      userInfo.value = response.data.user_info
      await loadTelegramChats()
    } else {
      // Session doesn't exist, switch to phone auth
      authStep.value = 'phone'
      error.value = 'Для доступа к чатам требуется авторизация по телефону. Введите номер телефона ниже.'
    }
  } catch (e: any) {
    const errorDetail = e?.response?.data?.detail || e?.message || 'Ошибка авторизации Telegram'
    
    // Check for specific Telegram widget errors
    if (errorDetail.includes('Username invalid') || errorDetail.includes('username')) {
      error.value = 'Неверный bot username. Проверьте настройку VITE_TELEGRAM_BOT_USERNAME в .env файле.'
      botUsernameMissing.value = true
    } else {
      error.value = errorDetail
    }
  } finally {
    loading.value = false
  }
}

async function loadTelegramChats() {
  const userId = telegramUserId.value || store.telegramUserId
  if (!userId) return

  loadingChats.value = true
  error.value = null

  try {
    const response = await api.post('/telegram/contacts', {
      user_id: userId
    })

    // Transform API response to match store interface
    const chats = response.data.contacts.map((contact: any) => ({
      id: contact.id,
      name: contact.name,
      type: contact.is_channel ? 'channel' : (contact.is_group ? 'group' : 'personal')
    }))

    store.setTelegramChats(chats)
    store.telegramSessionActive = true
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Ошибка загрузки чатов Telegram'
  } finally {
    loadingChats.value = false
  }
}

function handleNext() {
  if (isAuthorized.value && !loadingChats.value) {
    router.push('/map')
  }
}

onMounted(() => {
  // Check if bot username is configured (optional)
  const botUsername = import.meta.env.VITE_TELEGRAM_BOT_USERNAME
  
  if (botUsername && botUsername !== 'your_bot_username' && botUsername.trim() !== '') {
    // Bot is configured, can use widget as alternative
    botUsernameMissing.value = false
    
    // Set up Telegram Login Widget callback
    window.onTelegramAuth = handleTelegramAuth

    // Load Telegram Login Widget script
    const script = document.createElement('script')
    script.src = 'https://telegram.org/js/telegram-widget.js?22'
    script.setAttribute('data-telegram-login', botUsername)
    script.setAttribute('data-size', 'large')
    script.setAttribute('data-onauth', 'onTelegramAuth(user)')
    script.setAttribute('data-request-access', 'write')
    script.async = true

    script.onerror = () => {
      // Widget failed, but phone auth is still available
      console.warn('Telegram Login Widget failed to load')
    }

    const container = document.getElementById('telegram-login-container')
    if (container) {
      container.appendChild(script)
    }
  } else {
    // No bot configured, use phone auth only
    botUsernameMissing.value = true
    authStep.value = 'phone'
  }
})

onBeforeUnmount(() => {
  // Cleanup
  if (window.onTelegramAuth) {
    delete window.onTelegramAuth
  }
})
</script>

<style scoped>
.description {
  color: var(--text-secondary);
  margin-bottom: var(--spacing-md);
  text-align: center;
}

.auth-container {
  min-height: 200px;
  margin: var(--spacing-md) 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-md);
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

.auth-success {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-lg);
}

.success-icon {
  font-size: 3rem;
}

.user-info {
  color: var(--text-secondary);
  font-size: 1.1rem;
  font-weight: 500;
}

.error-message {
  color: var(--danger-color, #c0392b);
  text-align: center;
  margin-top: var(--spacing-md);
  padding: var(--spacing-sm);
  background: rgba(192, 57, 43, 0.1);
  border-radius: var(--border-radius);
}

.phone-auth-form {
  width: 100%;
  max-width: 400px;
  padding: var(--spacing-lg);
}

.phone-auth-form h3 {
  margin-top: 0;
  margin-bottom: var(--spacing-md);
  color: var(--primary-color);
}

.form-group {
  margin-bottom: var(--spacing-md);
}

.form-group label {
  display: block;
  margin-bottom: var(--spacing-xs);
  font-weight: 500;
  color: var(--text-primary);
}

.form-input {
  width: 100%;
  padding: var(--spacing-sm);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  font-size: 1rem;
  transition: border-color 0.2s;
}

.form-input:focus {
  outline: none;
  border-color: var(--primary-color);
}

.form-input:disabled {
  background: var(--secondary-color);
  cursor: not-allowed;
}

.hint {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin-bottom: var(--spacing-md);
}

.widget-container {
  width: 100%;
  display: flex;
  justify-content: center;
}

.note {
  color: var(--text-light);
  font-size: 0.9rem;
  text-align: center;
  margin-bottom: var(--spacing-md);
}
</style>

