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
  whatsappChats: [] as WhatsAppChat[],
  selectedWhatsAppChats: [] as string[],

  // Telegram session
  telegramSessionActive: false,
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

  reset() {
    this.whatsappSessionActive = false
    this.whatsappChats = []
    this.selectedWhatsAppChats = []
    this.telegramSessionActive = false
    this.telegramChats = []
    this.chatMappings = []
    this.migrationProgress = null
    this.migrationComplete = false
    this.migrationReport = null
  }
})

