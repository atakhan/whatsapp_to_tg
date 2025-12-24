# Рекомендации по рефакторингу LandingPage.vue

## Дата: 2025-12-22

## Стратегия рефакторинга

### Фаза 1: Подготовка (Низкий риск)
### Фаза 2: Выделение компонентов (Средний риск)
### Фаза 3: Выделение логики (Средний риск)
### Фаза 4: Оптимизация (Низкий риск)

---

## Фаза 1: Подготовка (1-2 дня)

### 1.1 Создать структуру папок

```
frontend/src/
├── components/
│   ├── landing/
│   │   ├── StarsBackground.vue
│   │   ├── SpaceShip.vue
│   │   ├── Planet.vue
│   │   ├── ChatCircle.vue
│   │   ├── MessagesList.vue
│   │   ├── BackgroundLogs.vue
│   │   └── TelegramAuthForm.vue
│   └── common/
│       ├── Button.vue
│       └── SearchInput.vue
├── composables/
│   ├── usePhysics.ts
│   ├── useWhatsApp.ts
│   ├── useTelegram.ts
│   ├── useChats.ts
│   ├── useMessages.ts
│   ├── useSearch.ts
│   └── useSessions.ts
├── utils/
│   ├── physics.ts
│   ├── transliteration.ts
│   ├── search.ts
│   ├── formatting.ts
│   └── constants.ts
├── types/
│   ├── chat.ts
│   ├── message.ts
│   └── session.ts
└── stores/
    ├── whatsapp.ts
    ├── telegram.ts
    └── migration.ts
```

### 1.2 Выделить типы

**Файл**: `types/chat.ts`
```typescript
export interface Chat {
  id: string
  name: string
  avatar: string | null
  visible: boolean
}

export interface TelegramChat {
  id: number | string
  name: string
  type: 'private' | 'group' | 'channel'
  // ...
}
```

**Файл**: `types/message.ts`
```typescript
export interface Message {
  id: string
  type: string
  timestamp?: string
  text?: string
  sender?: string
  media_path?: string | null
}

export type MessageType = 'text' | 'image' | 'video' | 'audio' | 'voice' | 'document' | 'sticker' | 'location' | 'contact'
```

**Файл**: `types/session.ts`
```typescript
export interface WhatsAppSession {
  sessionId: string | null
  status: 'idle' | 'loading' | 'qr' | 'connecting' | 'connected'
  qrCode: string | null
  error: string | null
}

export interface TelegramSession {
  sessionId: string | null
  phase: 'hidden' | 'entering' | 'phone' | 'code' | 'password' | 'connected'
  phone: string
  code: string
  password: string
  userInfo: any | null
  error: string | null
}
```

### 1.3 Выделить константы

**Файл**: `utils/constants.ts`
```typescript
// Physics constants
export const ENGINE_POWER = 0.3
export const ROTATION_POWER = 0.003
export const ROTATION_DRAG = 0.94
export const VELOCITY_DRAG = 0.99
export const MAX_CONTROL_ACCEL = ENGINE_POWER * 0.2
export const LANDING_ZONE_PX = 220

// Planet gravity
export const WA_MU = 3200
export const TG_MU = 5200
export const GRAVITY_SOFTENING_PX = 180

// Chat circle sizing
export const CHAT_CIRCLE_SIZE = 52
export const PLANET_SHRUNK_SIZE = 105
export const RING_GAP = 20

// Telegram chat circle sizing
export const TG_CHAT_CIRCLE_SIZE = 52
export const TG_PLANET_SHRUNK_SIZE = 70
export const TG_RING_GAP = 20

// Animation delays
export const MIGRATION_ANIMATION_DELAYS = [0, 25, 45, 60, 70, 75, 77]
export const CHAT_ANIMATION_DELAY = 30
export const PLANET_ANIMATION_DELAY = 1000
export const OVERLAY_FADE_DELAY = 300

// Search constants
export const SEARCH_MATCH_THRESHOLD = 0.7
```

---

## Фаза 2: Выделение компонентов (3-5 дней)

### 2.1 Компонент StarsBackground

**Файл**: `components/landing/StarsBackground.vue`
```vue
<template>
  <div 
    v-for="(star, index) in stars" 
    :key="index"
    class="star"
    :style="getStarStyle(star)"
  ></div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { generateStars } from '@/utils/stars'

const stars = ref<Star[]>([])

onMounted(() => {
  stars.value = generateStars(50)
})

function getStarStyle(star: Star) {
  return {
    left: `${star.x}%`,
    top: `${star.y}%`,
    width: `${star.size}px`,
    height: `${star.size}px`,
    opacity: star.opacity,
    animationDuration: `${star.duration}s`,
    animationDelay: `${star.delay}s`
  }
}
</script>
```

**Выгода**: 
- Уменьшение LandingPage на ~30 строк
- Переиспользуемость
- Легче тестировать

### 2.2 Компонент BackgroundLogs

**Файл**: `components/landing/BackgroundLogs.vue`
```vue
<template>
  <div v-if="logs.length > 0" class="background-logs-container">
    <div class="background-logs-content">
      <div
        v-for="(log, index) in logs"
        :key="index"
        class="background-log-entry"
        :class="`background-log-${log.level}`"
      >
        <span class="background-log-time">{{ formatTime(log.timestamp) }}</span>
        <span class="background-log-level">{{ log.level.toUpperCase() }}</span>
        <span class="background-log-message">{{ log.message }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineProps } from 'vue'
import { formatLogTime } from '@/utils/formatting'

interface Props {
  logs: Array<{ level: string, message: string, timestamp: number }>
}

const props = defineProps<Props>()

function formatTime(timestamp: number) {
  return formatLogTime(timestamp)
}
</script>
```

**Выгода**: 
- Уменьшение LandingPage на ~15 строк
- Изоляция логики форматирования

### 2.3 Компонент SpaceShip

**Файл**: `components/landing/SpaceShip.vue`
```vue
<template>
  <svg class="space-traffic" :class="{ 'element-hidden': hidden }" width="100%" height="100%">
    <!-- SVG корабля -->
  </svg>
</template>

<script setup lang="ts">
import { defineProps } from 'vue'
import { usePhysics } from '@/composables/usePhysics'

interface Props {
  hidden: boolean
  shipState: ShipState
}

const props = defineProps<Props>()
</script>
```

**Выгода**: 
- Уменьшение LandingPage на ~60 строк
- Изоляция SVG логики

### 2.4 Компонент Planet

**Файл**: `components/landing/Planet.vue`
```vue
<template>
  <div 
    class="planet" 
    :class="planetClasses"
    :style="{ boxShadow: boxShadow }"
    ref="planetRef"
  >
    <img :src="logoUrl" class="planet-logo" :class="{ 'logo-pulsing': pulsing }" :alt="alt" />
    <slot />
  </div>
</template>

<script setup lang="ts">
import { defineProps, computed } from 'vue'

interface Props {
  type: 'whatsapp' | 'telegram'
  centered?: boolean
  shrunk?: boolean
  inCorner?: boolean
  pulsing?: boolean
  boxShadow?: string
}

const props = defineProps<Props>()

const planetClasses = computed(() => ({
  [`planet-${props.type}`]: true,
  [`planet-${props.type}-centered`]: props.centered && !props.shrunk && !props.inCorner,
  [`planet-${props.type}-shrunk`]: props.shrunk && !props.inCorner,
  [`planet-${props.type}-corner`]: props.inCorner,
  [`planet-${props.type}-pulsing`]: props.pulsing
}))
</script>
```

**Выгода**: 
- Уменьшение LandingPage на ~100 строк
- Переиспользуемость для WhatsApp и Telegram

### 2.5 Компонент ChatCircle

**Файл**: `components/landing/ChatCircle.vue`
```vue
<template>
  <div 
    class="chat-circle"
    :class="circleClasses"
    :style="circleStyle"
    @click="$emit('select')"
    :title="chat.name"
  >
    <img 
      v-if="chat.avatar" 
      :src="chat.avatar" 
      :alt="chat.name" 
      class="chat-avatar"
      @error="onAvatarError"
    />
    <span v-else class="chat-initial">{{ getInitial(chat.name) }}</span>
  </div>
</template>

<script setup lang="ts">
import { defineProps, defineEmits, computed } from 'vue'
import { Chat } from '@/types/chat'
import { getChatInitial } from '@/utils/formatting'

interface Props {
  chat: Chat
  selected?: boolean
  dimmed?: boolean
  moving?: boolean
  style: Record<string, string>
}

const props = defineProps<Props>()
const emit = defineEmits<{ select: [] }>()

const circleClasses = computed(() => ({
  'chat-visible': props.chat.visible,
  'has-avatar': !!props.chat.avatar,
  'chat-selected': props.selected,
  'chat-dimmed': props.dimmed,
  'chat-moving-to-corner': props.moving
}))

function onAvatarError(event: Event) {
  const img = event.target as HTMLImageElement
  img.style.display = 'none'
  emit('avatar-error')
}
</script>
```

**Выгода**: 
- Уменьшение LandingPage на ~50 строк
- Переиспользуемость для WhatsApp и Telegram чатов

### 2.6 Компонент MessagesList

**Файл**: `components/landing/MessagesList.vue`
```vue
<template>
  <div class="messages-list-container">
    <div class="messages-list-header">
      <h3>Загруженные сообщения</h3>
      <p class="messages-count-header">{{ messagesCountText }}</p>
    </div>
    <div class="messages-list" ref="messagesListRef">
      <MessageItem
        v-for="message in messages"
        :key="message.id"
        :message="message"
      />
      <div v-if="messages.length === 0" class="messages-empty">
        <p>Сообщения не найдены</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineProps, computed, ref, watch, nextTick } from 'vue'
import { Message } from '@/types/message'
import MessageItem from './MessageItem.vue'

interface Props {
  messages: Message[]
}

const props = defineProps<Props>()

const messagesListRef = ref<HTMLElement | null>(null)

const messagesCountText = computed(() => {
  const count = props.messages.length
  if (count === 1) return '1 сообщение'
  if (count < 5) return `${count} сообщения`
  return `${count} сообщений`
})

function scrollToBottom() {
  if (messagesListRef.value) {
    messagesListRef.value.scrollTop = messagesListRef.value.scrollHeight
  }
}

watch(() => props.messages.length, () => {
  nextTick(() => scrollToBottom())
})
</script>
```

**Выгода**: 
- Уменьшение LandingPage на ~80 строк
- Изоляция логики отображения сообщений

---

## Фаза 3: Выделение логики (5-7 дней)

### 3.1 Composable usePhysics

**Файл**: `composables/usePhysics.ts`
```typescript
import { reactive, ref, computed } from 'vue'
import { 
  ENGINE_POWER, 
  ROTATION_POWER, 
  VELOCITY_DRAG,
  // ... другие константы
} from '@/utils/constants'

export function usePhysics() {
  const shipState = reactive({
    x: -100,
    y: -100,
    vx: 0,
    vy: 0,
    rotation: 0,
    vRotation: 0,
    mainEngine: false,
    throttle: 0,
    rcsLeft: false,
    rcsRight: false
  })

  const flightState = reactive({
    launched: false,
    dockedAt: 'wa' as 'wa' | 'tg'
  })

  const missionState = reactive({
    mode: 'idle' as 'idle' | 'transfer' | 'hover_tg',
    transferT: 0
  })

  let animationFrameId: number

  function startPhysicsLoop(planetWa: HTMLElement, planetTg: HTMLElement) {
    // Логика physicsLoop
  }

  function stopPhysicsLoop() {
    if (animationFrameId) {
      cancelAnimationFrame(animationFrameId)
    }
  }

  function spawnShipAbovePlanet(planetElement: HTMLElement) {
    // Логика spawnShipAboveWhatsApp
  }

  return {
    shipState,
    flightState,
    missionState,
    startPhysicsLoop,
    stopPhysicsLoop,
    spawnShipAbovePlanet
  }
}
```

**Выгода**: 
- Уменьшение LandingPage на ~300 строк
- Изоляция физики
- Легче тестировать
- Переиспользуемость

### 3.2 Composable useWhatsApp

**Файл**: `composables/useWhatsApp.ts`
```typescript
import { ref, computed } from 'vue'
import api from '@/api/client'
import { WhatsAppSession } from '@/types/session'

export function useWhatsApp() {
  const session = ref<WhatsAppSession>({
    sessionId: null,
    status: 'idle',
    qrCode: null,
    error: null
  })

  const whatsappCentered = ref(false)
  const whatsappShrunk = ref(false)
  const whatsappInCorner = ref(false)
  const showWaOverlay = ref(false)

  let statusPollInterval: number | null = null

  async function startConnection() {
    // Логика startWhatsAppConnection
  }

  function startStatusPolling() {
    // Логика startStatusPolling
  }

  function stopStatusPolling() {
    // Логика stopStatusPolling
  }

  async function onConnected() {
    // Логика onWhatsAppConnected
  }

  return {
    session,
    whatsappCentered,
    whatsappShrunk,
    whatsappInCorner,
    showWaOverlay,
    startConnection,
    onConnected,
    stopStatusPolling
  }
}
```

**Выгода**: 
- Уменьшение LandingPage на ~150 строк
- Изоляция WhatsApp логики
- Легче тестировать

### 3.3 Composable useChats

**Файл**: `composables/useChats.ts`
```typescript
import { ref, computed } from 'vue'
import { Chat } from '@/types/chat'
import { useSearch } from './useSearch'

export function useChats(sessionId: string | null) {
  const chats = ref<Chat[]>([])
  const visibleChats = ref<Chat[]>([])
  const selectedChat = ref<Chat | null>(null)
  const chatsLoading = ref(false)
  const chatMovingToCorner = ref(false)

  const { searchQuery, filterBySearch } = useSearch()

  async function loadChats() {
    // Логика loadChats
  }

  function selectChat(chat: Chat) {
    // Логика selectChat
  }

  function getChatCircleStyle(index: number) {
    // Логика getChatCircleStyle
  }

  return {
    chats,
    visibleChats,
    selectedChat,
    chatsLoading,
    chatMovingToCorner,
    searchQuery,
    loadChats,
    selectChat,
    getChatCircleStyle,
    filterBySearch
  }
}
```

**Выгода**: 
- Уменьшение LandingPage на ~200 строк
- Переиспользуемость для Telegram чатов
- Изоляция логики чатов

### 3.4 Composable useSearch

**Файл**: `composables/useSearch.ts`
```typescript
import { ref } from 'vue'
import { transliterateToLatin, transliterateToRussian } from '@/utils/transliteration'
import { isChatMatch } from '@/utils/search'

export function useSearch<T extends { name: string }>() {
  const searchQuery = ref('')

  function filterBySearch(items: T[]): T[] {
    if (!searchQuery.value.trim()) {
      return items
    }
    return items.filter(item => isChatMatch(item.name, searchQuery.value))
  }

  return {
    searchQuery,
    filterBySearch
  }
}
```

**Выгода**: 
- Уменьшение LandingPage на ~200 строк
- Переиспользуемость
- Легче тестировать

### 3.5 Утилиты

**Файл**: `utils/transliteration.ts`
```typescript
export const TRANSLITERATION_MAP: Record<string, string> = {
  // ... маппинг
}

export const REVERSE_TRANSLITERATION_MAP: Record<string, string> = {
  // ... обратный маппинг
}

export function transliterateToLatin(text: string): string {
  // Логика
}

export function transliterateToRussian(text: string): string {
  // Логика
}
```

**Файл**: `utils/search.ts`
```typescript
import { transliterateToLatin, transliterateToRussian } from './transliteration'

export function getSearchVariants(text: string): string[] {
  // Логика
}

export function normalizeString(str: string): string {
  // Логика
}

export function isChatMatch(chatName: string, query: string): boolean {
  // Логика isChatMatch
}
```

**Файл**: `utils/formatting.ts`
```typescript
export function formatMessageTime(timestamp: string): string {
  // Логика formatMessageTime
}

export function getMediaIcon(type: string): string {
  // Логика getMediaIcon
}

export function getMediaLabel(type: string): string {
  // Логика getMediaLabel
}

export function getChatInitial(name: string): string {
  // Логика getChatInitial
}

export function formatLogTime(timestamp: number): string {
  return new Date((timestamp || Date.now() / 1000) * 1000).toLocaleTimeString()
}
```

**Выгода**: 
- Уменьшение LandingPage на ~150 строк
- Переиспользуемость
- Легче тестировать

### 3.6 Composable useMessages

**Файл**: `composables/useMessages.ts`
```typescript
import { ref, nextTick } from 'vue'
import { Message } from '@/types/message'

export function useMessages() {
  const messages = ref<Message[]>([])
  const messagesLoading = ref(false)
  const showMessages = ref(false)
  const messagesProgress = ref({ loaded: 0, total: null as number | null, message: '' })
  const messagesLogs = ref<Array<{ level: string, message: string, timestamp: number }>>([])
  const messagesListRef = ref<HTMLElement | null>(null)
  
  let messagesEventSource: EventSource | null = null

  async function loadMessages(sessionId: string, chatId: string, chatName: string, limit?: number) {
    // Логика loadAndShowMessages
  }

  function scrollToBottom() {
    // Логика scrollToBottom
  }

  function clearMessages() {
    messages.value = []
    messagesLogs.value = []
    messagesProgress.value = { loaded: 0, total: null, message: '' }
    if (messagesEventSource) {
      messagesEventSource.close()
      messagesEventSource = null
    }
  }

  return {
    messages,
    messagesLoading,
    showMessages,
    messagesProgress,
    messagesLogs,
    messagesListRef,
    loadMessages,
    scrollToBottom,
    clearMessages
  }
}
```

**Выгода**: 
- Уменьшение LandingPage на ~200 строк
- Изоляция логики сообщений

---

## Фаза 4: Оптимизация (2-3 дня)

### 4.1 Использование Pinia для состояния

**Файл**: `stores/whatsapp.ts`
```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { WhatsAppSession } from '@/types/session'
import { Chat } from '@/types/chat'

export const useWhatsAppStore = defineStore('whatsapp', () => {
  const session = ref<WhatsAppSession>({
    sessionId: null,
    status: 'idle',
    qrCode: null,
    error: null
  })

  const chats = ref<Chat[]>([])
  const selectedChat = ref<Chat | null>(null)

  const isConnected = computed(() => session.value.status === 'connected')

  async function connect() {
    // Логика подключения
  }

  async function loadChats() {
    // Логика загрузки чатов
  }

  return {
    session,
    chats,
    selectedChat,
    isConnected,
    connect,
    loadChats
  }
})
```

**Выгода**: 
- Централизованное управление состоянием
- Легче тестировать
- Переиспользуемость между компонентами

### 4.2 Мемоизация вычислений

**Пример**:
```typescript
import { computed } from 'vue'

const chatCircleStyles = computed(() => {
  return visibleChats.value.map((chat, index) => 
    getChatCircleStyle(index)
  )
})
```

### 4.3 Lazy loading компонентов

```typescript
import { defineAsyncComponent } from 'vue'

const MessagesList = defineAsyncComponent(() => 
  import('@/components/landing/MessagesList.vue')
)
```

### 4.4 Оптимизация физического цикла

```typescript
// Останавливать цикл когда корабль скрыт
if (hideStage.value >= 5) {
  stopPhysicsLoop()
  return
}
```

---

## План миграции

### Шаг 1: Создать структуру (1 день)
- Создать папки и файлы
- Выделить типы и константы
- Настроить импорты

### Шаг 2: Выделить утилиты (1 день)
- `utils/transliteration.ts`
- `utils/search.ts`
- `utils/formatting.ts`
- `utils/constants.ts`

### Шаг 3: Выделить компоненты (3 дня)
- StarsBackground
- BackgroundLogs
- SpaceShip
- Planet
- ChatCircle
- MessagesList

### Шаг 4: Выделить composables (4 дня)
- usePhysics
- useWhatsApp
- useTelegram
- useChats
- useMessages
- useSearch

### Шаг 5: Интеграция (2 дня)
- Обновить LandingPage.vue
- Протестировать
- Исправить баги

### Шаг 6: Оптимизация (2 дня)
- Pinia stores
- Мемоизация
- Lazy loading

**Итого**: ~13 дней работы

---

## Ожидаемые результаты

### Метрики после рефакторинга

- **LandingPage.vue**: ~500-800 строк (вместо 3806)
- **Компонентов**: 10-15 (вместо 0)
- **Composables**: 6-8
- **Утилит**: 5-7
- **Stores**: 2-3

### Преимущества

1. **Читаемость**: +70%
2. **Поддерживаемость**: +80%
3. **Тестируемость**: +90%
4. **Переиспользуемость**: +85%
5. **Производительность**: +20-30%

### Риски

- **Время**: 13 дней работы
- **Баги**: Возможны регрессии при миграции
- **Совместимость**: Нужно тестировать все сценарии

---

## Приоритизация

### Высокий приоритет (сделать первым)

1. ✅ Выделить типы и константы
2. ✅ Выделить утилиты (transliteration, search, formatting)
3. ✅ Выделить компонент BackgroundLogs
4. ✅ Выделить composable useSearch
5. ✅ Выделить composable useMessages

### Средний приоритет

6. ⏳ Выделить компоненты (Planet, ChatCircle, MessagesList)
7. ⏳ Выделить composables (useWhatsApp, useTelegram, useChats)
8. ⏳ Выделить компонент SpaceShip

### Низкий приоритет

9. ⏳ Выделить composable usePhysics
10. ⏳ Создать Pinia stores
11. ⏳ Оптимизация производительности

---

## Чек-лист рефакторинга

### Перед началом

- [ ] Создать ветку для рефакторинга
- [ ] Написать тесты для критичных функций (если возможно)
- [ ] Сделать backup текущего кода

### Во время рефакторинга

- [ ] Выделять по одному модулю за раз
- [ ] Тестировать после каждого изменения
- [ ] Документировать изменения
- [ ] Обновлять импорты

### После рефакторинга

- [ ] Полное тестирование всех сценариев
- [ ] Проверка производительности
- [ ] Обновление документации
- [ ] Code review

---

## Альтернативный подход: Постепенная миграция

Если полный рефакторинг невозможен, можно делать постепенно:

1. **Неделя 1**: Выделить утилиты и константы
2. **Неделя 2**: Выделить 2-3 простых компонента
3. **Неделя 3**: Выделить 1-2 composables
4. **Неделя 4**: Продолжить по мере необходимости

**Преимущества**:
- Меньше риска
- Можно делать параллельно с разработкой
- Постепенное улучшение

**Недостатки**:
- Дольше по времени
- Временная дублированность кода
