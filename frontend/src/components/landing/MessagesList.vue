<template>
  <div v-if="visible" class="messages-visualization">
    <div v-if="loading" class="messages-loading">
      <div class="messages-spinner"></div>
      <p>{{ progress.message }}</p>
      <p v-if="progress.total" class="messages-progress-text">
        {{ progress.loaded }} / {{ progress.total }}
      </p>
      <p v-else-if="progress.loaded > 0" class="messages-progress-text">
        {{ progress.loaded }} сообщений...
      </p>
    </div>
    <div v-else class="messages-content">
      <div class="messages-list-container">
        <div class="messages-list-header">
          <h3>Сообщения для переноса</h3>
          <div class="messages-header-info">
            <p class="messages-count-header">
              {{ filteredMessages.length }} {{ formatMessageCount(filteredMessages.length) }}
            </p>
            <p v-if="selectedCount > 0" class="messages-selected-count">
              Выбрано: {{ selectedCount }}
            </p>
          </div>
        </div>
        
        <!-- Filter controls -->
        <div class="messages-filters">
          <input
            v-model="filterText"
            type="text"
            placeholder="Поиск по тексту..."
            class="messages-filter-input"
          />
          <select v-model="filterType" class="messages-filter-select">
            <option value="">Все типы</option>
            <option value="text">Текст</option>
            <option value="image">Изображения</option>
            <option value="video">Видео</option>
            <option value="audio">Аудио</option>
            <option value="document">Документы</option>
          </select>
          <select v-model="filterSender" class="messages-filter-select">
            <option value="">Все отправители</option>
            <option v-for="sender in uniqueSenders" :key="sender" :value="sender">
              {{ sender }}
            </option>
          </select>
        </div>
        
        <div class="messages-list" ref="messagesListRef">
          <div
            v-for="message in filteredMessages"
            :key="message.id"
            class="message-item"
            :class="{
              [`message-item-${message.type}`]: true,
              'message-selected': message.selected
            }"
            @click="toggleMessageSelection(message.id)"
          >
            <div class="message-checkbox">
              <input
                type="checkbox"
                :checked="message.selected"
                @click.stop
                @change="toggleMessageSelection(message.id)"
              />
            </div>
            <div class="message-content">
              <div class="message-header">
                <span class="message-sender">{{ message.sender || 'Unknown' }}</span>
                <span class="message-time">{{ message.timestamp ? formatMessageTime(message.timestamp) : '' }}</span>
              </div>
              <div class="message-body">
                <div v-if="message.type === 'text' && message.text" class="message-text">
                  {{ message.text }}
                </div>
                <div v-else-if="message.media_path" class="message-media">
                  <span class="message-media-icon">{{ getMediaIcon(message.type) }}</span>
                  <span class="message-media-label">{{ getMediaLabel(message.type) }}</span>
                </div>
                <div v-else class="message-type-label">
                  {{ getMediaLabel(message.type) }}
                </div>
              </div>
            </div>
          </div>
          <div v-if="filteredMessages.length === 0" class="messages-empty">
            <p>Сообщения не найдены</p>
          </div>
        </div>
        
        <!-- Load more controls -->
        <div v-if="!allLoaded && filteredMessages.length > 0" class="messages-load-controls">
          <button 
            @click="$emit('loadOneMore')" 
            class="btn-load-more"
            :disabled="loading"
          >
            Загрузить еще сообщение
          </button>
          <button 
            @click="$emit('loadAll')" 
            class="btn-load-all"
            :disabled="loading"
          >
            Загрузить все сообщения
          </button>
        </div>
      </div>
      <div class="messages-actions">
        <p class="messages-count">
          Выбрано: {{ selectedCount }} {{ formatMessageCount(selectedCount) }}
        </p>
        <div class="messages-buttons">
          <button @click="$emit('goBack')" class="btn-back-messages">
            <span class="btn-arrow">←</span>
            Назад
          </button>
          <button 
            @click="$emit('continue')" 
            class="btn-continue" 
            :disabled="selectedCount === 0"
          >
            Начать перенос
            <span class="btn-arrow">→</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch } from 'vue'
import { formatMessageTime, getMediaIcon, getMediaLabel, formatMessageCount } from '../../utils/messageUtils'
import type { Message, MessageProgress } from '../../composables/useMessages'
import { ANIMATION } from '../../constants/landingConstants'

const props = defineProps<{
  visible: boolean
  loading: boolean
  messages: Message[]
  progress: MessageProgress
  allLoaded?: boolean
  totalCount?: number | null
}>()

const messagesListRef = ref<HTMLElement | null>(null)
const filterText = ref('')
const filterType = ref('')
const filterSender = ref('')

// Computed properties
const uniqueSenders = computed(() => {
  const senders = new Set<string>()
  props.messages.forEach(msg => {
    if (msg.sender) senders.add(msg.sender)
  })
  return Array.from(senders).sort()
})

const filteredMessages = computed(() => {
  let result = props.messages
  
  // Filter by text
  if (filterText.value.trim()) {
    const query = filterText.value.toLowerCase()
    result = result.filter(msg => 
      (msg.text?.toLowerCase().includes(query)) ||
      (msg.sender?.toLowerCase().includes(query))
    )
  }
  
  // Filter by type
  if (filterType.value) {
    result = result.filter(msg => msg.type === filterType.value)
  }
  
  // Filter by sender
  if (filterSender.value) {
    result = result.filter(msg => msg.sender === filterSender.value)
  }
  
  return result
})

const selectedCount = computed(() => {
  return props.messages.filter(msg => msg.selected).length
})

const allLoaded = computed(() => props.allLoaded || false)

const emit = defineEmits<{
  goBack: []
  continue: []
  loadOneMore: []
  loadAll: []
  toggleSelection: [messageId: string]
}>()

function toggleMessageSelection(messageId: string) {
  emit('toggleSelection', messageId)
}

// Auto-scroll to bottom when new messages arrive
watch(() => props.messages.length, () => {
  if (messagesListRef.value) {
    nextTick(() => {
      window.setTimeout(() => {
        messagesListRef.value?.scrollTo({
          top: messagesListRef.value?.scrollHeight || 0,
          behavior: 'smooth'
        })
      }, ANIMATION.SCROLL_DELAY)
    })
  }
})

// Scroll to bottom when loading completes
watch(() => props.loading, (newLoading, oldLoading) => {
  if (oldLoading && !newLoading && messagesListRef.value) {
    nextTick(() => {
      window.setTimeout(() => {
        messagesListRef.value?.scrollTo({
          top: messagesListRef.value?.scrollHeight || 0,
          behavior: 'smooth'
        })
      }, ANIMATION.SCROLL_DELAY)
    })
  }
})
</script>

<style scoped>
.messages-visualization {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 40;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.messages-loading {
  color: white;
  font-size: 1.2rem;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.messages-spinner {
  width: 50px;
  height: 50px;
  border: 4px solid rgba(255, 255, 255, 0.2);
  border-top-color: #ffca3a;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.messages-progress-text {
  color: rgba(255, 255, 255, 0.8);
  font-size: 1rem;
  margin: 0;
}

.messages-content {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  padding: 20px;
  pointer-events: auto;
}

.messages-list-container {
  width: 100%;
  max-width: 800px;
  height: calc(100vh - 200px);
  display: flex;
  flex-direction: column;
  background: rgba(20, 20, 30, 0.9);
  backdrop-filter: blur(10px);
  border: 2px solid rgba(255, 255, 255, 0.2);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  overflow: hidden;
}

.messages-list-header {
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(0, 0, 0, 0.2);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.messages-header-info {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.messages-selected-count {
  margin: 0;
  color: #ffca3a;
  font-size: 0.9rem;
  font-weight: 600;
}

.messages-list-header h3 {
  margin: 0;
  color: white;
  font-size: 1.2rem;
  font-weight: 600;
}

.messages-count-header {
  margin: 0;
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.9rem;
}

.messages-filters {
  padding: 12px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(0, 0, 0, 0.1);
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.messages-filter-input,
.messages-filter-select {
  flex: 1;
  min-width: 150px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  color: white;
  font-size: 0.9rem;
}

.messages-filter-input::placeholder {
  color: rgba(255, 255, 255, 0.5);
}

.messages-filter-select {
  cursor: pointer;
}

.messages-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.messages-list::-webkit-scrollbar {
  width: 8px;
}

.messages-list::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
}

.messages-list::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 4px;
}

.messages-list::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.5);
}

.message-item {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 12px 16px;
  transition: all 0.2s ease;
  animation: messageAppear 0.3s ease-out;
}

@keyframes messageAppear {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-item:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.2);
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.message-sender {
  color: #ffca3a;
  font-weight: 600;
  font-size: 0.9rem;
}

.message-time {
  color: rgba(255, 255, 255, 0.5);
  font-size: 0.75rem;
}

.message-body {
  color: rgba(255, 255, 255, 0.9);
}

.message-text {
  line-height: 1.5;
  word-wrap: break-word;
  white-space: pre-wrap;
}

.message-media {
  display: flex;
  align-items: center;
  gap: 8px;
  color: rgba(255, 255, 255, 0.8);
}

.message-media-icon {
  font-size: 1.2rem;
}

.message-media-label {
  font-size: 0.9rem;
}

.message-type-label {
  color: rgba(255, 255, 255, 0.6);
  font-style: italic;
  font-size: 0.9rem;
}

.messages-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: rgba(255, 255, 255, 0.5);
  font-size: 1rem;
}

.messages-load-controls {
  padding: 12px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(0, 0, 0, 0.1);
  display: flex;
  gap: 12px;
  justify-content: center;
}

.btn-load-more,
.btn-load-all {
  padding: 10px 20px;
  font-size: 0.9rem;
  font-weight: 600;
  color: white;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-load-more:hover,
.btn-load-all:hover {
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.3);
}

.btn-load-more:disabled,
.btn-load-all:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-load-all {
  background: rgba(102, 126, 234, 0.2);
  border-color: rgba(102, 126, 234, 0.4);
}

.btn-load-all:hover {
  background: rgba(102, 126, 234, 0.3);
  border-color: rgba(102, 126, 234, 0.5);
}

/* Message type specific styles */
.message-item-text {
  border-left: 3px solid #667eea;
}

.message-item-image {
  border-left: 3px solid #f5576c;
}

.message-item-video {
  border-left: 3px solid #4facfe;
}

.message-item-audio,
.message-item-voice {
  border-left: 3px solid #43e97b;
}

.message-item-document {
  border-left: 3px solid #fa709a;
}

.message-item-sticker {
  border-left: 3px solid #fee140;
}

.message-item-location {
  border-left: 3px solid #30cfd0;
}

.message-item-contact {
  border-left: 3px solid #a8edea;
}

.messages-actions {
  padding: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  pointer-events: auto;
}

.messages-count {
  color: white;
  font-size: 1.1rem;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
  margin: 0;
}

.messages-buttons {
  display: flex;
  gap: 16px;
  align-items: center;
}

.btn-back-messages {
  padding: 14px 32px;
  font-size: 1.1rem;
  font-weight: 600;
  color: white;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
}

.btn-back-messages:hover {
  transform: translateY(-2px);
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.5);
  box-shadow: 0 6px 20px rgba(255, 255, 255, 0.2);
}

.btn-back-messages:active {
  transform: translateY(0);
}

.btn-back-messages .btn-arrow {
  font-size: 1.2rem;
  transition: transform 0.3s ease;
}

.btn-back-messages:hover .btn-arrow {
  transform: translateX(-4px);
}

.btn-continue {
  padding: 14px 32px;
  font-size: 1.1rem;
  font-weight: 600;
  color: white;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 50px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
}

.btn-continue:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.btn-continue:active {
  transform: translateY(0);
}

.btn-continue .btn-arrow {
  font-size: 1.2rem;
  transition: transform 0.3s ease;
}

.btn-continue:hover .btn-arrow {
  transform: translateX(4px);
}

.btn-continue:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.btn-continue:disabled:hover {
  transform: none;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
}
</style>

