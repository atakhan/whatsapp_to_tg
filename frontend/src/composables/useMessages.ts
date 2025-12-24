import { ref, onUnmounted, type Ref } from 'vue'
import { MESSAGES } from '../constants/landingConstants'
import { ANIMATION } from '../constants/landingConstants'
import { normalizeMessageType } from '../utils/messageUtils'

export interface Message {
  id: string
  type: string
  timestamp?: string
  text?: string
  sender?: string
  media_path?: string | null
  selected?: boolean // For message selection
}

export interface MessageLog {
  level: string
  message: string
  timestamp: number
}

export interface MessageProgress {
  loaded: number
  total: number | null
  message: string
}

export interface UseMessagesOptions {
  sessionId: Ref<string | null>
  chatId: Ref<string | null>
  chatName?: Ref<string | null>
  onLogsUpdate?: (logs: MessageLog[]) => void
  activeTimeouts?: number[]
}

/**
 * Composable for loading and managing WhatsApp messages via SSE
 */
export function useMessages(options: UseMessagesOptions) {
  const { sessionId, chatId, chatName, onLogsUpdate, activeTimeouts = [] } = options

  const messages = ref<Message[]>([])
  const messagesLoading = ref(false)
  const messagesProgress = ref<MessageProgress>({ loaded: 0, total: null, message: '' })
  const messagesError = ref<string | null>(null)
  const messagesLogs = ref<MessageLog[]>([])
  const allMessagesLoaded = ref(false)
  const totalMessagesCount = ref<number | null>(null)
  
  let messagesEventSource: EventSource | null = null

  /**
   * Load messages for selected chat via SSE
   */
  async function loadMessages() {
    if (!chatId.value || !sessionId.value) return

    console.log('Loading messages for chat:', { 
      id: chatId.value, 
      name: chatName?.value,
      sessionId: sessionId.value 
    })

    messagesLoading.value = true
    messages.value = []
    messagesLogs.value = []
    messagesError.value = null
    messagesProgress.value = { 
      loaded: 0, 
      total: MESSAGES.INITIAL_LIMIT, 
      message: `Загружаем последние ${MESSAGES.INITIAL_LIMIT} сообщений...` 
    }

    // Close previous event source if exists
    if (messagesEventSource) {
      messagesEventSource.close()
      messagesEventSource = null
    }

    try {
      // Use SSE to stream messages as they are loaded
      const limit = MESSAGES.INITIAL_LIMIT
      const params = new URLSearchParams()
      params.append('limit', limit.toString())
      if (chatName?.value) {
        params.append('chat_name', chatName.value)
      }
      const url = `/api/whatsapp/messages/${sessionId.value}/${chatId.value}/stream?${params.toString()}`
      console.log('Opening SSE connection to:', url, `(limit: ${limit})`)
      const eventSource = new EventSource(url)
      messagesEventSource = eventSource

      // Track loaded message IDs to avoid duplicates
      const loadedMessageIds = new Set<string>()

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          console.log('SSE message received:', data.type, data)

          if (data.type === 'progress') {
            // Update progress
            messagesProgress.value = {
              loaded: data.loaded || 0,
              total: data.total || null,
              message: data.message || `Загружено ${data.loaded || 0} сообщений...`
            }
            console.log('Progress updated:', messagesProgress.value)
          } else if (data.type === 'message' && data.message) {
            // New message received
            const msg = data.message
            const messageId = msg.id || `msg_${messages.value.length}`

            // Filter out duplicates
            if (!loadedMessageIds.has(messageId)) {
              loadedMessageIds.add(messageId)

              messages.value.push({
                id: messageId,
                type: normalizeMessageType(msg.type),
                timestamp: msg.timestamp,
                text: msg.text || '',
                sender: msg.sender || 'Unknown',
                media_path: msg.media_path || null,
                selected: false // Default to not selected
              })

              // Update progress
              messagesProgress.value.loaded = messages.value.length
              console.log('Message added:', messageId, 'Total:', messages.value.length)
            } else {
              console.log('Duplicate message skipped:', messageId)
            }
          } else if (data.type === 'complete') {
            // Last N messages loaded
            messagesLoading.value = false
            const loadedCount = data.total || messages.value.length
            totalMessagesCount.value = data.total_count || null // Total available messages
            allMessagesLoaded.value = messages.value.length >= (totalMessagesCount.value || messages.value.length)
            messagesProgress.value = {
              loaded: loadedCount,
              total: MESSAGES.INITIAL_LIMIT,
              message: loadedCount > 0 
                ? `Загружено ${loadedCount} из ${totalMessagesCount.value || '?'} сообщений` 
                : 'Сообщения не найдены'
            }
            console.log('Loading complete. Total messages:', messages.value.length, 'Total available:', totalMessagesCount.value)
            eventSource.close()
            messagesEventSource = null
          } else if (data.type === 'log') {
            // Log message received
            const log: MessageLog = {
              level: data.level || 'info',
              message: data.message || '',
              timestamp: data.timestamp || Date.now()
            }
            messagesLogs.value.push(log)
            onLogsUpdate?.(messagesLogs.value)
            
            // Auto-scroll background logs
            const timeoutId = window.setTimeout(() => {
              const logsContent = document.querySelector('.background-logs-content')
              if (logsContent) {
                logsContent.scrollTop = logsContent.scrollHeight
              }
            }, ANIMATION.LOGS_SCROLL_DELAY)
            activeTimeouts.push(timeoutId)
            console.log(`[${data.level}]`, data.message)
          } else if (data.type === 'error') {
            // Error occurred
            messagesLoading.value = false
            const errorMessage = data.error || 'Ошибка загрузки сообщений'
            messagesError.value = errorMessage
            messagesProgress.value.message = errorMessage
            console.error('SSE error:', errorMessage)
            eventSource.close()
            messagesEventSource = null
          }
        } catch (err) {
          console.error('Error parsing SSE data:', err, event.data)
        }
      }

      eventSource.onerror = (err) => {
        console.error('SSE error:', err)
        messagesLoading.value = false
        const errorMessage = 'Ошибка подключения к серверу'
        messagesError.value = errorMessage
        messagesProgress.value.message = errorMessage
        eventSource.close()
        messagesEventSource = null
      }

    } catch (err: unknown) {
      console.error('Error loading messages:', err)
      messagesLoading.value = false
      const errorMessage = 'Ошибка загрузки сообщений'
      messagesError.value = errorMessage
      messagesProgress.value.message = errorMessage
    }
  }

  /**
   * Load one more message
   */
  async function loadOneMoreMessage() {
    if (!chatId.value || !sessionId.value || messagesLoading.value || allMessagesLoaded.value) return
    
    const currentCount = messages.value.length
    const limit = currentCount + 1
    
    messagesLoading.value = true
    messagesProgress.value.message = 'Загружаем еще одно сообщение...'
    
    try {
      const params = new URLSearchParams()
      params.append('limit', limit.toString())
      if (chatName?.value) {
        params.append('chat_name', chatName.value)
      }
      const url = `/api/whatsapp/messages/${sessionId.value}/${chatId.value}/stream?${params.toString()}`
      const eventSource = new EventSource(url)
      
      const loadedMessageIds = new Set<string>(messages.value.map(m => m.id))
      
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          if (data.type === 'message' && data.message) {
            const msg = data.message
            const messageId = msg.id || `msg_${messages.value.length}`
            
            if (!loadedMessageIds.has(messageId)) {
              loadedMessageIds.add(messageId)
              messages.value.push({
                id: messageId,
                type: normalizeMessageType(msg.type),
                timestamp: msg.timestamp,
                text: msg.text || '',
                sender: msg.sender || 'Unknown',
                media_path: msg.media_path || null,
                selected: false
              })
            }
          } else if (data.type === 'complete') {
            messagesLoading.value = false
            totalMessagesCount.value = data.total_count || null
            allMessagesLoaded.value = messages.value.length >= (totalMessagesCount.value || messages.value.length)
            messagesProgress.value.message = `Загружено ${messages.value.length} из ${totalMessagesCount.value || '?'} сообщений`
            eventSource.close()
          }
        } catch (err) {
          console.error('Error parsing SSE data:', err)
        }
      }
      
      eventSource.onerror = () => {
        messagesLoading.value = false
        eventSource.close()
      }
    } catch (err) {
      console.error('Error loading one more message:', err)
      messagesLoading.value = false
    }
  }
  
  /**
   * Load all remaining messages
   */
  async function loadAllMessages() {
    if (!chatId.value || !sessionId.value || messagesLoading.value || allMessagesLoaded.value) return
    
    messagesLoading.value = true
    messagesProgress.value.message = 'Загружаем все сообщения...'
    
    try {
      const params = new URLSearchParams()
      params.append('limit', '0') // 0 means load all
      if (chatName?.value) {
        params.append('chat_name', chatName.value)
      }
      const url = `/api/whatsapp/messages/${sessionId.value}/${chatId.value}/stream?${params.toString()}`
      const eventSource = new EventSource(url)
      
      const loadedMessageIds = new Set<string>(messages.value.map(m => m.id))
      
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          if (data.type === 'progress') {
            messagesProgress.value = {
              loaded: data.loaded || 0,
              total: data.total || null,
              message: data.message || `Загружено ${data.loaded || 0} сообщений...`
            }
          } else if (data.type === 'message' && data.message) {
            const msg = data.message
            const messageId = msg.id || `msg_${messages.value.length}`
            
            if (!loadedMessageIds.has(messageId)) {
              loadedMessageIds.add(messageId)
              messages.value.push({
                id: messageId,
                type: normalizeMessageType(msg.type),
                timestamp: msg.timestamp,
                text: msg.text || '',
                sender: msg.sender || 'Unknown',
                media_path: msg.media_path || null,
                selected: false
              })
            }
          } else if (data.type === 'complete') {
            messagesLoading.value = false
            totalMessagesCount.value = data.total_count || messages.value.length
            allMessagesLoaded.value = true
            messagesProgress.value = {
              loaded: messages.value.length,
              total: totalMessagesCount.value,
              message: `Загружено все ${messages.value.length} сообщений`
            }
            eventSource.close()
          }
        } catch (err) {
          console.error('Error parsing SSE data:', err)
        }
      }
      
      eventSource.onerror = () => {
        messagesLoading.value = false
        eventSource.close()
      }
    } catch (err) {
      console.error('Error loading all messages:', err)
      messagesLoading.value = false
    }
  }
  
  /**
   * Toggle message selection by ID
   */
  function toggleMessageSelection(messageId: string) {
    const message = messages.value.find(msg => msg.id === messageId)
    if (message) {
      message.selected = !message.selected
    }
  }

  /**
   * Close messages event source and reset state
   */
  function closeMessages() {
    if (messagesEventSource) {
      messagesEventSource.close()
      messagesEventSource = null
    }
    messages.value = []
    messagesLoading.value = false
    messagesError.value = null
    messagesProgress.value = { loaded: 0, total: null, message: '' }
    messagesLogs.value = []
    allMessagesLoaded.value = false
    totalMessagesCount.value = null
  }

  // Cleanup on unmount
  onUnmounted(() => {
    closeMessages()
  })

  return {
    messages,
    messagesLoading,
    messagesProgress,
    messagesError,
    messagesLogs,
    allMessagesLoaded,
    totalMessagesCount,
    loadMessages,
    loadOneMoreMessage,
    loadAllMessages,
    toggleMessageSelection,
    closeMessages
  }
}

