<template>
  <div class="page">
    <div class="card">
      <h2>Авторизация Telegram</h2>
      <p class="description">
        Войдите в Telegram, чтобы получить доступ к вашим чатам
      </p>
      
      <div class="auth-container">
        <div class="auth-placeholder">
          <p>Telegram Login Widget будет здесь</p>
          <p class="auth-note">Или используйте Telegram Web авторизацию</p>
        </div>
      </div>

      <p class="note">
        После успешной авторизации будет открыта временная MTProto сессия
        и получен список ваших личных чатов в Telegram.
      </p>

      <div class="nav-buttons">
        <button @click="goBack" class="btn btn-secondary">Назад</button>
        <button @click="handleAuthorized" class="btn btn-primary" :disabled="!isAuthorized">
          Далее
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { store } from '../store'

const router = useRouter()
const isAuthorized = ref(false)

function goBack() {
  router.push('/select')
}

function handleAuthorized() {
  if (isAuthorized.value) {
    store.telegramSessionActive = true
    router.push('/map')
  }
}
</script>

<style scoped>
.description {
  color: var(--text-secondary);
  margin-bottom: var(--spacing-md);
  text-align: center;
}

.auth-container {
  margin: var(--spacing-md) 0;
  display: flex;
  justify-content: center;
}

.auth-placeholder {
  width: 100%;
  max-width: 400px;
  padding: var(--spacing-lg);
  border: 2px dashed var(--border-color);
  border-radius: var(--border-radius);
  background: var(--secondary-color);
  text-align: center;
}

.auth-placeholder p {
  color: var(--text-secondary);
  margin-bottom: var(--spacing-sm);
}

.auth-note {
  font-size: 0.9rem;
  color: var(--text-light);
}

.note {
  color: var(--text-light);
  font-size: 0.9rem;
  text-align: center;
  margin-bottom: var(--spacing-md);
}
</style>

