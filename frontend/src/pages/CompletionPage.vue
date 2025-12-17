<template>
  <div class="page">
    <div class="card">
      <h2>Перенос завершён</h2>
      
      <div v-if="migrationStats" class="stats">
        <div class="stat-item">
          <span class="stat-label">Всего сообщений:</span>
          <span class="stat-value">{{ migrationStats.total }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Успешно перенесено:</span>
          <span class="stat-value success">{{ migrationStats.processed }}</span>
        </div>
        <div v-if="migrationStats.errors > 0" class="stat-item">
          <span class="stat-label">Ошибок:</span>
          <span class="stat-value error">{{ migrationStats.errors }}</span>
        </div>
      </div>

      <p v-if="!hasErrors" class="success-message">
        Все данные успешно перенесены в Telegram!
      </p>
      <p v-else class="warning-message">
        Миграция завершена с ошибками. Проверьте отчёт для деталей.
      </p>

      <div class="actions">
        <button @click="openTelegram" class="btn btn-primary">
          Открыть Telegram
        </button>
        <button @click="downloadReport" class="btn btn-secondary">
          Скачать отчёт
        </button>
        <button @click="startNewMigration" class="btn btn-outline">
          Начать новую миграцию
        </button>
      </div>

      <p class="notice">
        Временные файлы автоматически удалены.
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { store } from '../store'

const router = useRouter()

const migrationStats = computed(() => {
  if (!store.migrationProgress) return null
  
  return {
    total: store.migrationProgress.total,
    processed: store.migrationProgress.current,
    errors: store.migrationProgress.errors?.length || 0
  }
})

const hasErrors = computed(() => {
  return migrationStats.value?.errors && migrationStats.value.errors > 0
})

function openTelegram() {
  // Open Telegram Web
  window.open('https://web.telegram.org', '_blank')
}

function downloadReport() {
  if (store.migrationReport) {
    const blob = new Blob([store.migrationReport.log], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `migration-report-${new Date().toISOString().split('T')[0]}.txt`
    a.click()
    URL.revokeObjectURL(url)
  } else {
    // Generate basic report from progress
    const report = `Миграция завершена\n\n` +
                  `Всего сообщений: ${migrationStats.value?.total || 0}\n` +
                  `Обработано: ${migrationStats.value?.processed || 0}\n` +
                  `Ошибок: ${migrationStats.value?.errors || 0}\n`
    const blob = new Blob([report], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `migration-report-${new Date().toISOString().split('T')[0]}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }
}

function startNewMigration() {
  store.reset()
  router.push('/')
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

.warning-message {
  color: var(--warning-color, #ff9800);
  font-size: 1.1rem;
  font-weight: 600;
  text-align: center;
  margin-bottom: var(--spacing-md);
}

.stats {
  background: var(--bg-secondary, #f5f5f5);
  border-radius: var(--border-radius);
  padding: var(--spacing-md);
  margin: var(--spacing-md) 0;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-sm) 0;
  border-bottom: 1px solid var(--border-color);
}

.stat-item:last-child {
  border-bottom: none;
}

.stat-label {
  color: var(--text-secondary);
  font-weight: 500;
}

.stat-value {
  font-weight: 600;
  font-size: 1.1rem;
}

.stat-value.success {
  color: var(--success-color);
}

.stat-value.error {
  color: var(--error-color);
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

