import { defineStore } from 'pinia'

export const useMigrationStore = defineStore('migration', {
  state: () => ({
    sessionId: '',
    userTelegramId: null,
    userInfo: null,
    parsedMessagesCount: 0,
    selectedChatId: null,
    selectedChatName: '',
    migrationStatus: null
  }),
  
  actions: {
    setSessionId(sessionId) {
      this.sessionId = sessionId
    },
    
    setUserTelegramId(userId) {
      this.userTelegramId = userId
    },
    
    setUserInfo(userInfo) {
      this.userInfo = userInfo
    },
    
    setParsedMessagesCount(count) {
      this.parsedMessagesCount = count
    },
    
    setSelectedChat(chatId, chatName) {
      this.selectedChatId = chatId
      this.selectedChatName = chatName
    },
    
    setMigrationStatus(status) {
      this.migrationStatus = status
    },
    
    reset() {
      this.sessionId = ''
      this.userTelegramId = null
      this.userInfo = null
      this.parsedMessagesCount = 0
      this.selectedChatId = null
      this.selectedChatName = ''
      this.migrationStatus = null
    }
  }
})
