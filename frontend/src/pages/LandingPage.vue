<template>
  <div class="page">
    <div class="card">
      <h1>WhatsApp → Telegram Migrator</h1>
      <p class="description">
        Перенесите свои чаты из WhatsApp в Telegram со всеми медиафайлами в максимальном качестве.
      </p>
      <button @click="startMigration" class="btn btn-primary">
        Начать перенос
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

function startMigration() {
  router.push('/whatsapp')
}
</script>

<style scoped>
.description {
  color: var(--text-secondary);
  font-size: 1.1rem;
  line-height: 1.6;
  margin-bottom: var(--spacing-md);
  text-align: center;
}

.card {
  text-align: center;
}
</style>

