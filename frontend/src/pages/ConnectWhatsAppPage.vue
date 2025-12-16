<template>
  <div class="page">
    <div class="card">
      <h2>Подключение WhatsApp</h2>
      <p class="instruction">
        Откройте WhatsApp → Связанные устройства → Связать устройство
      </p>
      <div class="qr-container">
        <div class="qr-placeholder">
          <p>QR-код будет отображен здесь</p>
        </div>
      </div>
      <p class="note">
        После сканирования QR-кода сайт получит временную сессию WhatsApp Web.
        Данные не покидают ваш браузер.
      </p>
      <div class="nav-buttons">
        <button @click="goBack" class="btn btn-secondary">Назад</button>
        <button @click="handleConnected" class="btn btn-primary" :disabled="!isConnected">
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
const isConnected = ref(false)

function goBack() {
  router.push('/')
}

function handleConnected() {
  if (isConnected.value) {
    store.whatsappSessionActive = true
    router.push('/select')
  }
}
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
</style>

