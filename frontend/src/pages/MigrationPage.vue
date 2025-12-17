<template>
  <div class="page">
    <div class="card">
      <h2>Перенос данных</h2>
      
      <div class="progress-section" v-if="store.migrationProgress">
        <ProgressBar 
          :current="store.migrationProgress.current"
          :total="store.migrationProgress.total"
        />
        <p class="progress-text">
          {{ store.migrationProgress.currentOperation }}
        </p>
        <p class="progress-count">
          {{ store.migrationProgress.current }} из {{ store.migrationProgress.total }}
        </p>
      </div>

      <div v-else class="migration-pending">
        <p>Подготовка к переносу...</p>
      </div>

      <div v-if="store.migrationProgress && store.migrationProgress.errors.length > 0" class="errors">
        <h3>Ошибки ({{ store.migrationProgress.errors.length }}):</h3>
        <ul>
          <li v-for="(error, index) in store.migrationProgress.errors" :key="index">
            {{ error }}
          </li>
        </ul>
        <p class="error-hint">
          Если ошибка связана с блокировкой базы данных, подождите несколько секунд и попробуйте снова.
        </p>
      </div>
      
      <div v-if="store.migrationProgress && store.migrationProgress.total === 0" class="info-message">
        <p>Инициализация миграции... Получение сообщений из WhatsApp Web.</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter } from 'vue-router'
import { store } from '../store'
import ProgressBar from '../components/ProgressBar.vue'
import api from '../api/client'

const router = useRouter()
let statusPollInterval: number | undefined

async function startMigration() {
  if (!store.whatsappSessionId || !store.telegramUserId || store.chatMappings.length === 0) {
    return
  }

  try {
      // Start migration for each chat mapping
      for (const mapping of store.chatMappings) {
        const targetChatId = mapping.telegramChatId
        
        // Convert target_chat_id (handle 'new' and 'saved')
        let numericTargetChatId: number | string
        if (targetChatId === 'new' || targetChatId === 'saved') {
          // Use special value 777000 - backend will convert to "me" for Saved Messages
          numericTargetChatId = 777000
        } else {
          numericTargetChatId = typeof targetChatId === 'number' ? targetChatId : Number(targetChatId)
        }

      await api.post('/migrate/start', {
        session_id: store.whatsappSessionId,
        user_id: store.telegramUserId,
        target_chat_id: numericTargetChatId,
        whatsapp_chat_id: mapping.whatsappChatId
      })
    }

    // Start polling for status
    startStatusPolling()
  } catch (e: any) {
    console.error('Failed to start migration:', e)
    if (store.migrationProgress) {
      store.migrationProgress.errors.push(e?.response?.data?.detail || 'Ошибка запуска миграции')
    }
  }
}

function startStatusPolling() {
  clearStatusPolling()
  
  statusPollInterval = window.setInterval(async () => {
    if (!store.whatsappSessionId) return

    try {
      const response = await api.get(`/migrate/status/${store.whatsappSessionId}`)
      const status = response.data

      store.setMigrationProgress({
        current: status.processed || 0,
        total: status.total || 0,
        currentOperation: status.current_action || 'Обработка...',
        errors: status.errors || []
      })

      // Check if migration is complete or failed
      if (status.completed_at && !store.migrationComplete) {
        // Generate migration report
        const report = {
          log: `Миграция завершена${status.errors && status.errors.length > 0 ? ' с ошибками' : ' успешно'}!\n\n` +
               `Всего сообщений: ${status.total}\n` +
               `Обработано: ${status.processed}\n` +
               `Ошибок: ${status.errors?.length || 0}\n\n` +
               `Начало: ${status.started_at || 'N/A'}\n` +
               `Завершение: ${status.completed_at}\n\n` +
               (status.errors && status.errors.length > 0 
                 ? `Ошибки:\n${status.errors.join('\n')}\n` 
                 : ''),
          errors: status.errors || []
        }
        store.setMigrationReport(report)
        
        // Cleanup session
        try {
          if (store.whatsappSessionId) {
            await api.post(`/migrate/cleanup/${store.whatsappSessionId}`)
          }
        } catch (e) {
          console.error('Failed to cleanup session:', e)
        }
        
        store.setMigrationComplete(true)
        clearStatusPolling()
      } else if (status.errors && status.errors.length > 0 && !status.completed_at) {
        // Migration failed but not completed - show errors
        store.setMigrationProgress({
          current: status.processed || 0,
          total: status.total || 0,
          currentOperation: `Ошибка: ${status.errors[status.errors.length - 1]}`,
          errors: status.errors || []
        })
      }
    } catch (e: any) {
      console.error('Failed to get migration status:', e)
      // If status endpoint returns 404, migration might not have started yet
      if (e?.response?.status === 404) {
        // Keep showing "Инициализация переноса..."
        if (store.migrationProgress) {
          store.migrationProgress.currentOperation = 'Инициализация переноса...'
        }
      } else {
        // Other errors - show error message
        if (store.migrationProgress) {
          const errorMsg = e?.response?.data?.detail || 'Ошибка получения статуса миграции'
          if (!store.migrationProgress.errors.includes(errorMsg)) {
            store.migrationProgress.errors.push(errorMsg)
          }
          store.migrationProgress.currentOperation = `Ошибка: ${errorMsg}`
        }
      }
    }
  }, 2000)  // Poll every 2 seconds
}

function clearStatusPolling() {
  if (statusPollInterval) {
    clearInterval(statusPollInterval)
    statusPollInterval = undefined
  }
}

onMounted(() => {
  // Initialize progress
  if (!store.migrationProgress) {
    store.setMigrationProgress({
      current: 0,
      total: 0,
      currentOperation: 'Инициализация переноса...',
      errors: []
    })
  }

  // Start migration
  startMigration()
})

onBeforeUnmount(() => {
  clearStatusPolling()
})

watch(() => store.migrationComplete, (complete) => {
  if (complete) {
    clearStatusPolling()
    router.push('/done')
  }
})
</script>

<style scoped>
.progress-section {
  margin: var(--spacing-md) 0;
}

.progress-text {
  text-align: center;
  color: var(--text-secondary);
  margin-top: var(--spacing-sm);
  font-weight: 600;
}

.progress-count {
  text-align: center;
  color: var(--text-light);
  font-size: 0.9rem;
  margin-top: var(--spacing-xs);
}

.migration-pending {
  text-align: center;
  padding: var(--spacing-lg);
  color: var(--text-secondary);
}

.errors {
  margin-top: var(--spacing-md);
  padding: var(--spacing-sm);
  background: rgba(244, 67, 54, 0.1);
  border-radius: var(--border-radius);
  border: 1px solid var(--error-color);
}

.errors h3 {
  color: var(--error-color);
  font-size: 1rem;
  margin-bottom: var(--spacing-sm);
}

.errors ul {
  list-style: none;
  padding-left: var(--spacing-sm);
}

.errors li {
  color: var(--error-color);
  font-size: 0.9rem;
  margin-bottom: var(--spacing-xs);
}

.error-hint {
  margin-top: var(--spacing-sm);
  font-size: 0.85rem;
  color: var(--text-secondary);
  font-style: italic;
}

.info-message {
  margin-top: var(--spacing-md);
  padding: var(--spacing-sm);
  background: rgba(33, 150, 243, 0.1);
  border-radius: var(--border-radius);
  border: 1px solid rgba(33, 150, 243, 0.3);
  text-align: center;
  color: var(--text-secondary);
}
</style>

