<template>
  <div class="page">
    <div class="card">
      <h2>Сопоставление чатов</h2>
      <p class="description">
        Выберите, куда перенести каждый выбранный чат WhatsApp:
      </p>

      <div class="mapping-table">
        <div 
          v-for="whatsappChatId in store.selectedWhatsAppChats" 
          :key="whatsappChatId"
          class="mapping-row"
        >
          <div class="source-chat">
            <strong>{{ getWhatsAppChatName(whatsappChatId) }}</strong>
            <span class="chat-label">WhatsApp</span>
          </div>
          <div class="arrow">→</div>
          <div class="target-chat">
            <select 
              :value="getMapping(whatsappChatId)"
              @change="updateMapping(whatsappChatId, $event)"
              class="chat-select"
            >
              <option value="new">Создать новый чат</option>
              <option value="saved">Сохраненные сообщения</option>
              <option 
                v-for="tgChat in store.telegramChats" 
                :key="tgChat.id"
                :value="tgChat.id"
              >
                {{ tgChat.name }}
              </option>
            </select>
          </div>
        </div>
      </div>

      <div class="nav-buttons">
        <button @click="goBack" class="btn btn-secondary">Назад</button>
        <button @click="handleStartMigration" class="btn btn-primary">
          Начать перенос
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { store } from '../store'
import type { ChatMapping } from '../store'

const router = useRouter()

function getWhatsAppChatName(chatId: string): string {
  const chat = store.whatsappChats.find(c => c.id === chatId)
  return chat?.name || chatId
}

function getMapping(whatsappChatId: string): string | number {
  const mapping = store.chatMappings.find(m => m.whatsappChatId === whatsappChatId)
  return mapping?.telegramChatId || 'new'
}

function updateMapping(whatsappChatId: string, event: Event) {
  const target = event.target as HTMLSelectElement
  const telegramChatId = target.value === 'new' || target.value === 'saved' 
    ? target.value 
    : (target.value.includes('-') ? BigInt(target.value) : Number(target.value))
  
  const existingIndex = store.chatMappings.findIndex(m => m.whatsappChatId === whatsappChatId)
  const mapping: ChatMapping = {
    whatsappChatId,
    telegramChatId,
    telegramChatName: target.value === 'new' || target.value === 'saved' 
      ? undefined 
      : store.telegramChats.find(c => String(c.id) === target.value)?.name
  }

  if (existingIndex > -1) {
    store.chatMappings[existingIndex] = mapping
  } else {
    store.chatMappings.push(mapping)
  }
}

function goBack() {
  router.push('/telegram')
}

function handleStartMigration() {
  if (store.chatMappings.length === store.selectedWhatsAppChats.length) {
    router.push('/migrate')
  }
}
</script>

<style scoped>
.description {
  color: var(--text-secondary);
  margin-bottom: var(--spacing-md);
}

.mapping-table {
  margin: var(--spacing-md) 0;
}

.mapping-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  margin-bottom: var(--spacing-sm);
}

.source-chat {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.chat-label {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.arrow {
  font-size: 1.5rem;
  color: var(--text-light);
  padding: 0 var(--spacing-sm);
}

.target-chat {
  flex: 1;
}

.chat-select {
  width: 100%;
}
</style>

