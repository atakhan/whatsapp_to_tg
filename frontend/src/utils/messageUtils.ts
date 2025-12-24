/**
 * Normalize message type to match CSS classes
 */
export function normalizeMessageType(type: string): string {
  const normalized = type?.toLowerCase() || 'text'
  
  // Map various type names to standard types
  const typeMap: Record<string, string> = {
    'text': 'text',
    'image': 'image',
    'photo': 'image',
    'video': 'video',
    'audio': 'audio',
    'voice': 'voice',
    'voice_message': 'voice',
    'document': 'document',
    'file': 'document',
    'sticker': 'sticker',
    'location': 'location',
    'contact': 'contact',
    'gif': 'image',
    'ptt': 'voice' // Push-to-talk (voice message)
  }
  
  return typeMap[normalized] || 'text'
}

/**
 * Format message timestamp to human-readable format
 */
export function formatMessageTime(timestamp: string): string {
  if (!timestamp) return ''
  try {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)
    
    if (diffMins < 1) return 'только что'
    if (diffMins < 60) return `${diffMins} мин назад`
    if (diffHours < 24) return `${diffHours} ч назад`
    if (diffDays < 7) return `${diffDays} дн назад`
    
    return date.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })
  } catch {
    return timestamp
  }
}

/**
 * Get icon emoji for message type
 */
export function getMediaIcon(type: string): string {
  const icons: Record<string, string> = {
    'image': '🖼️',
    'video': '🎥',
    'audio': '🎵',
    'voice': '🎤',
    'document': '📄',
    'sticker': '😊',
    'location': '📍',
    'contact': '👤',
    'text': '💬'
  }
  return icons[type] || '📎'
}

/**
 * Get label for message type
 */
export function getMediaLabel(type: string): string {
  const labels: Record<string, string> = {
    'image': 'Изображение',
    'video': 'Видео',
    'audio': 'Аудио',
    'voice': 'Голосовое сообщение',
    'document': 'Документ',
    'sticker': 'Стикер',
    'location': 'Местоположение',
    'contact': 'Контакт',
    'text': 'Текст'
  }
  return labels[type] || 'Сообщение'
}

/**
 * Format message count with proper Russian pluralization
 */
export function formatMessageCount(count: number): string {
  if (count === 1) return 'сообщение'
  if (count < 5) return 'сообщения'
  return 'сообщений'
}

