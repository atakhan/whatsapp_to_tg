<template>
  <div class="page">
    <div class="card">
      <h2>Перенос завершён</h2>
      <p class="success-message">
        Все данные успешно перенесены в Telegram!
      </p>

      <div class="actions">
        <button @click="openTelegram" class="btn btn-primary">
          Открыть чат в Telegram
        </button>
        <button @click="downloadReport" class="btn btn-secondary">
          Скачать отчёт
        </button>
      </div>

      <p class="notice">
        Временные файлы автоматически удалены.
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { store } from '../store'

function openTelegram() {
  // Open Telegram chat
  window.open('https://web.telegram.org', '_blank')
}

function downloadReport() {
  if (store.migrationReport) {
    const blob = new Blob([store.migrationReport.log], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'migration-report.txt'
    a.click()
    URL.revokeObjectURL(url)
  }
}
</script>

<style scoped>
.success-message {
  color: var(--success-color);
  font-size: 1.1rem;
  font-weight: 600;
  text-align: center;
  margin-bottom: var(--spacing-md);
}

.actions {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  margin: var(--spacing-md) 0;
}

.notice {
  text-align: center;
  color: var(--text-light);
  font-size: 0.9rem;
  margin-top: var(--spacing-md);
}
</style>

