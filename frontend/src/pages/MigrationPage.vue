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
        <h3>Ошибки:</h3>
        <ul>
          <li v-for="(error, index) in store.migrationProgress.errors" :key="index">
            {{ error }}
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { store } from '../store'
import ProgressBar from '../components/ProgressBar.vue'

const router = useRouter()

onMounted(() => {
  // Simulate migration start
  if (!store.migrationProgress) {
    store.setMigrationProgress({
      current: 0,
      total: 100,
      currentOperation: 'Инициализация переноса...',
      errors: []
    })
  }
})

watch(() => store.migrationComplete, (complete) => {
  if (complete) {
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
</style>

