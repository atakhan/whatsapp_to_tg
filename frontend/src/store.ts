import { reactive } from 'vue'

export interface WhatsAppChat {
  id: string
  name: string
  type: 'personal' | 'group'
  messageCount: number
  avatar?: string
}

export interface TelegramChat {
  id: string | number
  name: string
  type: 'personal' | 'group' | 'channel'
}

export interface ChatMapping {
  whatsappChatId: string
  telegramChatId: string | number | 'new' | 'saved'
  telegramChatName?: string
}

export interface MigrationProgress {
  current: number
  total: number
  currentOperation: string
  errors: string[]
}

export const store = reactive({
  // WhatsApp session
  whatsappSessionActive: false,
  whatsappSessionId: null as string | null,
  whatsappChats: [] as WhatsAppChat[],
  selectedWhatsAppChats: [] as string[],

  // Telegram session
  telegramSessionActive: false,
  telegramUserId: null as number | null,
  telegramChats: [] as TelegramChat[],

  // Chat mappings
  chatMappings: [] as ChatMapping[],

  // Migration progress
  migrationProgress: null as MigrationProgress | null,
  migrationComplete: false,
  migrationReport: null as { log: string; errors: string[] } | null,

  // Actions
  setWhatsAppChats(chats: WhatsAppChat[]) {
    this.whatsappChats = chats
  },

  setSelectedWhatsAppChats(chatIds: string[]) {
    this.selectedWhatsAppChats = chatIds
  },

  setTelegramChats(chats: TelegramChat[]) {
    this.telegramChats = chats
  },

  setChatMappings(mappings: ChatMapping[]) {
    this.chatMappings = mappings
  },

  setMigrationProgress(progress: MigrationProgress) {
    this.migrationProgress = progress
  },

  setMigrationComplete(complete: boolean) {
    this.migrationComplete = complete
  },

  setMigrationReport(report: { log: string; errors: string[] }) {
    this.migrationReport = report
  },

  setWhatsAppSessionId(sessionId: string | null) {
    this.whatsappSessionId = sessionId
    // Also save to localStorage for persistence across page reloads
    if (sessionId) {
      localStorage.setItem('whatsapp_session_id', sessionId)
    } else {
      localStorage.removeItem('whatsapp_session_id')
    }
  },

  setTelegramUserId(userId: number | null) {
    this.telegramUserId = userId
  },

  reset() {
    this.whatsappSessionActive = false
    this.whatsappSessionId = null
    this.whatsappChats = []
    this.selectedWhatsAppChats = []
    this.telegramSessionActive = false
    this.telegramUserId = null
    this.telegramChats = []
    this.chatMappings = []
    this.migrationProgress = null
    this.migrationComplete = false
    this.migrationReport = null
  }
})

