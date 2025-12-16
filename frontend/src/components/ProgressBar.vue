<template>
  <div class="progress-container">
    <div 
      class="progress-bar" 
      :style="{ width: `${percentage}%` }"
    >
      <span v-if="percentage > 10">{{ percentage }}%</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  current: number
  total: number
}>()

const percentage = computed(() => {
  if (props.total === 0) return 0
  return Math.round((props.current / props.total) * 100)
})
</script>

<style scoped>
.progress-container {
  width: 100%;
  background: var(--secondary-color);
  border-radius: var(--border-radius);
  height: 24px;
  overflow: hidden;
  margin: var(--spacing-sm) 0;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  transition: width 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--white);
  font-size: 0.875rem;
  font-weight: 600;
}
</style>

