<template>
  <div class="auth-page">
    <div class="auth-card">
      <h2>Авторизация в Telegram</h2>
      <p class="description">
        Войдите в свой аккаунт Telegram для продолжения
      </p>
      
      <div v-if="!authenticated" class="auth-methods">
        <!-- Telegram Login Widget -->
        <div id="telegram-login-widget"></div>
        
        <!-- Manual phone auth -->
        <div v-if="showPhoneAuth" class="phone-auth">
          <input 
            v-model="phone"
            type="tel"
            placeholder="+1234567890"
            class="input-field"
          />
          <button @click="sendCode" class="btn-primary" :disabled="sendingCode">
            {{ sendingCode ? 'Отправка...' : 'Отправить код' }}
          </button>
        </div>
        
        <div v-if="codeSent" class="code-auth">
          <input 
            v-model="code"
            type="text"
            placeholder="Код из Telegram"
            class="input-field"
          />
          <button @click="verifyCode" class="btn-primary" :disabled="verifying">
            {{ verifying ? 'Проверка...' : 'Подтвердить' }}
          </button>
        </div>
        
        <button v-if="!showPhoneAuth && !codeSent" @click="showPhoneAuth = true" class="btn-secondary">
          Войти по номеру телефона
        </button>
      </div>
      
      <div v-if="authenticated" class="auth-success">
        <span class="success-icon">✅</span>
        <p>Авторизация успешна!</p>
        <p class="user-info" v-if="userInfo">
          {{ userInfo.first_name }} {{ userInfo.last_name || '' }}
        </p>
        <button @click="continueToSelectChat" class="btn-primary">
          Продолжить
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
  name: 'Auth',
  data() {
    return {
      authenticated: false,
      showPhoneAuth: false,
      phone: '',
      code: '',
      codeSent: false,
      sendingCode: false,
      verifying: false,
      phoneCodeHash: null,
      userInfo: null,
      error: null
    }
  },
  setup() {
    const store = useMigrationStore()
    return { store }
  },
  mounted() {
    this.initTelegramWidget()
  },
  methods: {
    initTelegramWidget() {
      // Telegram Login Widget script
      const script = document.createElement('script')
      script.src = 'https://telegram.org/js/telegram-widget.js?22'
      script.setAttribute('data-telegram-login', 'your_bot_username') // Replace with your bot username
      script.setAttribute('data-size', 'large')
      script.setAttribute('data-onauth', 'onTelegramAuth')
      script.setAttribute('data-request-access', 'write')
      script.async = true
      
      window.onTelegramAuth = (user) => {
        this.handleTelegramAuth(user)
      }
      
      const widget = document.getElementById('telegram-login-widget')
      if (widget) {
        widget.appendChild(script)
      }
    },
    
    async handleTelegramAuth(authData) {
      try {
        const response = await api.post('/auth/telegram-login', {
          auth_data: authData
        })
        
        if (response.data.session_exists) {
          this.store.setUserTelegramId(response.data.user_id)
          this.store.setUserInfo(response.data.user_info)
          this.userInfo = response.data.user_info
          this.authenticated = true
        } else {
          // Need phone auth
          this.showPhoneAuth = true
        }
      } catch (error) {
        this.error = error.response?.data?.detail || 'Ошибка авторизации'
      }
    },
    
    async sendCode() {
      if (!this.phone) {
        this.error = 'Введите номер телефона'
        return
      }
      
      this.sendingCode = true
      this.error = null
      
      try {
        const response = await api.post('/auth/telegram-phone-auth', {
          phone: this.phone,
          user_id: this.store.userTelegramId || 0 // Will be set after widget auth
        })
        
        this.phoneCodeHash = response.data.phone_code_hash
        this.codeSent = true
        this.sendingCode = false
      } catch (error) {
        this.error = error.response?.data?.detail || 'Ошибка отправки кода'
        this.sendingCode = false
      }
    },
    
    async verifyCode() {
      if (!this.code) {
        this.error = 'Введите код'
        return
      }
      
      this.verifying = true
      this.error = null
      
      try {
        const response = await api.post('/auth/telegram-verify-code', {
          phone: this.phone,
          code: this.code,
          phone_code_hash: this.phoneCodeHash,
          user_id: this.store.userTelegramId || 0
        })
        
        this.store.setUserTelegramId(response.data.user_info.id)
        this.store.setUserInfo(response.data.user_info)
        this.userInfo = response.data.user_info
        this.authenticated = true
        this.verifying = false
      } catch (error) {
        this.error = error.response?.data?.detail || 'Неверный код'
        this.verifying = false
      }
    },
    
    continueToSelectChat() {
      // Parse messages first
      this.parseMessages()
    },
    
    async parseMessages() {
      try {
        const response = await api.post('/parse', {
          session_id: this.store.sessionId
        })
        
        this.store.setParsedMessagesCount(response.data.messages_count)
        this.$router.push('/select-chat')
      } catch (error) {
        this.error = error.response?.data?.detail || 'Ошибка парсинга сообщений'
      }
    }
  }
}
</script>

<style scoped>
.auth-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}

.auth-card {
  background: white;
  border-radius: 16px;
  padding: 3rem;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  max-width: 500px;
  width: 100%;
  text-align: center;
}

.auth-card h2 {
  color: #333;
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.description {
  color: #666;
  margin-bottom: 2rem;
}

.auth-methods {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  align-items: center;
}

.phone-auth,
.code-auth {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  width: 100%;
}

.input-field {
  padding: 0.75rem;
  border: 2px solid #ddd;
  border-radius: 8px;
  font-size: 1rem;
  width: 100%;
}

.input-field:focus {
  outline: none;
  border-color: #667eea;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  width: 100%;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: transparent;
  color: #667eea;
  border: 2px solid #667eea;
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
  border-radius: 8px;
  cursor: pointer;
  width: 100%;
}

.auth-success {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.success-icon {
  font-size: 4rem;
}

.user-info {
  font-size: 1.2rem;
  color: #333;
  font-weight: 600;
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
