<template>
  <div class="page landing-page" @click="onPageClick">
    <!-- Stars -->
    <StarsBackground />


    <!-- Migration loading overlay -->
    <div v-if="migrationInProgress" class="migration-overlay">
      <div class="migration-loading-circle">
        <div class="loading-circle"></div>
        <p class="migration-status-text">{{ migrationStatus }}</p>
        <p v-if="migrationProgress.total" class="migration-progress-text">
          {{ migrationProgress.loaded }} / {{ migrationProgress.total }}
        </p>
      </div>
    </div>
    
    <!-- Migration completion screen -->
    <div v-if="migrationCompleted && migrationResult" class="migration-completion-overlay">
      <div class="migration-completion-content">
        <div class="completion-icon">✅</div>
        <h2 class="completion-title">Перенос завершен!</h2>
        
        <div class="completion-stats">
          <div class="stat-item">
            <span class="stat-label">Перенесено сообщений:</span>
            <span class="stat-value">{{ migrationResult.successful }} / {{ migrationResult.total }}</span>
          </div>
          <div v-if="migrationResult.failed > 0" class="stat-item stat-error">
            <span class="stat-label">Ошибок:</span>
            <span class="stat-value">{{ migrationResult.failed }}</span>
          </div>
        </div>
        
        <div class="completion-chats-info">
          <div class="chat-info-item">
            <span class="chat-info-label">Из WhatsApp:</span>
            <span class="chat-info-name">{{ selectedChat?.name || 'Неизвестный чат' }}</span>
          </div>
          <div class="chat-info-item">
            <span class="chat-info-label">В Telegram:</span>
            <span class="chat-info-name">{{ selectedTelegramChat?.name || 'Неизвестный чат' }}</span>
          </div>
        </div>
        
        <div v-if="migrationResult.errors && migrationResult.errors.length > 0" class="completion-errors">
          <h3>Ошибки:</h3>
          <ul>
            <li v-for="(error, index) in migrationResult.errors" :key="index">{{ error }}</li>
          </ul>
        </div>
        
        <div class="completion-actions">
          <button @click="selectAnotherChat" class="btn-select-another">
            Выбрать другой чат
          </button>
          <button @click="finishSession" class="btn-finish-session">
            Завершить сессию
          </button>
        </div>
      </div>
    </div>

    <!-- Space layer: ship + engines (physics-driven) -->
    <RocketShip :shipState="shipState" :hidden="!shouldShowRocket" />
    
    <!-- Title for chat selection -->
    
    <!-- Destination selection panel -->
    <div v-if="showDestinationSelection" class="destination-selection-panel">
      <!-- Subtitle for selected WhatsApp chat -->
      <p class="selected-chat-subtitle">Выбранный чат из вастапп:</p>
      
      <!-- Selected WhatsApp chat block -->
      <div class="selected-wa-chat-block">
        <div class="wa-chat-circle">
          <img v-if="selectedChat?.avatar" :src="selectedChat.avatar" :alt="selectedChat.name" class="wa-chat-avatar" />
          <span v-else class="wa-chat-initial">{{ getChatInitial(selectedChat?.name || '') }}</span>
        </div>
        <p class="wa-chat-name">{{ selectedChat?.name }}</p>
      </div>
      
      <!-- Title for Telegram chat selection -->
      <h3 class="destination-title">Куда перенести ватсап-чат?</h3>
      
      <!-- Loading/Error states -->
      <div v-if="telegramChatsLoading" class="chats-loading-message">
        <p>Загрузка чатов...</p>
      </div>
      <div v-else-if="telegramChatsError" class="chats-error-message">
        <p>{{ telegramChatsError }}</p>
        <button @click="loadTelegramChats" class="chats-retry-btn">Повторить</button>
      </div>
      
      <!-- Start migration button -->
      <button 
        v-if="!telegramChatsLoading && !telegramChatsError"
        @click="startDataMigration" 
        class="btn-start-migration"
        :disabled="!canStartMigration"
      >
        Начать перенос
        <span class="btn-arrow">→</span>
      </button>
    </div>
    
    <!-- Telegram chat circles orbiting around Telegram planet -->
    <div 
      v-for="(tgChat, index) in visibleTelegramChats" 
      :key="tgChat.id"
      class="telegram-chat-circle"
      :class="{ 
        'tg-chat-visible': tgChat.visible, 
        'tg-chat-selected': selectedTelegramChat?.id === tgChat.id,
        'tg-chat-dimmed': selectedTelegramChat && selectedTelegramChat.id !== tgChat.id
      }"
      :style="getTelegramChatCircleStyle(index)"
      @click="selectTelegramChat(tgChat)"
      :title="tgChat.name"
    >
      <span class="tg-chat-initial">{{ getChatInitial(tgChat.name) }}</span>
    </div>
    
    <!-- Header at top -->
    <div class="header-section">
      <div class="badge">TETRAKOM</div>
    </div>

    <!-- Split screen: WhatsApp and Telegram -->
    <div class="split-screen-wrapper">
      <div class="split-section split-whatsapp">
        <div class="planet-container planet-container-wa">
          <!-- WhatsApp Planet -->
          <div 
            class="planet planet-wa" 
            ref="planetWa" 
            :style="{ boxShadow: waBoxShadow }" 
            :class="{ 
              'planet-wa-corner': whatsappInCorner,
              'planet-wa-pulsing': chatsLoading,
              'planet-wa-clickable': waStatus === 'idle' || (waStatus === 'connected' && (selectedChat || chatsLoading || chats.length === 0)),
              'planet-wa-qr': waStatus === 'qr' && qrCode,
              'planet-wa-qr-collapsing': qrCode && waStatus === 'connected',
              'planet-wa-shrinking': chatsLoading && waStatus === 'connected' && !selectedChat,
              'planet-wa-with-chats': waStatus === 'connected' && !selectedChat && !chatsLoading && chats.length > 0,
              'planet-wa-chat-selected': waStatus === 'connected' && selectedChat && !chatsLoading,
              'planet-wa-messages-loaded': messages.length > 0 && !messagesLoading && selectedChat
            }"
            @click="onWhatsAppPlanetClick"
          >
            <!-- Lock icon if not connected -->
            <div 
              v-if="waStatus === 'idle' || waStatus === 'loading'"
              class="planet-lock"
              :class="{ 'planet-lock-fading': waStatus === 'loading' }"
            >
              🔒
            </div>
            <img src="https://upload.wikimedia.org/wikipedia/commons/6/6b/WhatsApp.svg" class="planet-logo" :class="{ 'logo-pulsing': chatsLoading || waStatus === 'loading' || waStatus === 'qr' }" alt="WhatsApp Planet" />
            
            <!-- WhatsApp connection overlay -->
            <div 
              class="wa-overlay" 
              :class="{ 
                'overlay-visible': (waStatus === 'qr' || waError) || (showWaOverlay && waStatus !== 'idle' && waStatus !== 'loading' && waStatus !== 'connected'),
                'overlay-in-planet': true,
                'overlay-no-background': waStatus === 'qr'
              }"
            >
              <!-- QR Code state -->
              <div v-if="waStatus === 'qr' && qrCode" class="wa-qr">
                <img :src="`data:image/png;base64,${qrCode}`" alt="QR Code" class="wa-qr-image" />
              </div>
              
              <!-- Error state -->
              <div v-if="waError" class="wa-error">
                <p>{{ waError }}</p>
                <button @click.stop="retryConnection" class="wa-retry-btn">Попробовать снова</button>
              </div>
            </div>
          </div>
          
          <!-- Messages card (when messages are loaded) -->
          <div 
            v-if="messages.length > 0 && !messagesLoading && selectedChat"
            class="messages-card-container"
          >
            <div class="messages-card">
              <div class="messages-card-header">
                <h3 class="messages-card-title">Сообщения</h3>
                <span class="messages-card-count">{{ messages.length }}</span>
              </div>
              <div class="messages-card-content">
                <div 
                  v-for="message in messages" 
                  :key="message.id"
                  class="message-card-item"
                >
                  <div class="message-card-header">
                    <span class="message-card-sender">{{ message.sender || 'Неизвестно' }}</span>
                    <span class="message-card-time">{{ message.timestamp ? new Date(message.timestamp).toLocaleTimeString() : '' }}</span>
                  </div>
                  <div class="message-card-body">
                    <p v-if="message.text" class="message-card-text">{{ message.text }}</p>
                    <div v-if="message.media_path" class="message-card-media">
                      <span>📎 Медиа</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- WhatsApp Title and Status (moving elements) -->
          <div 
            v-if="!selectedChat || (selectedChat && waStatus === 'connected')"
            class="split-content"
            :class="{ 'split-content-moved': waStatus === 'connected' }"
          >
            <h2 
              class="split-title"
              :class="{ 'split-title-moved': waStatus === 'connected' }"
            >
              WhatsApp
              <button 
                v-if="waStatus === 'connected'"
                @click="disconnectWhatsApp"
                class="wa-disconnect-btn"
                title="Выйти из WhatsApp"
              >
                Выйти
              </button>
            </h2>
            <p 
              class="split-description planet-status"
              :class="{ 
                'split-status-moved': waStatus === 'connected'
              }"
            >
              {{ displayStatusMessage }}
            </p>
          </div>
        </div>
        
        <!-- Search form for chats -->
        <div 
          v-if="waStatus === 'connected' && !selectedChat && !chatsLoading && chats.length > 0" 
          class="chat-search-container split-whatsapp-search"
          :class="{ 'chat-search-hiding': selectedChat }"
        >
          <input
            v-model="chatSearchQuery"
            type="text"
            placeholder="Поиск чата..."
            class="chat-search-input"
            @input="filterChatsBySearch"
          />
        </div>
        
        <!-- View chat button -->
        <div 
          v-if="selectedChat && waStatus === 'connected' && !chatsLoading"
          class="selected-chat-controls split-whatsapp-search"
          :class="{ 
            'selected-chat-controls-visible': selectedChat && !chatMovingToPlanet,
            'selected-chat-controls-hiding': chatMovingToPlanet
          }"
        >
          <button @click="proceedWithSelectedChat" class="btn-view-chat">
            Просмотр чата
          </button>
        </div>
        
        <!-- Chat circles orbiting around WhatsApp planet (inside split-whatsapp, after search) -->
        <div 
          v-for="(chat, index) in visibleChats" 
          :key="chat.id"
          class="chat-circle"
          :class="{ 
            'chat-visible': chat.visible, 
            'has-avatar': chat.avatar,
            'chat-selected': selectedChat?.id === chat.id,
            'chat-dimmed': selectedChat && selectedChat.id !== chat.id,
            'chat-moving-to-corner': chatMovingToCorner && selectedChat?.id === chat.id,
            'chat-moving-to-planet': chatMovingToPlanet && selectedChat?.id === chat.id,
            'chat-hiding': chatsHiding && selectedChat && selectedChat.id !== chat.id
          }"
          :style="getChatCircleStyle(index)"
          @click="selectChat(chat)"
          :title="chat.name"
        >
          <img v-if="chat.avatar" :src="chat.avatar" :alt="chat.name" class="chat-avatar" @error="onAvatarError($event, chat)" />
          <span v-else class="chat-initial">{{ getChatInitial(chat.name) }}</span>
        </div>
      </div>
      
      <div class="split-section split-telegram">
        <div class="planet-container planet-container-tg">
          <!-- Telegram Planet -->
          <div 
            class="planet planet-tg" 
            ref="planetTg" 
            :style="{ boxShadow: tgBoxShadow }" 
            :class="{ 
              'planet-tg-shrunk': telegramShrunk,
              'planet-tg-clickable': tgPhase === 'hidden' || tgPhase === 'connected'
            }"
            @click="onTelegramPlanetClick"
          >
            <!-- Lock icon if not connected -->
            <div v-if="tgPhase !== 'connected'" class="planet-lock">🔒</div>
            <img src="https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg" class="planet-logo" :class="{ 'logo-pulsing': tgLoading }" alt="Telegram Planet" />
            
            <!-- Telegram auth overlay -->
            <div 
              class="tg-overlay" 
              :class="{ 
                'overlay-visible': tgPhase !== 'hidden' && tgPhase !== 'connected',
                'overlay-in-planet': true
              }"
            >
              <!-- Not connected - show auth button -->
              <div v-if="tgPhase === 'hidden'" class="tg-connect-prompt">
                <p class="tg-connect-text">Нажмите, чтобы авторизоваться</p>
                <button @click.stop="startTelegramAuth" class="tg-connect-btn">
                  Авторизоваться
                </button>
              </div>
              
              <!-- Phone input -->
              <div v-else-if="tgPhase === 'phone'" class="tg-auth-form">
                <p class="tg-auth-title">Введите номер телефона</p>
                <input 
                  v-model="tgPhone" 
                  type="tel" 
                  placeholder="+7 999 123 45 67"
                  class="tg-input"
                  @keyup.enter="sendTelegramCode"
                />
                <button @click.stop="sendTelegramCode" class="tg-btn" :disabled="tgLoading || !tgPhone">
                  {{ tgLoading ? 'Отправка...' : 'Отправить код' }}
                </button>
              </div>
              
              <!-- Code input -->
              <div v-else-if="tgPhase === 'code'" class="tg-auth-form">
                <p class="tg-auth-title">Введите код из Telegram</p>
                <input 
                  v-model="tgCode" 
                  type="text" 
                  placeholder="12345"
                  class="tg-input"
                  @keyup.enter="verifyTelegramCode"
                />
                <button @click.stop="verifyTelegramCode" class="tg-btn" :disabled="tgLoading || !tgCode">
                  {{ tgLoading ? 'Проверка...' : 'Подтвердить' }}
                </button>
              </div>
              
              <!-- Password input -->
              <div v-else-if="tgPhase === 'password'" class="tg-auth-form">
                <p class="tg-auth-title">Введите пароль</p>
                <input 
                  v-model="tgPassword" 
                  type="password" 
                  placeholder="Пароль"
                  class="tg-input"
                  @keyup.enter="verifyTelegramPassword"
                />
                <button @click.stop="verifyTelegramPassword" class="tg-btn" :disabled="tgLoading || !tgPassword">
                  {{ tgLoading ? 'Проверка...' : 'Подтвердить' }}
                </button>
              </div>
              
              <!-- Connected state -->
              <div v-else-if="tgPhase === 'connected'" class="tg-connected">
                <span class="tg-success-icon">✓</span>
                <p class="tg-connected-text">Авторизовано!</p>
              </div>
            </div>
          </div>
          
          <!-- Telegram Title -->
          <div 
            v-if="!(tgPhase === 'connected' && !selectedTelegramChat && !telegramChatsLoading && telegramChats.length > 0)"
            class="split-content"
          >
            <h2 class="split-title">Telegram</h2>
            <p class="split-description planet-status">
              {{ telegramStatusMessage }}
            </p>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed, nextTick } from 'vue'
import api from '../api/client'
import { store } from '../store'
import { useRocketPhysics } from '../composables/useRocketPhysics'
import RocketShip from '../components/RocketShip.vue'
import StarsBackground from '../components/landing/StarsBackground.vue'
import { useMessages, type Message } from '../composables/useMessages'
import { PLANET_VISUAL } from '../constants/rocketConstants'
import { shadowForPlanet } from '../utils/rocketUtils'
import { ANIMATION, MESSAGES, POLLING } from '../constants/landingConstants'

// ----------------------------
// Constants
// ----------------------------

// UI Sizes
const UI_SIZES = {
  // WhatsApp chat circles
  CHAT_CIRCLE_SIZE: 52,
  RING_GAP: 20,
  // Telegram chat circles
  TG_CHAT_CIRCLE_SIZE: 52,
  TG_RING_GAP: 20,
  // Ship rendering
  SHIP_SCALE: 3.5,
  // Screen positioning
  TOP_PADDING: 24,
  CRUISE_ALTITUDE_MIN: 80,
  CRUISE_ALTITUDE_MAX: 220,
  CRUISE_ALTITUDE_RATIO: 0.22,
} as const

// Stars constants moved to constants/starsConstants.ts
// Messages constants moved to constants/landingConstants.ts

// ----------------------------
// DOM refs
// ----------------------------
const planetWa = ref<HTMLElement | null>(null)
const planetTg = ref<HTMLElement | null>(null)

// ----------------------------
// Migration animation state
// ----------------------------
const showWaOverlay = ref(false) // true when overlay content should be visible
const whatsappShrunk = ref(false) // true when WhatsApp planet shrinks after connection

// ----------------------------
// Rocket Physics (using composable)
// ----------------------------
const waBoxShadow = ref('')
const tgBoxShadow = ref('')

// ----------------------------
// WhatsApp connection state
// ----------------------------
const waStatus = ref<'idle' | 'loading' | 'qr' | 'connecting' | 'connected'>('idle')
const qrCode = ref<string | null>(null)
const waError = ref<string | null>(null)
const waSessionId = ref<string | null>(null)
const whatsappStatusMessageInternal = ref('Проверяю доступные сессии...')
let statusPollInterval: number | null = null

// Computed status message that shows loading progress if messages are loading
const displayStatusMessage = computed(() => {
  // Show error if there's an error loading chats
  if (waError.value && waStatus.value === 'connected') {
    return waError.value
  }
  // Show messages error if there's an error loading messages (priority over everything except chat errors)
  if (messagesError.value && selectedChat.value) {
    return messagesError.value
  }
  // Show messages loading progress if loading (priority over selected chat name)
  if (messagesLoading.value && messagesProgress.value.message) {
    return messagesProgress.value.message
  }
  // Show selected chat name if chat is selected
  if (selectedChat.value && waStatus.value === 'connected') {
    return `Выбран чат: ${selectedChat.value.name}`
  }
  return whatsappStatusMessageInternal.value
})

// Computed property to show rocket - always visible
const shouldShowRocket = computed(() => {
  // Rocket is always visible regardless of state
  return true
})

// ----------------------------
// Chats state
// ----------------------------
interface Chat {
  id: string
  name: string
  avatar: string | null
  visible: boolean
}
const chatsLoading = ref(false)
const chats = ref<Chat[]>([])
const visibleChats = ref<Chat[]>([])
const selectedChat = ref<Chat | null>(null)
const chatMovingToCorner = ref(false)
const chatMovingToPlanet = ref(false) // Chat moving to planet center
const chatsHiding = ref(false) // Other chats hiding
const chatSearchQuery = ref('')
const chatThetaOffset = ref(0) // θoffset - текущий угол (плавно интерполируется)
const targetChatThetaOffset = ref(0) // Целевой угол (устанавливается при скроллинге)

// Cache planet center position to keep orbits stable
const planetCenterCache = ref<{ x: number; y: number } | null>(null)

// Constants for polar coordinate system
const TAU = Math.PI * 2 // 2π

// Smooth scrolling animation state
let scrollAnimationFrameId: number | null = null
const SCROLL_SMOOTHING_FACTOR = 0.15 // Скорость интерполяции (0-1, чем больше - тем быстрее)

// Normalize angle to [0, 2π] range
function normalizeAngle(a: number): number {
  a = a % TAU
  if (a < 0) a += TAU
  return a
}

// Normalize angle difference for smooth interpolation across 0/2π boundary
function normalizeAngleDifference(current: number, target: number): number {
  let diff = target - current
  // Normalize to [-π, π] range for shortest path
  if (diff > Math.PI) diff -= TAU
  if (diff < -Math.PI) diff += TAU
  return diff
}

// Smooth scroll animation loop
function animateChatScroll() {
  const current = chatThetaOffset.value
  const target = targetChatThetaOffset.value
  
  // Calculate shortest angular difference
  const diff = normalizeAngleDifference(current, target)
  
  // If difference is very small, snap to target to avoid infinite micro-movements
  if (Math.abs(diff) < 0.001) {
    chatThetaOffset.value = normalizeAngle(target)
  } else {
    // Smooth interpolation using exponential easing
    chatThetaOffset.value = normalizeAngle(current + diff * SCROLL_SMOOTHING_FACTOR)
  }
  
  // Continue animation if there's still a difference
  if (Math.abs(normalizeAngleDifference(chatThetaOffset.value, target)) > 0.001) {
    scrollAnimationFrameId = requestAnimationFrame(animateChatScroll)
  } else {
    scrollAnimationFrameId = null
  }
}

// Start smooth scroll animation if not already running
function startScrollAnimation() {
  if (scrollAnimationFrameId === null) {
    scrollAnimationFrameId = requestAnimationFrame(animateChatScroll)
  }
}

// Messages visualization state (using composable)
let chatsEventSource: EventSource | null = null
let activeTimeouts: number[] = [] // Track all setTimeout calls for cleanup

// Chat scroll rotation handler - обновляет целевой угол для плавной анимации
function handleChatScroll(event: WheelEvent) {
  // Only rotate if chats are visible
  if (waStatus.value === 'connected' && !selectedChat.value && !chatsLoading.value && chats.value.length > 0) {
    // Prevent default scroll behavior
    event.preventDefault()
    
    // Обновляем целевой угол (не текущий - он будет плавно интерполироваться)
    // Negative deltaY means scrolling up (rotate counter-clockwise)
    // Positive deltaY means scrolling down (rotate clockwise)
    const k = 0.002 // Sensitivity coefficient
    targetChatThetaOffset.value += event.deltaY * k
    
    // Нормализация целевого угла для предотвращения накопления ошибок
    targetChatThetaOffset.value = normalizeAngle(targetChatThetaOffset.value)
    
    // Запускаем анимацию плавного скроллинга
    startScrollAnimation()
  }
}

// ----------------------------
// Migration state
// ----------------------------
const migrationInProgress = ref(false)
const migrationCompleted = ref(false)
const migrationStatus = ref('Подготовка к переносу...')
const migrationProgress = ref({ loaded: 0, total: 0 })
const migrationResult = ref<{
  total: number
  successful: number
  failed: number
  errors: string[]
} | null>(null)
const migrationLogs = ref<Array<{ level: string, message: string, timestamp: number }>>([])
let migrationEventSource: EventSource | null = null
let migrationStatusPollInterval: number | null = null

// Use messages composable
const messagesComposable = useMessages({
  sessionId: waSessionId,
  chatId: computed(() => selectedChat.value?.id || null),
  chatName: computed(() => selectedChat.value?.name || null),
  onLogsUpdate: () => {
    // Logs are no longer displayed
  },
  activeTimeouts
})

const { 
  messages, 
  messagesLoading,
  messagesProgress,
  messagesError,
  loadMessages, 
  closeMessages 
} = messagesComposable

// Initialize rocket physics after messagesLoading is defined
const rocket = useRocketPhysics({
  planetRefs: {
    wa: planetWa,
    tg: planetTg,
  },
  hideStage: ref(0), // Not used in new flow, but required by composable
  messagesLoading: messagesLoading, // Pass messages loading state
  onGravityUpdate: (gravityViz) => {
    waBoxShadow.value = shadowForPlanet('wa', gravityViz.wa, PLANET_VISUAL)
    tgBoxShadow.value = shadowForPlanet('tg', gravityViz.tg, PLANET_VISUAL)
  },
})

const { shipState, flightState, spawnShipAboveWhatsApp, launchMission, startPhysics, stopPhysics } = rocket

// Use constants from UI_SIZES
const CHAT_CIRCLE_SIZE = UI_SIZES.CHAT_CIRCLE_SIZE
const RING_GAP = UI_SIZES.RING_GAP

// ----------------------------
// Telegram connection state
// ----------------------------
const tgPhase = ref<'hidden' | 'entering' | 'phone' | 'code' | 'password' | 'connected'>('hidden')
const tgPhone = ref('')
const tgCode = ref('')
const tgPassword = ref('')
const tgPhoneCodeHash = ref<string | null>(null)
const tgSessionId = ref<string | null>(null)
const tgError = ref<string | null>(null)
const tgLoading = ref(false)
const tgUserInfo = ref<any>(null)
const whatsappInCorner = ref(false) // WhatsApp planet moved to corner
const telegramShrunk = ref(false) // Telegram planet shrunk after auth
const telegramStatusMessage = ref('Не авторизовано')

// ----------------------------
// Migration destination selection
// ----------------------------
const showDestinationSelection = ref(false)
const destinationType = ref<'saved' | 'existing' | 'new_group' | null>(null)
const telegramChats = ref<TelegramChat[]>([])
const visibleTelegramChats = ref<TelegramChat[]>([])
const telegramChatsLoading = ref(false)
const telegramChatsError = ref<string | null>(null)
const selectedTelegramChat = ref<TelegramChat | null>(null)
const newGroupName = ref('')

// Use constants from UI_SIZES
const TG_CHAT_CIRCLE_SIZE = UI_SIZES.TG_CHAT_CIRCLE_SIZE
const TG_RING_GAP = UI_SIZES.TG_RING_GAP

// Telegram chat interface
interface TelegramChat {
  id: string
  name: string
  visible: boolean
}


// Stars logic moved to components/landing/StarsBackground.vue and composables/useStars.ts

// startMigration removed - планеты теперь всегда видны, подключение по клику

// ----------------------------
// WhatsApp Connection Logic
// ----------------------------
// ----------------------------
// Rocket Launch Handler
// ----------------------------
function onPageClick(event: MouseEvent) {
  // Launch rocket on click only if rocket is visible and not already launched
  if (shouldShowRocket.value && !flightState.launched) {
    // Don't launch if clicking on buttons or chat circles (but allow clicks on planets)
    const target = event.target as HTMLElement
    if (target.closest('button') || target.closest('.chat-circle') || target.closest('.telegram-chat-circle')) {
      return
    }
    
    // Determine which section contains the click point
    // Use the click coordinates to find the section
    const clickX = event.clientX
    const clickY = event.clientY
    
    // Check if click is in WhatsApp section (left half of screen)
    const screenWidth = window.innerWidth
    const isInWhatsAppSection = clickX < screenWidth / 2
    
    // Also check by DOM element (for clicks on planets or other elements)
    const clickedElement = event.target as HTMLElement
    const whatsappSection = clickedElement.closest('.split-whatsapp')
    const telegramSection = clickedElement.closest('.split-telegram')
    
    // Determine target planet based on section
    let targetPlanet: 'wa' | 'tg' = 'tg' // default
    
    if (whatsappSection || isInWhatsAppSection) {
      targetPlanet = 'wa'
    } else if (telegramSection || !isInWhatsAppSection) {
      targetPlanet = 'tg'
    }
    
    // Launch to the planet in the clicked section
    launchMission(targetPlanet)
  }
}

// ----------------------------
// Planet Click Handlers
// ----------------------------
function onWhatsAppPlanetClick(event: MouseEvent) {
  // Stop event propagation to prevent onPageClick from firing
  event.stopPropagation()
  
  // If rocket is visible and not launched, launch rocket AND start connection simultaneously
  if (shouldShowRocket.value && !flightState.launched) {
    // Launch rocket to WhatsApp planet
    launchMission('wa')
    // Start WhatsApp connection at the same time
    if (waStatus.value === 'idle') {
      startWhatsAppAuth()
    }
    return
  }
  
  // Handle planet click for connection (when rocket is already launched or not visible)
  // Only allow click if not connected
  if (waStatus.value === 'idle') {
    startWhatsAppAuth()
  }
}

function onTelegramPlanetClick(event: MouseEvent) {
  // Stop event propagation to prevent onPageClick from firing
  event.stopPropagation()
  
  // If rocket is visible and not launched, launch rocket AND start connection simultaneously
  if (shouldShowRocket.value && !flightState.launched) {
    // Launch rocket to Telegram planet
    launchMission('tg')
    // Start Telegram connection at the same time
    if (tgPhase.value === 'hidden') {
      startTelegramAuth()
    }
    return
  }
  
  // Handle planet click for connection (when rocket is already launched or not visible)
  // Only allow click if not connected and not already in auth flow
  if (tgPhase.value === 'hidden') {
    startTelegramAuth()
  }
}

async function startWhatsAppAuth() {
  // Show overlay immediately
  showWaOverlay.value = true
  whatsappStatusMessageInternal.value = 'Подключение...'
  // Start connection process
  await startWhatsAppConnection()
}

function startTelegramAuth() {
  // Generate session ID for Telegram
  tgSessionId.value = `tg_${Date.now()}_${Math.random().toString(36).substring(7)}`
  telegramStatusMessage.value = 'Авторизация...'
  // Show phone input
  tgPhase.value = 'phone'
}

async function startWhatsAppConnection() {
  waStatus.value = 'loading'
  waError.value = null
  qrCode.value = null
  whatsappStatusMessageInternal.value = 'Пробуем подключиться к WhatsApp и получить QR-код для входа...'
  console.log('[WA] startWhatsAppConnection: init')
  
  try {
    // Try to reuse existing session first
    console.log('[WA] startWhatsAppConnection: fetching existing sessions')
    const sessionsResponse = await api.get('/whatsapp/sessions')
    const sessions = sessionsResponse.data.sessions || []
    console.log('[WA] startWhatsAppConnection: sessions response', sessions)
    
    if (sessions.length > 0) {
      const lastSessionId = sessions[sessions.length - 1]
      console.log('[WA] startWhatsAppConnection: trying to reuse session', lastSessionId)
      try {
        const reuseResponse = await api.post(`/whatsapp/sessions/${lastSessionId}/reuse`)
        console.log('[WA] startWhatsAppConnection: reuse response', reuseResponse.data)
        if (reuseResponse.data.reused && reuseResponse.data.status?.status === 'ready') {
          whatsappStatusMessageInternal.value = 'Сессия валидна! Подключаюсь к WhatsApp...'
          waSessionId.value = lastSessionId
          store.setWhatsAppSessionId(lastSessionId)
          waStatus.value = 'connected'
          showWaOverlay.value = false // Hide overlay immediately when connected
          whatsappStatusMessageInternal.value = 'Подключено! Загружаю чаты...'
          console.log('[WA] startWhatsAppConnection: session reused and ready, proceeding to chats')
          await onWhatsAppConnected()
          return
        }
        console.log('[WA] startWhatsAppConnection: session not ready, will start new connection')
        whatsappStatusMessageInternal.value = 'Сессия недействительна, создаю новую...'
      } catch (e) {
        // Session reuse failed, continue with new connection
        console.warn('[WA] startWhatsAppConnection: reuse failed, creating new session', e)
        whatsappStatusMessageInternal.value = 'Сессия недействительна, создаю новую...'
      }
    } else {
      whatsappStatusMessageInternal.value = 'Сессий не найдено, запрашиваю QR-код...'
      console.log('[WA] startWhatsAppConnection: no saved sessions found')
    }
    
    // Start new connection
    whatsappStatusMessageInternal.value = 'Подключаюсь к WhatsApp...'
    console.log('[WA] startWhatsAppConnection: calling /whatsapp/connect')
    const response = await api.post('/whatsapp/connect')
    console.log('[WA] startWhatsAppConnection: /whatsapp/connect response', response.data)
    waSessionId.value = response.data.session_id
    store.setWhatsAppSessionId(response.data.session_id)
    
    if (response.data.qr_code) {
      qrCode.value = response.data.qr_code
      waStatus.value = 'qr'
      whatsappStatusMessageInternal.value = 'Отсканируйте QR-код в приложении WhatsApp'
      console.log('[WA] startWhatsAppConnection: QR received, waiting for scan')
    } else if (response.data.status === 'ready') {
      waStatus.value = 'connected'
      showWaOverlay.value = false // Hide overlay immediately when connected
      whatsappStatusMessageInternal.value = 'Подключено! Загружаю чаты...'
      console.log('[WA] startWhatsAppConnection: connection ready without QR, proceeding to chats')
      await onWhatsAppConnected()
    } else {
      whatsappStatusMessageInternal.value = 'Ожидаю подключения...'
      console.log('[WA] startWhatsAppConnection: non-final status from /connect', response.data.status)
    }
    
    // Start polling for status updates
    startStatusPolling()
    
  } catch (err: unknown) {
    console.error('[WA] startWhatsAppConnection: error', err)
    const error = err as { response?: { data?: { detail?: string } } }
    waError.value = error.response?.data?.detail || 'Ошибка подключения к WhatsApp'
    waStatus.value = 'idle'
    whatsappStatusMessageInternal.value = 'Ошибка подключения. Попробуйте обновить страницу.'
  }
}

function startStatusPolling() {
  if (statusPollInterval) {
    clearInterval(statusPollInterval)
  }
  
  statusPollInterval = window.setInterval(async () => {
    if (!waSessionId.value) return
    
    try {
      console.log('[WA] startStatusPolling: polling status for session', waSessionId.value)
      const response = await api.get(`/whatsapp/status/${waSessionId.value}`)
      const status = response.data.status
      console.log('[WA] startStatusPolling: status response', response.data)

      if (status === 'ready') {
        waStatus.value = 'connected'
        showWaOverlay.value = false // Hide overlay immediately when connected
        whatsappStatusMessageInternal.value = 'Подключено! Загружаю чаты...'
        console.log('[WA] startStatusPolling: status ready, proceeding to chats')
        stopStatusPolling()
        // Show connected message, then shrink planet
        await onWhatsAppConnected()
      } else if (status === 'qr' && response.data.qr_code) {
        qrCode.value = response.data.qr_code
        waStatus.value = 'qr'
        whatsappStatusMessageInternal.value = 'Отсканируйте QR-код в приложении WhatsApp'
      } else if (status === 'connecting') {
        waStatus.value = 'connecting'
        whatsappStatusMessageInternal.value = 'Подключение в процессе...'
      } else if (status === 'waiting_qr') {
        whatsappStatusMessageInternal.value = 'Ожидаю QR-код...'
      } else if (status === 'failed') {
        waError.value = response.data.error || 'Подключение не удалось'
        whatsappStatusMessageInternal.value = 'Ошибка подключения'
        console.warn('[WA] startStatusPolling: status failed', response.data.error)
        stopStatusPolling()
      }
    } catch (err) {
      // Ignore polling errors
      console.warn('[WA] startStatusPolling: polling error', err)
    }
  }, POLLING.STATUS_POLL_INTERVAL)
}

function stopStatusPolling() {
  if (statusPollInterval) {
    clearInterval(statusPollInterval)
    statusPollInterval = null
  }
}

async function retryConnection() {
  waError.value = null
  await startWhatsAppConnection()
}

async function disconnectWhatsApp() {
  if (!waSessionId.value) {
    // Already disconnected, just reset state
    resetWhatsAppState()
    return
  }

  try {
    whatsappStatusMessageInternal.value = 'Отключение...'
    console.log('[WA] disconnectWhatsApp: disconnecting session', waSessionId.value)
    
    // Call backend API to disconnect
    await api.post(`/whatsapp/${waSessionId.value}/disconnect`)
    console.log('[WA] disconnectWhatsApp: disconnect successful')
    
    // Reset all state
    resetWhatsAppState()
    
    whatsappStatusMessageInternal.value = 'Отключено'
  } catch (err: unknown) {
    console.error('[WA] disconnectWhatsApp: error', err)
    const error = err as { response?: { data?: { detail?: string } } }
    const errorMessage = error.response?.data?.detail || 'Ошибка отключения'
    
    // Even if API call fails, reset local state
    resetWhatsAppState()
    whatsappStatusMessageInternal.value = errorMessage
  }
}

function resetWhatsAppState() {
  // Stop polling
  stopStatusPolling()
  
  // Close EventSource connections
  if (chatsEventSource) {
    chatsEventSource.close()
    chatsEventSource = null
  }
  closeMessages()
  
  // Reset state
  waStatus.value = 'idle'
  waSessionId.value = null
  qrCode.value = null
  waError.value = null
  showWaOverlay.value = false
  whatsappShrunk.value = false
  chatsLoading.value = false
  chats.value = []
  visibleChats.value = []
  selectedChat.value = null
  chatSearchQuery.value = ''
  
  // Reset scroll angles
  chatThetaOffset.value = 0
  targetChatThetaOffset.value = 0
  
  // Clear store
  store.setWhatsAppSessionId(null)
  store.whatsappSessionActive = false
  
  console.log('[WA] resetWhatsAppState: state reset complete')
}

async function onWhatsAppConnected() {
  // If we were showing QR, wait for planet to collapse back to normal size
  if (qrCode.value) {
    // Wait for collapse animation (0.6s)
    await new Promise(resolve => setTimeout(resolve, 600))
    // Clear QR code after animation
    qrCode.value = null
  }
  
  // Wait to show the "Connected" message
  await new Promise(resolve => setTimeout(resolve, ANIMATION.CONNECTED_MESSAGE_DELAY))
  
  // Hide overlay content
  showWaOverlay.value = false
  
  // Wait for overlay to fade out
  await new Promise(resolve => setTimeout(resolve, ANIMATION.OVERLAY_FADE_DELAY))
  
  // Start loading chats (planet will shrink at the start of loadChats)
  await loadChats()
}

async function loadChats() {
  chatsLoading.value = true
  chats.value = []
  visibleChats.value = []
  chatSearchQuery.value = '' // Reset search
  planetCenterCache.value = null // Reset planet center cache
  
  // Reset scroll angles when loading new chats
  chatThetaOffset.value = 0
  targetChatThetaOffset.value = 0
  
  whatsappStatusMessageInternal.value = 'Подгружаем чаты...'
  console.log('[WA] loadChats: start, session', waSessionId.value)
  
  // Wait for shrink animation to complete before starting to load chats
  await new Promise(resolve => setTimeout(resolve, ANIMATION.PLANET_SHRINK_DELAY))
  
  // Track loaded chat IDs to avoid duplicates
  const loadedChatIds = new Set<string>()
  
  try {
    // Close previous event source if exists
    if (chatsEventSource) {
      chatsEventSource.close()
      chatsEventSource = null
    }
    
    // Use SSE to stream chats as they are loaded
    const eventSource = new EventSource(`/api/whatsapp/chats/${waSessionId.value}/stream`)
    chatsEventSource = eventSource
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        if (data.type === 'start') {
          // Loading started
          whatsappStatusMessageInternal.value = 'Загружаю список чатов...'
          console.log('[WA] loadChats: streaming started')
        } else if (data.type === 'chats' && data.chats) {
          // New batch of chats received
          const newChats = data.chats
            .map((chat: { id?: string, name: string, avatar?: string | null }) => {
              const chatId = chat.id || `chat_${chat.name}`
              console.log('[WA] loadChats: processing chat', { id: chatId, name: chat.name, originalId: chat.id })
              return {
                id: chatId,
                name: chat.name,
                avatar: chat.avatar || null,
                visible: false
              }
            })
            .filter((chat: Chat) => {
              // Filter out duplicates
              if (loadedChatIds.has(chat.id)) {
                return false
              }
              loadedChatIds.add(chat.id)
              return true
            })
          
          if (newChats.length > 0) {
            // Add new chats to the list
            const wasEmpty = chats.value.length === 0
            chats.value.push(...newChats)

            // First successful batch = считаем, что есть доступ к чатам
            if (wasEmpty) {
              console.log('[WA] loadChats: first chats batch received, access to chats confirmed')
              whatsappStatusMessageInternal.value = 'Доступ к чатам получен, продолжаю загрузку...'
            } else {
              // Update status message with count
              whatsappStatusMessageInternal.value = `Загружено чатов: ${chats.value.length}...`
            }
            
            // Show them immediately with small animation delay
            newChats.forEach((chat: Chat, index: number) => {
              const timeoutId = window.setTimeout(() => {
                const visibleChat = { ...chat, visible: true }
                visibleChats.value.push(visibleChat)
                
                // Cache planet center position when first chat appears
                // Use static calculation instead of getBoundingClientRect to avoid animation issues
                if (visibleChats.value.length === 1 && !planetCenterCache.value) {
                  // Planet is in left half of screen (split-whatsapp section)
                  // Section is centered vertically and horizontally in its half
                  planetCenterCache.value = {
                    x: window.innerWidth / 4, // Left half center (25% of screen width)
                    y: window.innerHeight / 2 // Vertical center (50% of screen height)
                  }
                }
              }, index * ANIMATION.CHAT_APPEAR_DELAY)
              activeTimeouts.push(timeoutId)
            })
          }
        } else if (data.type === 'complete') {
          // All chats loaded
          chatsLoading.value = false
          whatsappStatusMessageInternal.value = `Готово! Загружено ${chats.value.length} чатов`
          eventSource.close()
          chatsEventSource = null
        } else if (data.type === 'error') {
          // Error occurred
          chatsLoading.value = false
          waError.value = data.error || 'Ошибка загрузки чатов'
          whatsappStatusMessageInternal.value = 'Ошибка загрузки чатов'
          eventSource.close()
          chatsEventSource = null
        }
      } catch (err) {
        console.error('Error parsing SSE data:', err)
      }
    }
    
    eventSource.onerror = (err) => {
      console.error('SSE error:', err)
      chatsLoading.value = false
      waError.value = 'Ошибка подключения к серверу'
      whatsappStatusMessageInternal.value = 'Ошибка подключения к серверу'
      eventSource.close()
      chatsEventSource = null
    }
    
  } catch (err: unknown) {
    chatsLoading.value = false
    const errorMessage = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Ошибка загрузки чатов'
    waError.value = errorMessage
    whatsappStatusMessageInternal.value = 'Ошибка загрузки чатов'
  }
}

// Removed unused function animateChatsAppearing - chats are now animated inline in loadChats

function getChatCircleStyle(index: number) {
  // Calculate which ring and position within that ring
  let ringIndex = 0
  let positionInRing = index
  let chatsInCurrentRing = getChatsPerRing(0)
  
  while (positionInRing >= chatsInCurrentRing) {
    positionInRing -= chatsInCurrentRing
    ringIndex++
    chatsInCurrentRing = getChatsPerRing(ringIndex)
  }
  
  // Calculate base angle for this element (θbase = i * stepAngle)
  // i - логический индекс элемента в кольце
  const totalInRing = getChatsPerRing(ringIndex)
  const stepAngle = TAU / totalInRing // Шаг угла для элементов в кольце
  const thetaBase = -Math.PI / 2 + positionInRing * stepAngle // Start from top (-90°)
  
  // Формула позиционирования: θ = θbase + θoffset
  const theta = thetaBase + chatThetaOffset.value
  
  // Calculate radius for this ring (FIXED - should not change during scroll)
  // Always use reduced planet size (78px) for chat positioning when chats are displayed
  const planetSize = 78 // Always use reduced size for chat orbit calculation
  const baseRadius = planetSize / 2 + RING_GAP + CHAT_CIRCLE_SIZE / 2
  const r = baseRadius + ringIndex * (CHAT_CIRCLE_SIZE + RING_GAP) // r - радиус орбиты (СТРОГО ФИКСИРОВАН)
  
  // Use cached planet center (set when first chat appears, static calculation)
  // CRITICAL: Center must NEVER change during scroll - only angle changes, not center or radius
  const cx = planetCenterCache.value?.x ?? (window.innerWidth / 4)
  const cy = planetCenterCache.value?.y ?? (window.innerHeight / 2)
  
  // Формула позиционирования в полярных координатах:
  // x = cx + r * cos(θ)
  // y = cy + r * sin(θ)
  // ВАЖНО: cx, cy, r - константы, меняется только θ
  const cosTheta = Math.cos(theta)
  const sinTheta = Math.sin(theta)
  const x = cx + r * cosTheta - CHAT_CIRCLE_SIZE / 2
  const y = cy + r * sinTheta - CHAT_CIRCLE_SIZE / 2
  
  return {
    left: `${x}px`,
    top: `${y}px`,
    width: `${CHAT_CIRCLE_SIZE}px`,
    height: `${CHAT_CIRCLE_SIZE}px`
  }
}

function getChatsPerRing(ringIndex: number): number {
  // First ring: calculate based on circumference
  // Each subsequent ring is larger and fits more chats
  // Always use reduced planet size (78px) for chat positioning when chats are displayed
  const planetSize = 78 // Always use reduced size for chat orbit calculation
  const baseRadius = planetSize / 2 + RING_GAP + CHAT_CIRCLE_SIZE / 2
  const ringRadius = baseRadius + ringIndex * (CHAT_CIRCLE_SIZE + RING_GAP)
  const circumference = 2 * Math.PI * ringRadius
  
  // How many circles fit with some spacing
  return Math.floor(circumference / (CHAT_CIRCLE_SIZE + 8))
}

function getChatInitial(name: string): string {
  if (!name) return '?'
  return name.charAt(0).toUpperCase()
}

// Transliteration map: Russian -> Latin
const transliterationMap: Record<string, string> = {
  'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
  'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
  'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
  'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
  'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
  'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
  'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
  'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
  'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch',
  'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
}

// Reverse transliteration map: Latin -> Russian (common patterns)
const reverseTransliterationMap: Record<string, string> = {
  'a': 'а', 'b': 'б', 'v': 'в', 'g': 'г', 'd': 'д', 'e': 'е', 'yo': 'ё',
  'zh': 'ж', 'z': 'з', 'i': 'и', 'y': 'й', 'k': 'к', 'l': 'л', 'm': 'м',
  'n': 'н', 'o': 'о', 'p': 'п', 'r': 'р', 's': 'с', 't': 'т', 'u': 'у',
  'f': 'ф', 'h': 'х', 'ts': 'ц', 'ch': 'ч', 'sh': 'ш', 'sch': 'щ',
  'yu': 'ю', 'ya': 'я'
}

// Transliterate Russian to Latin
function transliterateToLatin(text: string): string {
  let result = ''
  let i = 0
  
  while (i < text.length) {
    const char = text[i]
    const lowerChar = char.toLowerCase()
    
    // Check if current character has a transliteration
    if (transliterationMap[char]) {
      result += transliterationMap[char]
    } else if (transliterationMap[lowerChar]) {
      result += transliterationMap[lowerChar]
    } else {
      result += char
    }
    i++
  }
  
  return result
}

// Transliterate Latin to Russian (approximate)
function transliterateToRussian(text: string): string {
  let result = text.toLowerCase()
  
  // Replace multi-character sequences first (longer sequences first)
  // Sort by length descending to match longer sequences first
  const multiCharEntries = Object.entries(reverseTransliterationMap)
    .filter(([lat]) => lat.length > 1)
    .sort(([a], [b]) => b.length - a.length)
  
  for (const [lat, rus] of multiCharEntries) {
    const regex = new RegExp(lat, 'gi')
    result = result.replace(regex, rus)
  }
  
  // Replace single characters
  for (const [lat, rus] of Object.entries(reverseTransliterationMap)) {
    if (lat.length === 1) {
      const regex = new RegExp(lat, 'gi')
      result = result.replace(regex, rus)
    }
  }
  
  return result
}

// Get all search variants (original + transliterations)
function getSearchVariants(text: string): string[] {
  const variants = [text]
  
  // Check if text contains Cyrillic
  const hasCyrillic = /[а-яёА-ЯЁ]/.test(text)
  // Check if text contains Latin
  const hasLatin = /[a-zA-Z]/.test(text)
  
  if (hasCyrillic) {
    // If input is Russian, add Latin transliteration
    variants.push(transliterateToLatin(text))
  }
  
  if (hasLatin) {
    // If input is Latin, add Russian transliteration
    variants.push(transliterateToRussian(text))
  }
  
  return variants
}

// Normalize string for search (lowercase, remove extra spaces)
function normalizeString(str: string): string {
  return str.toLowerCase().trim().replace(/\s+/g, ' ')
}

// Check if any of the search variants match the chat name
function matchesAnyVariant(chatName: string, queryVariants: string[]): boolean {
  const normalizedChat = normalizeString(chatName)
  const chatVariants = getSearchVariants(chatName)
  
  for (const queryVariant of queryVariants) {
    const normalizedQuery = normalizeString(queryVariant)
    
    // Check against original chat name
    if (normalizedChat.includes(normalizedQuery)) {
      return true
    }
    
    // Check against all chat name variants
    for (const chatVariant of chatVariants) {
      const normalizedChatVariant = normalizeString(chatVariant)
      if (normalizedChatVariant.includes(normalizedQuery)) {
        return true
      }
    }
  }
  
  return false
}

// Simple similarity check - checks if query matches chat name with some tolerance for typos
function isChatMatch(chatName: string, query: string): boolean {
  if (!query.trim()) return true
  
  // Get all search variants (original + transliterations)
  const queryVariants = getSearchVariants(query)
  
  // First check exact matches with transliteration
  if (matchesAnyVariant(chatName, queryVariants)) {
    return true
  }
  
  const normalizedChat = normalizeString(chatName)
  const chatVariants = getSearchVariants(chatName)
  
  // Check if all query words are present in chat name (order doesn't matter)
  for (const queryVariant of queryVariants) {
    const normalizedQuery = normalizeString(queryVariant)
    const queryWords = normalizedQuery.split(/\s+/).filter(w => w.length > 0)
    if (queryWords.length === 0) continue
    
    // Check against original chat name
    const allWordsMatchOriginal = queryWords.every(word => {
      if (normalizedChat.includes(word)) return true
      return normalizedChat.split(/\s+/).some(chatWord => 
        chatWord.startsWith(word.substring(0, Math.max(1, word.length - 1))) ||
        word.startsWith(chatWord.substring(0, Math.max(1, chatWord.length - 1)))
      )
    })
    
    if (allWordsMatchOriginal) return true
    
    // Check against chat name variants
    for (const chatVariant of chatVariants) {
      const normalizedChatVariant = normalizeString(chatVariant)
      const allWordsMatchVariant = queryWords.every(word => {
        if (normalizedChatVariant.includes(word)) return true
        return normalizedChatVariant.split(/\s+/).some(chatWord => 
          chatWord.startsWith(word.substring(0, Math.max(1, word.length - 1))) ||
          word.startsWith(chatWord.substring(0, Math.max(1, chatWord.length - 1)))
        )
      })
      
      if (allWordsMatchVariant) return true
    }
  }
  
  // Check character similarity (simple fuzzy match) with transliteration
  for (const queryVariant of queryVariants) {
    const normalizedQuery = normalizeString(queryVariant)
    const queryChars = normalizedQuery.split('').filter(c => c !== ' ')
    
    for (const chatVariant of chatVariants) {
      const normalizedChatVariant = normalizeString(chatVariant)
      const chatChars = normalizedChatVariant.split('').filter(c => c !== ' ')
      
      let matchedChars = 0
      let queryIndex = 0
      let chatIndex = 0
      
      while (queryIndex < queryChars.length && chatIndex < chatChars.length) {
        if (queryChars[queryIndex] === chatChars[chatIndex]) {
          matchedChars++
          queryIndex++
        }
        chatIndex++
      }
      
      // If at least threshold% of query characters match, consider it a match
      if (queryChars.length > 0) {
        const matchRatio = matchedChars / queryChars.length
        if (matchRatio >= MESSAGES.FUZZY_MATCH_THRESHOLD) return true
      }
    }
  }
  
  return false
}

function filterChatsBySearch() {
  const query = chatSearchQuery.value
  
  if (!query.trim()) {
    // Show all chats if search is empty
    visibleChats.value = chats.value.map((chat: Chat) => ({ ...chat, visible: true }))
    return
  }
  
  // Filter chats based on search query
  const filtered = chats.value.filter((chat: Chat) => isChatMatch(chat.name, query))
  visibleChats.value = filtered.map((chat: Chat) => ({ ...chat, visible: true }))
}

function selectChat(chat: Chat) {
  // Toggle selection - click again to deselect
  if (selectedChat.value?.id === chat.id) {
    selectedChat.value = null
  } else {
    selectedChat.value = chat
    console.log('Chat selected:', { id: chat.id, name: chat.name })
  }
}

async function proceedWithSelectedChat() {
  if (!selectedChat.value) return
  
  // Store selected chat for migration
  store.setSelectedWhatsAppChats([selectedChat.value.id])
  
  // Start animations
  chatsHiding.value = true // Hide other chats
  chatMovingToPlanet.value = true // Move selected chat to planet center
  
  // Wait for animations
  await new Promise(resolve => setTimeout(resolve, ANIMATION.CORNER_ANIMATION_DELAY))
  
  // Hide other chat circles (keep selected chat visible)
  if (selectedChat.value) {
    visibleChats.value = visibleChats.value.filter((chat: Chat) => chat.id === selectedChat.value?.id)
  }
  
  // Load and show messages
  await loadAndShowMessages()
  
  // Don't auto-proceed - wait for user to click "Continue" button
}

async function goBackToChatSelection() {
  // Close messages event source and reset state
  closeMessages()
  
  // Reset selected chat
  selectedChat.value = null
  chatMovingToCorner.value = false
  chatMovingToPlanet.value = false
  chatsHiding.value = false
  
  // Return WhatsApp planet from corner to center (shrunk state)
  whatsappInCorner.value = false
  
  // Wait for animation
  await new Promise(resolve => setTimeout(resolve, ANIMATION.CORNER_ANIMATION_DELAY))
  
  // Restore WhatsApp chats visibility
  visibleChats.value = chats.value.map((chat: Chat) => ({ ...chat, visible: true }))
}


async function loadAndShowMessages() {
  if (!selectedChat.value || !waSessionId.value) return
  
  // Load messages via composable
  await loadMessages()
}

async function goBackToWhatsAppChats() {
  // Hide Telegram planet and reset Telegram state
  telegramShrunk.value = false
  tgPhase.value = 'hidden'
  tgPhone.value = ''
  tgCode.value = ''
  tgPassword.value = ''
  tgPhoneCodeHash.value = null
  tgError.value = null
  tgLoading.value = false
  
  // Hide destination selection panel
  showDestinationSelection.value = false
  destinationType.value = null
  selectedTelegramChat.value = null
  telegramChats.value = []
  visibleTelegramChats.value = []
  newGroupName.value = ''
  
  // Reset chat moving state
  chatMovingToCorner.value = false
  
  // Wait for Telegram planet to hide
  await new Promise(resolve => setTimeout(resolve, 500))
  
  // Return WhatsApp planet from corner to center (shrunk state)
  whatsappInCorner.value = false
  
  // Wait for animation
  await new Promise(resolve => setTimeout(resolve, ANIMATION.CORNER_ANIMATION_DELAY))
  
  // Restore WhatsApp chats visibility
  visibleChats.value = chats.value.map((chat: Chat) => ({ ...chat, visible: true }))
  
  // Reset selected chat
  selectedChat.value = null
}

async function sendTelegramCode() {
  if (!tgPhone.value || !tgSessionId.value) return
  
  tgLoading.value = true
  tgError.value = null
  
  try {
    const response = await api.post('/auth/telegram-phone-auth', {
      session_id: tgSessionId.value,
      phone: tgPhone.value
    })
    
    tgPhoneCodeHash.value = response.data.phone_code_hash
    tgPhase.value = 'code'
  } catch (err: unknown) {
    const error = err as { response?: { data?: { detail?: string } } }
    tgError.value = error.response?.data?.detail || 'Ошибка отправки кода'
  } finally {
    tgLoading.value = false
  }
}

async function verifyTelegramCode() {
  if (!tgCode.value || !tgSessionId.value || !tgPhoneCodeHash.value) return
  
  tgLoading.value = true
  tgError.value = null
  telegramStatusMessage.value = 'Проверка кода...'
  
  try {
    const response = await api.post('/auth/telegram-verify-code', {
      session_id: tgSessionId.value,
      phone: tgPhone.value,
      code: tgCode.value,
      phone_code_hash: tgPhoneCodeHash.value
    })
    
    tgUserInfo.value = response.data.user_info
    store.setTelegramUserId(response.data.user_id)
    
    // Show success message
    tgPhase.value = 'connected'
    telegramStatusMessage.value = 'Авторизовано'
    
    // Wait to show success
    await new Promise(resolve => setTimeout(resolve, ANIMATION.CONNECTED_MESSAGE_DELAY))
    
    // Load Telegram chats
    await onTelegramConnected()
    
  } catch (err: unknown) {
    const error = err as { response?: { data?: { detail?: string } } }
    const errorDetail = error.response?.data?.detail || ''
    if (errorDetail.includes('2FA') || errorDetail.includes('password')) {
      // Switch to password input
      tgPhase.value = 'password'
      tgError.value = 'Требуется пароль 2FA'
      telegramStatusMessage.value = 'Требуется пароль 2FA'
    } else {
      tgError.value = errorDetail || 'Неверный код'
      telegramStatusMessage.value = 'Ошибка авторизации'
    }
  } finally {
    tgLoading.value = false
  }
}

async function verifyTelegramPassword() {
  if (!tgPassword.value || !tgSessionId.value || !tgPhoneCodeHash.value) return
  
  tgLoading.value = true
  tgError.value = null
  telegramStatusMessage.value = 'Проверка пароля...'
  
  try {
    const response = await api.post('/auth/telegram-verify-code', {
      session_id: tgSessionId.value,
      phone: tgPhone.value,
      code: tgCode.value,
      phone_code_hash: tgPhoneCodeHash.value,
      password: tgPassword.value
    })
    
    tgUserInfo.value = response.data.user_info
    store.setTelegramUserId(response.data.user_id)
    
    // Show success message
    tgPhase.value = 'connected'
    telegramStatusMessage.value = 'Авторизовано'
    
    // Wait to show success
    await new Promise(resolve => setTimeout(resolve, ANIMATION.CONNECTED_MESSAGE_DELAY))
    
    // Load Telegram chats
    await onTelegramConnected()
    
  } catch (err: unknown) {
    const error = err as { response?: { data?: { detail?: string } } }
    tgError.value = error.response?.data?.detail || 'Неверный пароль'
    telegramStatusMessage.value = 'Ошибка авторизации'
  } finally {
    tgLoading.value = false
  }
}

async function onTelegramConnected() {
  // Auto-load Telegram chats list
  await loadTelegramChats()
  
  // Update status message with chat count
  if (telegramChats.value.length > 0) {
    telegramStatusMessage.value = `Авторизовано (${telegramChats.value.length} чатов)`
  }
}

async function loadTelegramChats() {
  if (!tgUserInfo.value?.id) {
    console.error('Cannot load Telegram chats: user_id is missing', tgUserInfo.value)
    telegramChatsError.value = 'Ошибка: не найден ID пользователя Telegram'
    telegramStatusMessage.value = 'Ошибка загрузки чатов'
    return
  }
  
  telegramChatsLoading.value = true
  telegramChats.value = []
  visibleTelegramChats.value = []
  telegramChatsError.value = null
  telegramStatusMessage.value = 'Загрузка чатов...'
  
  try {
    console.log('Loading Telegram chats for user_id:', tgUserInfo.value.id)
    const response = await api.post('/telegram/contacts', {
      user_id: tgUserInfo.value.id
    })
    
    console.log('Telegram chats response:', response.data)
    const chatList = response.data.contacts || []
    
    // Prepare chats with visibility flag
    telegramChats.value = chatList.map((chat: { id?: string | number, name: string }) => ({
      id: String(chat.id || chat.name),
      name: chat.name,
      visible: false
    }))
    
    if (telegramChats.value.length === 0) {
      console.warn('No Telegram chats found')
    } else {
      console.log(`Loaded ${telegramChats.value.length} Telegram chats`)
      // Animate chats appearing one by one
      await animateTelegramChatsAppearing()
    }
  } catch (err: any) {
    console.error('Error loading Telegram chats:', err)
    const errorMessage = err.response?.data?.detail || err.message || 'Ошибка загрузки чатов'
    telegramChatsError.value = errorMessage
  } finally {
    telegramChatsLoading.value = false
  }
}

async function animateTelegramChatsAppearing() {
  visibleTelegramChats.value = []
  for (let i = 0; i < telegramChats.value.length; i++) {
    const chat = { ...telegramChats.value[i], visible: true }
    visibleTelegramChats.value.push(chat)
    
    // Delay between each chat appearing (faster for more chats)
    const delay = Math.max(
      ANIMATION.CHAT_ANIMATION_MIN_DELAY, 
      ANIMATION.CHAT_ANIMATION_BASE_DELAY - telegramChats.value.length * ANIMATION.CHAT_ANIMATION_DELAY_FACTOR
    )
    await new Promise(resolve => setTimeout(resolve, delay))
  }
}

function getTelegramChatCircleStyle(index: number) {
  // Calculate which ring and position within that ring
  let ringIndex = 0
  let positionInRing = index
  let chatsInCurrentRing = getTelegramChatsPerRing(0)
  
  while (positionInRing >= chatsInCurrentRing) {
    positionInRing -= chatsInCurrentRing
    ringIndex++
    chatsInCurrentRing = getTelegramChatsPerRing(ringIndex)
  }
  
  // Calculate angle (clockwise from top)
  const totalInRing = getTelegramChatsPerRing(ringIndex)
  const angleStep = (2 * Math.PI) / totalInRing
  const angle = -Math.PI / 2 + positionInRing * angleStep // Start from top (-90°)
  
  // Calculate radius for this ring
  const planetSize = 280 // Telegram planet size
  const baseRadius = planetSize / 2 + TG_RING_GAP + TG_CHAT_CIRCLE_SIZE / 2
  const ringRadius = baseRadius + ringIndex * (TG_CHAT_CIRCLE_SIZE + TG_RING_GAP)
  
  // Calculate position relative to Telegram planet (right half of screen, centered)
  const centerX = (window.innerWidth / 4) * 3 // Right half center
  const centerY = window.innerHeight / 2 // Vertical center
  
  const x = centerX + Math.cos(angle) * ringRadius - TG_CHAT_CIRCLE_SIZE / 2
  const y = centerY + Math.sin(angle) * ringRadius - TG_CHAT_CIRCLE_SIZE / 2
  
  return {
    left: `${x}px`,
    top: `${y}px`,
    width: `${TG_CHAT_CIRCLE_SIZE}px`,
    height: `${TG_CHAT_CIRCLE_SIZE}px`
  }
}

function getTelegramChatsPerRing(ringIndex: number): number {
  // First ring: calculate based on circumference
  // Each subsequent ring is larger and fits more chats
  const planetSize = 280 // Telegram planet size
  const baseRadius = planetSize / 2 + TG_RING_GAP + TG_CHAT_CIRCLE_SIZE / 2
  const ringRadius = baseRadius + ringIndex * (TG_CHAT_CIRCLE_SIZE + TG_RING_GAP)
  const circumference = 2 * Math.PI * ringRadius
  
  // How many circles fit with some spacing
  return Math.floor(circumference / (TG_CHAT_CIRCLE_SIZE + 8))
}

function selectTelegramChat(chat: TelegramChat) {
  // Toggle selection - click again to deselect
  if (selectedTelegramChat.value?.id === chat.id) {
    selectedTelegramChat.value = null
  } else {
    selectedTelegramChat.value = chat
  }
}

// Message formatting functions moved to utils/messageUtils.ts

const canStartMigration = computed(() => {
  // Can start if Telegram chat is selected AND at least one message is selected
  const hasSelectedMessages = messages.value.some((msg: Message) => msg.selected)
  return selectedTelegramChat.value !== null && hasSelectedMessages && !migrationInProgress.value
})

async function startDataMigration() {
  if (!canStartMigration.value || !selectedChat.value || !selectedTelegramChat.value) return
  
  // Get selected message IDs
  const selectedMessageIds = messages.value
    .filter((msg: Message) => msg.selected)
    .map((msg: Message) => msg.id)
  
  if (selectedMessageIds.length === 0) {
    console.warn('No messages selected for migration')
    return
  }
  
  migrationInProgress.value = true
  migrationStatus.value = 'Начинаю перенос...'
  migrationProgress.value = { loaded: 0, total: selectedMessageIds.length }
  migrationLogs.value = []
  
  // Hide destination selection and messages
  showDestinationSelection.value = false
  
  // Add initial log
  addMigrationLog('info', `Начинаю перенос ${selectedMessageIds.length} сообщений...`)
  
  try {
    // Use WhatsApp session ID for migration
    const migrationSessionId = waSessionId.value || `migration_${Date.now()}`
    
    const response = await api.post('/migrate/start', {
      session_id: migrationSessionId,
      user_id: tgUserInfo.value?.id,
      target_chat_id: parseInt(selectedTelegramChat.value.id),
      whatsapp_chat_id: selectedChat.value.id
      // Note: Backend will migrate all messages from the chat
      // Selected message IDs filtering can be added later if needed
    })
    
    console.log('Migration started:', response.data)
    addMigrationLog('info', 'Миграция запущена, отслеживаю прогресс...')
    
    // Start polling migration status
    startMigrationStatusPolling(migrationSessionId)
    
  } catch (err: unknown) {
    console.error('Error starting migration:', err)
    migrationInProgress.value = false
    migrationStatus.value = 'Ошибка запуска переноса'
    const error = err as { response?: { data?: { detail?: string } } }
    addMigrationLog('error', error.response?.data?.detail || 'Не удалось запустить перенос')
  }
}

function startMigrationStatusPolling(sessionId: string) {
  // Poll migration status every 1 second
  migrationStatusPollInterval = window.setInterval(async () => {
    try {
      const response = await api.get(`/migrate/status/${sessionId}`)
      const status = response.data
      
      migrationProgress.value = {
        loaded: status.processed || 0,
        total: status.total || 0
      }
      
      if (status.current_action) {
        migrationStatus.value = status.current_action
        // Only add log if action changed (to avoid spam)
        const lastLog = migrationLogs.value[migrationLogs.value.length - 1]
        if (!lastLog || lastLog.message !== status.current_action) {
          addMigrationLog('info', status.current_action)
        }
      }
      
      // Check if migration is complete
      if (status.processed >= status.total && status.total > 0) {
        migrationInProgress.value = false
        migrationCompleted.value = true
        migrationStatus.value = 'Перенос завершен!'
        
        // Save migration result
        const errorCount = status.errors?.length || 0
        migrationResult.value = {
          total: status.total || 0,
          successful: status.processed || 0,
          failed: errorCount,
          errors: status.errors || []
        }
        
        addMigrationLog('info', `Успешно перенесено ${status.processed} сообщений`)
        
        // Stop polling
        if (migrationStatusPollInterval) {
          clearInterval(migrationStatusPollInterval)
          migrationStatusPollInterval = null
        }
        
        console.log('Migration completed successfully', migrationResult.value)
      }
      
      // Check for errors (but don't stop migration if there are errors)
      if (status.errors && status.errors.length > 0) {
        status.errors.forEach((error: string) => {
          addMigrationLog('error', error)
        })
      }
      
    } catch (err: unknown) {
      console.error('Error polling migration status:', err)
      const error = err as { response?: { status: number } }
      // If 404, migration might not have started yet, continue polling
      // If other error, log but continue
      if (error.response?.status === 404) {
        // Migration not found yet, might still be starting
        addMigrationLog('warn', 'Ожидание запуска миграции...')
      }
    }
  }, 1000) // Poll every second
}

function addMigrationLog(level: string, message: string) {
  migrationLogs.value.push({
    level,
    message,
    timestamp: Date.now() / 1000
  })
  
  // Auto-scroll logs
  const timeoutId = window.setTimeout(() => {
    const logsContent = document.querySelector('.background-logs-content')
    if (logsContent) {
      logsContent.scrollTop = logsContent.scrollHeight
    }
  }, ANIMATION.LOGS_SCROLL_DELAY)
  activeTimeouts.push(timeoutId)
}

function selectAnotherChat() {
  // Reset migration state
  migrationCompleted.value = false
  migrationInProgress.value = false
  migrationResult.value = null
  migrationLogs.value = []
  migrationProgress.value = { loaded: 0, total: 0 }
  
  // Reset message selection
  messages.value.forEach((msg: Message) => {
    msg.selected = false
  })
  
  // Reset chat selections
  selectedChat.value = null
  selectedTelegramChat.value = null
  showDestinationSelection.value = false
  
  // Return WhatsApp planet from corner
  whatsappInCorner.value = false
  
  // Restore WhatsApp chats visibility
  visibleChats.value = chats.value.map((chat: Chat) => ({ ...chat, visible: true }))
  
  // Restore Telegram chats visibility
  visibleTelegramChats.value = telegramChats.value.map((chat: TelegramChat) => ({ ...chat, visible: true }))
}

function finishSession() {
  // Close all connections
  closeMessages()
  if (chatsEventSource) {
    chatsEventSource.close()
    chatsEventSource = null
  }
  
  // Reset all state
  migrationCompleted.value = false
  migrationInProgress.value = false
  migrationResult.value = null
  migrationLogs.value = []
  
  // Reset WhatsApp state
  waStatus.value = 'idle'
  whatsappStatusMessageInternal.value = 'Не подключено'
  selectedChat.value = null
  chats.value = []
  visibleChats.value = []
  whatsappInCorner.value = false
  
  // Reset scroll angles
  chatThetaOffset.value = 0
  targetChatThetaOffset.value = 0
  
  // Reset Telegram state
  tgPhase.value = 'hidden'
  telegramStatusMessage.value = 'Не авторизовано'
  selectedTelegramChat.value = null
  telegramChats.value = []
  visibleTelegramChats.value = []
  showDestinationSelection.value = false
  
  // Reset messages
  messages.value = []
  
  // Clear sessions from store (optional - user might want to keep them)
  // store.setWhatsAppSessionId(null)
  // store.setTelegramUserId(null)
}

function onAvatarError(event: Event, chat: Chat) {
  // If avatar fails to load, hide it and show initial instead
  const img = event.target as HTMLImageElement
  img.style.display = 'none'
  chat.avatar = null
}

// ----------------------------
// Session restoration
// ----------------------------
async function restoreWhatsAppSession() {
  // Check if we have a saved session ID
  const savedSessionId = store.whatsappSessionId || localStorage.getItem('whatsapp_session_id')
  
  if (!savedSessionId) {
    return false
  }
  
  try {
    whatsappStatusMessageInternal.value = 'Проверяю сохраненную сессию...'
    // Try to reuse the session
    const reuseResponse = await api.post(`/whatsapp/sessions/${savedSessionId}/reuse`)
    
    if (reuseResponse.data.reused && reuseResponse.data.status?.status === 'ready') {
      whatsappStatusMessageInternal.value = 'Подключено'
      waSessionId.value = savedSessionId
      store.setWhatsAppSessionId(savedSessionId)
      store.whatsappSessionActive = true
      waStatus.value = 'connected'
      
      // Reset search
      chatSearchQuery.value = ''
      
      // Load chats if session is active
      await loadChats()
      return true
    }
  } catch (err) {
    // Session reuse failed, clear invalid session
    console.warn('Failed to restore WhatsApp session:', err)
    store.setWhatsAppSessionId(null)
    waSessionId.value = null
  }
  
  return false
}

async function restoreTelegramSession() {
  // Check if we have a saved user ID
  const savedUserId = store.telegramUserId || (() => {
    const saved = localStorage.getItem('telegram_user_id')
    return saved ? parseInt(saved, 10) : null
  })()
  
  if (!savedUserId || isNaN(savedUserId)) {
    return false
  }
  
  try {
    // Check if session exists and is valid
    const checkResponse = await api.post('/telegram/check-session', {
      user_id: savedUserId
    })
    
    if (checkResponse.data.valid && checkResponse.data.user_info) {
      tgUserInfo.value = checkResponse.data.user_info
      store.setTelegramUserId(savedUserId)
      store.telegramSessionActive = true
      
      // Restore Telegram state
      tgPhase.value = 'connected'
      telegramStatusMessage.value = 'Авторизовано'
      
      // Load chats
      await loadTelegramChats()
      return true
    }
  } catch (err) {
    // Session check failed, clear invalid session
    console.warn('Failed to restore Telegram session:', err)
    store.setTelegramUserId(null)
    tgUserInfo.value = null
  }
  
  return false
}


onMounted(async () => {
  flightState.launched = false
  flightState.dockedAt = 'wa'
  
  // Wait for DOM to be ready before positioning rocket
  await nextTick()
  
  // Start visible near the top, aligned to WhatsApp. It will hover until user clicks.
  spawnShipAboveWhatsApp()
  startPhysics()
  
  // Initialize target angle to current angle
  targetChatThetaOffset.value = chatThetaOffset.value
  
  // Add scroll listener for chat rotation
  window.addEventListener('wheel', handleChatScroll, { passive: false })
  
  // Try to restore saved sessions
  const whatsappRestored = await restoreWhatsAppSession()
  await restoreTelegramSession()
  
  // If sessions were not restored, show "Connect" buttons in planets
  // User will click on planets to start authorization
  if (!whatsappRestored) {
    waStatus.value = 'idle'
    whatsappStatusMessageInternal.value = 'Нажмите на планету, чтобы подключиться'
  }
  
  // Telegram will show connect button if not restored (tgPhase stays 'hidden')
})

onUnmounted(() => {
  stopPhysics()
  
  // Stop scroll animation
  if (scrollAnimationFrameId !== null) {
    cancelAnimationFrame(scrollAnimationFrameId)
    scrollAnimationFrameId = null
  }
  
  // Remove scroll listener
  window.removeEventListener('wheel', handleChatScroll)
  
  // Stop status polling
  stopStatusPolling()
  
  // Stop migration status polling
  if (migrationStatusPollInterval) {
    clearInterval(migrationStatusPollInterval)
    migrationStatusPollInterval = null
  }
  
  // Close all EventSource connections
  closeMessages()
  if (chatsEventSource) {
    chatsEventSource.close()
    chatsEventSource = null
  }
  if (migrationEventSource) {
    migrationEventSource.close()
    migrationEventSource = null
  }
  
  // Clear all active timeouts
  activeTimeouts.forEach(timeoutId => clearTimeout(timeoutId))
  activeTimeouts = []
})
</script>

<style scoped>
/* Kurzgesagt Palette */
:root {
  --k-dark: #2c1a4d;
  --k-bg: #3d2c61;
  --k-wa: #00d775;
  --k-tg: #40a7e3;
  --k-text: #ffffff;
  --k-accent: #ffca3a;
}

.landing-page {
  background-color: #3d2c61;
  background-image: radial-gradient(circle at 50% 100%, #523b82 0%, #3d2c61 100%);
  position: relative;
  overflow: hidden;
  text-align: center;
  color: #fff;
  height: 100vh;
  width: 100vw;
}

/* Space Traffic SVG */
.space-traffic {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 5;
  pointer-events: none;
}

/* Header Section */
.header-section {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 15;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 2rem 0;
  pointer-events: none;
}

.header-section > * {
  pointer-events: auto;
}

/* Split Screen Layout */
.split-screen-wrapper {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 10;
  display: flex;
  width: 100%;
  height: 100vh;
}

.split-section {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  border-right: 2px solid rgba(255, 255, 255, 0.1);
}

.split-section:last-child {
  border-right: none;
}

.split-whatsapp {
  background: linear-gradient(135deg, rgba(37, 211, 102, 0.1) 0%, rgba(37, 211, 102, 0.05) 100%);
  position: relative;
}

.split-telegram {
  background: linear-gradient(135deg, rgba(64, 167, 227, 0.1) 0%, rgba(64, 167, 227, 0.05) 100%);
}

/* Planet Container */
.planet-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2rem;
  width: 100%;
  height: 100%;
  position: relative;
}

.split-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 0;
  box-sizing: border-box;
  width: auto;
  position: relative;
  transition: all 0.6s ease-out;
}

.split-content .split-description {
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  margin-top: 1rem;
  width: auto;
  max-width: 600px;
  min-width: 300px;
}

.split-content .split-description.split-status-moved {
  position: absolute !important;
  top: auto !important;
  bottom: calc(2rem + 80px) !important;
  left: 50% !important;
  transform: translateX(-50%) !important;
  margin-top: 0 !important;
  max-width: 90% !important;
  min-width: auto !important;
}

.split-content-with-chats {
  position: fixed;
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 10;
}

.split-content-moved {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 40;
}

.split-title {
  font-size: 1.25rem;
  font-weight: 800;
  line-height: 1.2;
  margin: 0;
  padding: 0;
  text-align: center;
  text-shadow: 3px 3px 0px rgba(44, 26, 77, 0.3);
  color: #ffffff;
  width: 100%;
  transition: all 0.6s ease-out;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  position: relative;
}

.split-title-moved {
  position: absolute;
  top: 2rem;
  left: 50%;
  transform: translateX(-50%);
  width: auto;
  pointer-events: auto;
  z-index: 40;
}

.split-whatsapp .split-title-top {
  left: 50%;
  transform: translateX(-50%);
}

.split-whatsapp .split-title {
  color: #25D366;
}

.split-whatsapp .split-title-top {
  color: #25D366;
}

.wa-disconnect-btn {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  padding: 0.25rem 0.75rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  pointer-events: auto;
  font-size: 0.875rem;
  font-weight: 500;
  color: inherit;
  transition: all 0.2s ease;
  backdrop-filter: blur(4px);
  margin: 0;
  text-shadow: inherit;
}

.wa-disconnect-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.3);
  transform: translateY(-1px);
}

.wa-disconnect-btn:active {
  transform: translateY(0);
}

.split-telegram .split-title {
  color: #40a7e3;
}

.split-description {
  font-size: 1.1rem;
  line-height: 1.6;
  margin: 0;
  padding: 0;
  text-align: center;
  font-weight: 500;
  opacity: 0.9;
  max-width: 400px;
  width: 100%;
  transition: all 0.6s ease-out;
}

.split-status-moved {
  position: absolute !important;
  bottom: calc(2rem + 80px) !important; /* 2rem (bottom padding) + ~80px (height of search input + padding) */
  left: 50% !important;
  transform: translateX(-50%) !important;
  width: auto !important;
  max-width: 90% !important;
  pointer-events: none;
  z-index: 10;
  text-align: center;
}

.split-whatsapp .split-status-bottom {
  left: 50%;
  transform: translateX(-50%);
}

.split-title-move-up {
  animation: moveTitleUp 0.6s ease-out forwards;
}

.split-status-move-down {
  animation: moveStatusDown 0.6s ease-out forwards;
}

@keyframes moveTitleUp {
  from {
    transform: translateY(0);
    opacity: 1;
  }
  to {
    transform: translateY(-200px);
    opacity: 0;
  }
}

@keyframes moveStatusDown {
  from {
    transform: translateY(0);
    opacity: 1;
  }
  to {
    transform: translateY(200px);
    opacity: 0;
  }
}

/* Button Section */
.button-section {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 15;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 2rem 0;
  pointer-events: none;
}

.button-section > * {
  pointer-events: auto;
}

/* Legacy content-wrapper for compatibility */
.content-wrapper {
  position: relative;
  z-index: 10;
  max-width: 700px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;
}

.badge {
  background-color: #ffca3a;
  color: #2c1a4d;
  font-weight: 800;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.8rem;
  letter-spacing: 1px;
  box-shadow: 0 4px 0 rgba(0,0,0,0.2);
  transform: rotate(-3deg);
}

.title {
  font-size: 3.5rem;
  font-weight: 800;
  line-height: 1.1;
  margin: 0;
  text-shadow: 4px 4px 0px #2c1a4d;
  color: #ffffff;
}

.description {
  font-size: 1.25rem;
  line-height: 1.6;
  margin: 0;
  font-weight: 500;
  max-width: 600px;
}

.description strong {
  font-weight: 800;
}

.sub-text {
  display: block;
  margin-top: 1rem;
  opacity: 0.8;
  font-size: 1rem;
}

/* Launch Button */
.btn-launch {
  background-color: #ff4757;
  color: white;
  font-size: 1.3rem;
  font-weight: 800;
  padding: 1.2rem 3rem;
  border-radius: 50px;
  border: none;
  box-shadow: 0 8px 0 #c0392b, 0 15px 20px rgba(0,0,0,0.2);
  transition: all 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.btn-launch:hover {
  transform: translateY(4px);
  box-shadow: 0 4px 0 #c0392b, 0 8px 10px rgba(0,0,0,0.2);
}

.btn-launch:active {
  transform: translateY(8px);
  box-shadow: 0 0 0 #c0392b, 0 0 0 rgba(0,0,0,0.2);
}

.btn-launch:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

.btn-launch:disabled:hover {
  transform: none;
  box-shadow: 0 8px 0 #c0392b, 0 15px 20px rgba(0,0,0,0.2);
}

.icon {
  font-size: 1.5rem;
}

/* Cosmic Decorations - STATIC NOW */
.planet {
  position: absolute;
  border-radius: 50%;
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: center;
}

.planet-logo {
  width: 60%;
  height: 60%;
  object-fit: contain;
  opacity: 0.9;
  filter: drop-shadow(0 4px 4px rgba(0,0,0,0.2));
}

.planet-wa {
  width: 280px;
  height: 280px;
  background: #25D366;
  position: relative;
  box-shadow: inset -40px -40px 0 rgba(0,0,0,0.1), 0 0 80px rgba(37, 211, 102, 0.5);
  z-index: 5;
  transition: width 0.6s ease-out,
              height 0.6s ease-out,
              transform 0.5s cubic-bezier(0.4, 0, 0.2, 1),
              box-shadow 0.6s ease-out;
  transform-origin: center center;
}

/* WhatsApp planet shrinking when loading chats */
.planet-wa-shrinking {
  width: 78px;
  height: 78px;
  box-shadow: inset -12px -12px 0 rgba(0,0,0,0.1), 0 0 30px rgba(37, 211, 102, 0.5);
  animation: planetShrink 0.5s ease-out forwards;
}

@keyframes planetShrink {
  from {
    width: 280px;
    height: 280px;
  }
  to {
    width: 78px;
    height: 78px;
  }
}

/* WhatsApp planet with QR code - enlarged */
.planet-wa-qr {
  /* QR max size: 250px
   * Distance from center to QR corner = 250/2 * √2 ≈ 176.78px
   * Padding from QR corner to planet edge = 250/6 ≈ 41.67px
   * Planet radius = 176.78 + 41.67 ≈ 218.45px
   * Planet diameter = 436.9px ≈ 437px */
  width: 437px;
  height: 437px;
  box-shadow: inset -65px -65px 0 rgba(0,0,0,0.1), 0 0 100px rgba(37, 211, 102, 0.5);
  animation: planetExpand 0.6s ease-out;
  transition: width 0.6s ease-out, height 0.6s ease-out, box-shadow 0.6s ease-out;
}

@keyframes planetExpand {
  from {
    width: 280px;
    height: 280px;
  }
  to {
    width: 437px;
    height: 437px;
  }
}

/* WhatsApp planet collapsing from QR size back to normal */
.planet-wa-qr-collapsing {
  width: 280px;
  height: 280px;
  box-shadow: inset -40px -40px 0 rgba(0,0,0,0.1), 0 0 80px rgba(37, 211, 102, 0.5);
  animation: planetCollapse 0.6s ease-out forwards;
}

@keyframes planetCollapse {
  from {
    width: 437px;
    height: 437px;
    box-shadow: inset -65px -65px 0 rgba(0,0,0,0.1), 0 0 100px rgba(37, 211, 102, 0.5);
  }
  to {
    width: 280px;
    height: 280px;
    box-shadow: inset -40px -40px 0 rgba(0,0,0,0.1), 0 0 80px rgba(37, 211, 102, 0.5);
  }
}

/* WhatsApp planet with chats - reduced size */
.planet-wa-with-chats {
  /* Chat circle radius = 52/2 = 26px
   * Planet radius should be 1.5 * chat radius = 1.5 * 26 = 39px
   * Planet diameter = 78px */
  width: 78px;
  height: 78px;
  box-shadow: inset -12px -12px 0 rgba(0,0,0,0.1), 0 0 30px rgba(37, 211, 102, 0.5);
  cursor: default;
  pointer-events: none;
  /* No transform here - animation from planet-wa-shrinking already applied */
}

/* WhatsApp planet when chat is selected - keep reduced size */
.planet-wa-chat-selected {
  width: 78px;
  height: 78px;
  box-shadow: inset -12px -12px 0 rgba(0,0,0,0.1), 0 0 30px rgba(37, 211, 102, 0.5);
  cursor: default;
  pointer-events: none;
}

/* WhatsApp planet when messages are loaded - move up */
.planet-wa-messages-loaded {
  transform: translate(-50%, -50%) translateY(-200px) !important;
  transition: transform 0.6s ease-out !important;
}

/* Planet lock icon */
.planet-lock {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 4rem;
  z-index: 25;
  pointer-events: none;
  opacity: 0.8;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
  transition: opacity 0.4s ease-out, transform 0.4s ease-out;
}

.planet-lock-fading {
  opacity: 0;
  transform: translate(-50%, -50%) scale(0.8);
}

/* WhatsApp planet shrunk state (after connection) */
.planet-wa-shrunk {
  width: 105px;
  height: 105px;
  bottom: 50% !important;
  left: 50% !important;
  transform: translate(-50%, 50%);
  box-shadow: inset -15px -15px 0 rgba(0,0,0,0.1), 0 0 40px rgba(37, 211, 102, 0.5);
  z-index: 5 !important; /* Fourth layer: planet and rocket */
}

.planet-wa-shrunk .planet-logo {
  opacity: 0.9;
  transition: opacity 0.5s ease-in-out;
}

/* WhatsApp planet corner state */
.planet-wa-corner {
  width: 280px;
  height: 280px;
  bottom: -40px !important;
  left: -40px !important;
  top: auto !important;
  transform: none;
  box-shadow: inset -40px -40px 0 rgba(0,0,0,0.1), 0 0 80px rgba(37, 211, 102, 0.5);
  z-index: 25;
}

.planet-wa-corner .planet-logo {
  opacity: 0.9;
}

.planet-tg {
  width: 280px;
  height: 280px;
  background: #229ED9;
  position: relative;
  box-shadow: inset -40px -40px 0 rgba(0,0,0,0.1), 0 0 80px rgba(34, 158, 217, 0.5);
  z-index: 20;
  transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1),
              height 0.5s cubic-bezier(0.4, 0, 0.2, 1),
              transform 0.5s cubic-bezier(0.4, 0, 0.2, 1),
              box-shadow 0.5s cubic-bezier(0.4, 0, 0.2, 1);
  transform-origin: center center;
}


/* Telegram planet shrunk state */
.planet-tg-shrunk {
  width: 70px;
  height: 70px;
  transform: translate(-50%, calc(-50% - 60px)) !important; /* Slightly above center */
  box-shadow: inset -10px -10px 0 rgba(0,0,0,0.1), 0 0 30px rgba(34, 158, 217, 0.4);
  z-index: 25;
}

.planet-tg-shrunk .planet-logo {
  opacity: 0.9;
}

/* Telegram planet exiting state (after launch button) */
.planet-tg-exiting {
  width: 180px !important;
  height: 180px !important;
  bottom: -100px !important;
  right: -100px !important;
  opacity: 0.4 !important;
  transform: scale(0.65) !important;
  box-shadow: inset -25px -25px 0 rgba(0,0,0,0.1), 0 0 50px rgba(34, 158, 217, 0.3) !important;
  transition: width 1.2s cubic-bezier(0.25, 0.46, 0.45, 0.94),
              height 1.2s cubic-bezier(0.25, 0.46, 0.45, 0.94),
              bottom 1.2s cubic-bezier(0.25, 0.46, 0.45, 0.94),
              right 1.2s cubic-bezier(0.25, 0.46, 0.45, 0.94),
              transform 1.2s cubic-bezier(0.25, 0.46, 0.45, 0.94),
              opacity 1.2s cubic-bezier(0.25, 0.46, 0.45, 0.94),
              box-shadow 1.2s cubic-bezier(0.25, 0.46, 0.45, 0.94) !important;
  pointer-events: none;
}

.planet-tg-exiting .planet-logo {
  opacity: 0.4 !important;
  transition: opacity 1.2s cubic-bezier(0.25, 0.46, 0.45, 0.94) !important;
}

/* Telegram auth overlay */
.tg-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  opacity: 0;
  transition: opacity 0.5s ease-in-out;
  z-index: 30;
  pointer-events: none;
}

.tg-overlay.overlay-visible {
  opacity: 1;
  pointer-events: auto;
}

.tg-auth-form {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.tg-auth-title {
  color: white;
  font-size: 1.2rem;
  font-weight: 600;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
  margin-bottom: 8px;
}

.tg-input {
  width: 220px;
  padding: 14px 20px;
  font-size: 1.1rem;
  border: none;
  border-radius: 25px;
  background: rgba(255, 255, 255, 0.95);
  color: #333;
  text-align: center;
  outline: none;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
}

.tg-input::placeholder {
  color: #999;
}

.tg-input-code {
  font-size: 1.5rem;
  letter-spacing: 8px;
  width: 180px;
}

.tg-btn {
  background: linear-gradient(135deg, #229ED9 0%, #1a7cb8 100%);
  color: white;
  font-size: 1rem;
  font-weight: 600;
  padding: 12px 30px;
  border-radius: 25px;
  border: none;
  cursor: pointer;
  box-shadow: 0 4px 15px rgba(34, 158, 217, 0.4);
  transition: all 0.2s ease;
}

.tg-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(34, 158, 217, 0.5);
}

.tg-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.tg-connected {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.tg-success-icon {
  font-size: 4rem;
  color: white;
  text-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
}

.tg-connected-text {
  color: white;
  font-size: 1.5rem;
  font-weight: 700;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.tg-error {
  color: #ffca3a;
  font-size: 0.95rem;
  margin-top: 12px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

/* Stars styles moved to components/landing/StarsBackground.vue */

/* Element fade-out animation */
.element-hidden {
  opacity: 0 !important;
  transform: translateY(-20px) scale(0.95) !important;
  pointer-events: none !important;
  transition: opacity 0.4s ease-out, transform 0.4s ease-out !important;
}

/* Ensure elements have transition for smooth animation */
.badge,
.title,
.description,
.btn-launch,
.space-traffic,
.split-title,
.split-description {
  transition: opacity 0.4s ease-out, transform 0.4s ease-out;
}

/* When migration started, prevent interactions with content */
.content-wrapper.fade-out,
.header-section.fade-out,
.split-screen-wrapper.fade-out,
.button-section.fade-out {
  pointer-events: none;
}

/* WhatsApp connection overlay */
.wa-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  opacity: 0;
  transition: opacity 0.5s ease-in-out;
  z-index: 30;
  pointer-events: none;
}

.wa-overlay.overlay-visible {
  opacity: 1;
  pointer-events: auto;
}

/* Overlay in planet (split-screen mode) */
.wa-overlay.overlay-in-planet {
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
  border-radius: 50%;
}

.wa-overlay.overlay-no-background {
  background: transparent;
  backdrop-filter: none;
}

.tg-overlay.overlay-in-planet {
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
  border-radius: 50%;
}

/* Connect prompt styles */
.wa-connect-prompt,
.tg-connect-prompt {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 20px;
}

.wa-connect-text,
.tg-connect-text {
  color: white;
  font-size: 1rem;
  font-weight: 500;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
  text-align: center;
}

.wa-connect-btn,
.tg-connect-btn {
  background: linear-gradient(135deg, #25D366 0%, #1da851 100%);
  color: white;
  font-size: 1rem;
  font-weight: 600;
  padding: 12px 30px;
  border-radius: 25px;
  border: none;
  cursor: pointer;
  box-shadow: 0 4px 15px rgba(37, 211, 102, 0.4);
  transition: all 0.2s ease;
}

.tg-connect-btn {
  background: linear-gradient(135deg, #229ED9 0%, #1a7cb8 100%);
  box-shadow: 0 4px 15px rgba(34, 158, 217, 0.4);
}

.wa-connect-btn:hover,
.tg-connect-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(37, 211, 102, 0.5);
}

.tg-connect-btn:hover {
  box-shadow: 0 6px 20px rgba(34, 158, 217, 0.5);
}

/* Clickable planet styles */
.planet-wa-clickable,
.planet-tg-clickable {
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.planet-wa-clickable:hover {
  transform: scale(1.05);
  box-shadow: inset -40px -40px 0 rgba(0,0,0,0.1), 0 0 100px rgba(37, 211, 102, 0.6) !important;
}

.planet-tg-clickable:hover {
  transform: scale(1.05);
  box-shadow: inset -40px -40px 0 rgba(0,0,0,0.1), 0 0 100px rgba(34, 158, 217, 0.6) !important;
}

.wa-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.wa-spinner {
  width: 50px;
  height: 50px;
  border: 4px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.wa-loading-text {
  display: none; /* Text moved to status message */
}

.wa-qr {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.wa-qr-image {
  /* Max QR size: 250px, with padding 1/6 of QR width (≈41.67px) on each side */
  max-width: 250px;
  max-height: 250px;
  width: 250px;
  height: 250px;
  border-radius: 16px;
  background: white;
  padding: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  animation: qrAppear 0.5s ease-out 0.6s both;
  opacity: 0;
  transform: scale(0.8);
}

@keyframes qrAppear {
  from {
    opacity: 0;
    transform: scale(0.8);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.wa-qr-hint {
  display: none; /* Text moved to status message */
}

.wa-connected {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.wa-success-icon {
  font-size: 4rem;
  color: white;
  text-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
}

.wa-connected-text {
  color: white;
  font-size: 1.5rem;
  font-weight: 700;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.wa-error {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.wa-error p {
  color: #ffca3a;
  font-size: 0.95rem;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.wa-retry-btn {
  background: rgba(255, 255, 255, 0.2);
  border: 2px solid white;
  color: white;
  padding: 8px 20px;
  border-radius: 20px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.wa-retry-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* Pulsing logo animation while loading chats */
.logo-pulsing {
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.9; }
}

/* Chats loading message */
.chats-loading-message {
  position: fixed;
  bottom: 30%;
  left: 50%;
  transform: translateX(-50%);
  z-index: 25;
  pointer-events: none;
}

.chats-loading-message p {
  color: white;
  font-size: 1.1rem;
  font-weight: 500;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
  opacity: 0.9;
}

/* Chat selection title */
.chat-selection-title {
  position: fixed;
  top: 80px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 50;
  color: white;
  font-size: 2rem;
  font-weight: 600;
  text-align: center;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.5);
  margin: 0;
  animation: fadeInDown 0.5s ease-out;
}

@keyframes fadeInDown {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

/* Chat search container */
.chat-search-container {
  position: fixed;
  bottom: 60px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 101;
  width: 100%;
  max-width: 500px;
  padding: 0 20px;
  animation: fadeInUp 0.5s ease-out;
}

.split-whatsapp-search {
  position: absolute;
  bottom: 2rem;
  left: 50%;
  transform: translateX(-50%);
  z-index: 101;
  width: calc(100% - 40px);
  max-width: 500px;
  padding: 0 20px;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

.chat-search-hiding {
  animation: slideDownOut 0.4s ease-out forwards;
}

@keyframes slideDownOut {
  from {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
  to {
    opacity: 0;
    transform: translateX(-50%) translateY(100px);
  }
}

.selected-chat-controls {
  position: absolute;
  bottom: 2rem;
  left: 50%;
  transform: translateX(-50%);
  z-index: 101;
  width: calc(100% - 40px);
  max-width: 500px;
  padding: 0 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  opacity: 0;
  transform: translateX(-50%) translateY(100px);
  pointer-events: none;
}

.selected-chat-controls-visible {
  animation: slideUpIn 0.4s ease-out forwards;
  pointer-events: auto;
}

.selected-chat-controls-hiding {
  opacity: 0;
  transform: translateX(-50%) translateY(100px);
  pointer-events: none;
  transition: opacity 0.4s ease-out, transform 0.4s ease-out;
}

@keyframes slideUpIn {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(100px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}


.btn-view-chat {
  background: rgba(37, 211, 102, 0.2);
  border: 2px solid #25D366;
  border-radius: 12px;
  padding: 0.75rem 2rem;
  color: #25D366;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  backdrop-filter: blur(4px);
  min-width: 200px;
}

.btn-view-chat:hover {
  background: rgba(37, 211, 102, 0.3);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(37, 211, 102, 0.4);
}

.btn-view-chat:active {
  transform: translateY(0);
}

.chat-search-input {
  width: 100%;
  padding: 16px 24px;
  font-size: 1.1rem;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  color: white;
  outline: none;
  transition: all 0.3s ease;
}

.chat-search-input::placeholder {
  color: rgba(255, 255, 255, 0.6);
}

.chat-search-input:focus {
  border-color: #ffca3a;
  background: rgba(255, 255, 255, 0.15);
  box-shadow: 0 4px 20px rgba(255, 202, 58, 0.3);
}

.chat-search-input:hover {
  border-color: rgba(255, 255, 255, 0.5);
  background: rgba(255, 255, 255, 0.12);
}

/* Chat circles */
.chat-circle {
  position: fixed;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 30;
  opacity: 0;
  transform: scale(0);
  /* CRITICAL: No transition on left/top for scroll rotation - must update instantly */
  /* Only transition opacity, transform (scale), and box-shadow for appearance animations */
  transition: opacity 0.3s ease-out, transform 0.3s ease-out, box-shadow 0.2s ease, z-index 0s, width 0.6s cubic-bezier(0.4, 0, 0.2, 1), height 0.6s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
  /* Force instant position updates for scroll rotation */
  will-change: left, top;
}

.chat-circle.chat-visible {
  opacity: 1;
  transform: scale(1);
  animation: chatAppearSmooth 0.4s ease-out forwards;
}

@keyframes chatAppearSmooth {
  from {
    opacity: 0;
    transform: scale(0);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.chat-circle.chat-visible:hover {
  transform: scale(1.15) !important;
  box-shadow: 0 6px 25px rgba(0, 0, 0, 0.4);
  z-index: 100 !important;
}

.chat-circle.chat-visible:active {
  transform: scale(1.05) !important;
}

.chat-initial {
  color: white;
  font-size: 1.2rem;
  font-weight: 700;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
  user-select: none;
}

.chat-avatar {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
}

.chat-circle.has-avatar {
  background: transparent;
  padding: 0;
  overflow: hidden;
}

/* Selected chat state */
.chat-circle.chat-selected {
  transform: scale(1.4) !important;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5), 0 0 20px rgba(102, 126, 234, 0.6);
  z-index: 99 !important;
  border: 3px solid #ffca3a;
}

/* Chat moving to corner animation */
.chat-circle.chat-moving-to-corner {
  left: 30px !important;
  top: 30px !important;
  width: 52px !important;
  height: 52px !important;
  transform: scale(1) !important;
  transition: left 0.6s cubic-bezier(0.4, 0, 0.2, 1),
              top 0.6s cubic-bezier(0.4, 0, 0.2, 1),
              transform 0.6s cubic-bezier(0.4, 0, 0.2, 1),
              width 0.6s cubic-bezier(0.4, 0, 0.2, 1),
              height 0.6s cubic-bezier(0.4, 0, 0.2, 1),
              box-shadow 0.6s cubic-bezier(0.4, 0, 0.2, 1),
              border 0.6s cubic-bezier(0.4, 0, 0.2, 1) !important;
  z-index: 30 !important;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3) !important;
  border: 2px solid #ffca3a !important;
}

/* Chat moving to planet center animation */
.chat-circle.chat-moving-to-planet {
  /* Center of WhatsApp planet: left half of screen (25% of width), vertical center (50% of height) */
  /* Planet size: 78px, Chat size: 52px */
  /* Position: centerX - chatSize/2, centerY - chatSize/2 */
  left: calc(25% - 26px) !important;
  top: calc(50% - 26px) !important;
  width: 52px !important;
  height: 52px !important;
  transform: scale(1) !important;
  transition: left 0.6s cubic-bezier(0.4, 0, 0.2, 1),
              top 0.6s cubic-bezier(0.4, 0, 0.2, 1),
              transform 0.6s cubic-bezier(0.4, 0, 0.2, 1),
              width 0.6s cubic-bezier(0.4, 0, 0.2, 1),
              height 0.6s cubic-bezier(0.4, 0, 0.2, 1),
              box-shadow 0.6s cubic-bezier(0.4, 0, 0.2, 1),
              border 0.6s cubic-bezier(0.4, 0, 0.2, 1),
              opacity 0.6s cubic-bezier(0.4, 0, 0.2, 1) !important;
  z-index: 30 !important;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3) !important;
  border: 2px solid #ffca3a !important;
}

/* Chat hiding animation */
.chat-circle.chat-hiding {
  opacity: 0 !important;
  transform: scale(0.5) !important;
  pointer-events: none !important;
  transition: opacity 0.4s ease-out, transform 0.4s ease-out !important;
}

/* Dimmed (non-selected) chats */
.chat-circle.chat-dimmed {
  opacity: 0.4 !important;
  transform: scale(0.9) !important;
  filter: grayscale(30%);
  transition: opacity 0.3s ease-out, transform 0.3s ease-out, filter 0.3s ease-out !important;
}

.chat-circle.chat-dimmed:hover {
  opacity: 0.7 !important;
  transform: scale(1) !important;
}

/* WhatsApp planet when messages are loaded - move up */
.planet-wa-messages-loaded {
  transform: translate(-50%, calc(-50% - 200px)) !important;
  transition: transform 0.6s ease-out !important;
}

/* Messages card container */
.messages-card-container {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 90%;
  max-width: 600px;
  z-index: 25;
  animation: messagesCardAppear 0.6s ease-out;
}

@keyframes messagesCardAppear {
  from {
    opacity: 0;
    transform: translate(-50%, -50%) translateY(20px);
  }
  to {
    opacity: 1;
    transform: translate(-50%, -50%) translateY(0);
  }
}

.messages-card {
  background: rgba(20, 20, 30, 0.95);
  backdrop-filter: blur(10px);
  border: 2px solid rgba(37, 211, 102, 0.3);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
  overflow: hidden;
}

.messages-card-header {
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(37, 211, 102, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.messages-card-title {
  margin: 0;
  color: #ffffff;
  font-size: 1.2rem;
  font-weight: 600;
}

.messages-card-count {
  color: #25D366;
  font-size: 0.9rem;
  font-weight: 600;
  background: rgba(37, 211, 102, 0.2);
  padding: 4px 12px;
  border-radius: 12px;
}

.messages-card-content {
  max-height: 400px;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.messages-card-content::-webkit-scrollbar {
  width: 6px;
}

.messages-card-content::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 3px;
}

.messages-card-content::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 3px;
}

.messages-card-content::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.5);
}

.message-card-item {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 12px 16px;
  transition: all 0.2s ease;
}

.message-card-item:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.2);
}

.message-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.message-card-sender {
  color: #25D366;
  font-weight: 600;
  font-size: 0.9rem;
}

.message-card-time {
  color: rgba(255, 255, 255, 0.5);
  font-size: 0.75rem;
}

.message-card-body {
  color: rgba(255, 255, 255, 0.9);
}

.message-card-text {
  line-height: 1.5;
  word-wrap: break-word;
  white-space: pre-wrap;
  margin: 0;
}

.message-card-media {
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.9rem;
  margin-top: 8px;
}

/* Telegram chat circles */
.telegram-chat-circle {
  position: fixed;
  border-radius: 50%;
  background: linear-gradient(135deg, #229ED9 0%, #1a7cb8 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 15;
  opacity: 0;
  transform: scale(0);
  transition: opacity 0.3s ease-out, transform 0.3s ease-out, box-shadow 0.2s ease;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
}

.telegram-chat-circle.tg-chat-visible {
  opacity: 1;
  transform: scale(1);
}

.telegram-chat-circle.tg-chat-visible:hover {
  transform: scale(1.15) !important;
  box-shadow: 0 6px 25px rgba(34, 158, 217, 0.5);
  z-index: 100 !important;
}

.telegram-chat-circle.tg-chat-visible:active {
  transform: scale(1.05) !important;
}

.tg-chat-initial {
  color: white;
  font-size: 1.2rem;
  font-weight: 700;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
  user-select: none;
}

.telegram-chat-circle.tg-chat-selected {
  transform: scale(1.4) !important;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5), 0 0 20px rgba(34, 158, 217, 0.6);
  z-index: 99 !important;
  border: 3px solid #ffca3a;
}

.telegram-chat-circle.tg-chat-dimmed {
  opacity: 0.4 !important;
  transform: scale(0.9) !important;
  filter: grayscale(30%);
}

.telegram-chat-circle.tg-chat-dimmed:hover {
  opacity: 0.7 !important;
  transform: scale(1) !important;
}


.btn-continue:disabled:hover {
  transform: none;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
}

.message-dot {
  position: absolute;
  border-radius: 50%;
  opacity: 0;
  animation: dotAppear 0.4s ease-out forwards;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.4);
  transition: transform 0.2s ease;
}

.message-dot:hover {
  transform: scale(1.3);
  z-index: 10;
}

@keyframes dotAppear {
  from {
    opacity: 0;
    transform: scale(0) rotate(0deg);
  }
  to {
    opacity: 0.85;
    transform: scale(1) rotate(360deg);
  }
}

/* Message type colors */
.message-dot-text {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.message-dot-image {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.message-dot-video {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.message-dot-audio,
.message-dot-voice {
  background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
}

.message-dot-document {
  background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
}

.message-dot-sticker {
  background: linear-gradient(135deg, #30cfd0 0%, #330867 100%);
}

.message-dot-location {
  background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
}

.message-dot-contact {
  background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
}

/* Default color for unknown types */
.message-dot {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

/* Selected chat panel */
.selected-chat-panel {
  position: fixed;
  bottom: 60px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  z-index: 50;
  animation: slideUp 0.3s ease-out;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}


.selected-chat-buttons {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-back {
  background: rgba(37, 211, 102, 0.3);
  color: white;
  font-size: 1.1rem;
  font-weight: 700;
  padding: 14px 40px;
  border-radius: 30px;
  border: 2px solid rgba(37, 211, 102, 0.5);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  box-shadow: 0 6px 20px rgba(37, 211, 102, 0.2);
  transition: all 0.2s ease;
  backdrop-filter: blur(10px);
}

.btn-back:hover {
  background: rgba(37, 211, 102, 0.4);
  border-color: rgba(37, 211, 102, 0.7);
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(37, 211, 102, 0.3);
}

.btn-back:active {
  transform: translateY(0);
}

.btn-next {
  background: linear-gradient(135deg, #229ED9 0%, #1a7cb8 100%);
  color: white;
  font-size: 1.1rem;
  font-weight: 700;
  padding: 14px 40px;
  border-radius: 30px;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  box-shadow: 0 6px 20px rgba(34, 158, 217, 0.4);
  transition: all 0.2s ease;
}

.btn-next:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(34, 158, 217, 0.5);
}

.btn-next:active {
  transform: translateY(0);
}

.btn-arrow {
  font-size: 1.3rem;
}

/* Destination selection panel */
.destination-selection-panel {
  position: fixed;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  z-index: 50;
  width: 100%;
  padding-top: 40px;
  animation: slideUp 0.3s ease-out;
}

.selected-chat-subtitle {
  color: rgba(255, 255, 255, 0.8);
  font-size: 1rem;
  font-weight: 500;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
  margin: 0;
}

.selected-wa-chat-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  margin: 8px 0;
}

.wa-chat-circle {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
  border: 3px solid #ffca3a;
}

.wa-chat-avatar {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
}

.wa-chat-initial {
  color: white;
  font-size: 2rem;
  font-weight: 700;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

.wa-chat-name {
  color: white;
  font-size: 1.2rem;
  font-weight: 600;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
  margin: 0;
}

.destination-title {
  color: white;
  font-size: 1.5rem;
  font-weight: 700;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
  margin: 16px 0 8px 0;
}

.destination-option {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.1);
  border: 2px solid rgba(255, 255, 255, 0.2);
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
}

.destination-option:hover {
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.3);
  transform: translateY(-2px);
}

.destination-option.destination-selected {
  background: rgba(34, 158, 217, 0.3);
  border-color: #229ED9;
  box-shadow: 0 4px 15px rgba(34, 158, 217, 0.4);
}

.destination-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.destination-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.destination-name {
  color: white;
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

.destination-desc {
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.9rem;
  margin: 0;
}

.chats-loading-message {
  color: rgba(255, 255, 255, 0.7);
  text-align: center;
  padding: 20px;
  font-size: 0.95rem;
}

.chats-error-message {
  color: #ffca3a;
  text-align: center;
  padding: 20px;
  font-size: 0.95rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.chats-retry-btn {
  background: rgba(255, 255, 255, 0.2);
  border: 2px solid #ffca3a;
  color: #ffca3a;
  padding: 8px 20px;
  border-radius: 20px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.chats-retry-btn:hover {
  background: rgba(255, 202, 58, 0.2);
}

.new-group-container {
  width: 100%;
  margin-top: 8px;
}

.new-group-input {
  width: 100%;
  padding: 14px 20px;
  font-size: 1rem;
  border: 2px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  outline: none;
  transition: all 0.2s ease;
}

.new-group-input::placeholder {
  color: rgba(255, 255, 255, 0.5);
}

.new-group-input:focus {
  border-color: #229ED9;
  background: rgba(255, 255, 255, 0.15);
}

.btn-start-migration {
  position: fixed;
  bottom: 40px;
  left: 50%;
  transform: translateX(-50%);
  background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
  color: white;
  font-size: 1.3rem;
  font-weight: 800;
  padding: 18px 50px;
  border-radius: 50px;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 8px 0 #0d6e5f, 0 15px 20px rgba(37, 211, 102, 0.4);
  transition: all 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  z-index: 60;
}

.btn-start-migration:hover:not(:disabled) {
  transform: translateX(-50%) translateY(4px);
  box-shadow: 0 4px 0 #0d6e5f, 0 8px 10px rgba(37, 211, 102, 0.4);
}

.btn-start-migration:active:not(:disabled) {
  transform: translateX(-50%) translateY(8px);
  box-shadow: 0 0 0 #0d6e5f, 0 0 0 rgba(37, 211, 102, 0.4);
}

.btn-start-migration:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: translateX(-50%);
}

/* Migration overlay */
.migration-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
}

.migration-loading-circle {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
  color: white;
}

.loading-circle {
  width: 80px;
  height: 80px;
  border: 6px solid rgba(255, 255, 255, 0.2);
  border-top-color: #ffca3a;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.migration-status-text {
  font-size: 1.5rem;
  font-weight: 600;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
  margin: 0;
  text-align: center;
}

.migration-progress-text {
  font-size: 1rem;
  color: rgba(255, 255, 255, 0.8);
  margin: 0;
  text-align: center;
}

/* Migration completion screen */
.migration-completion-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 60;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(8px);
}

.migration-completion-content {
  background: rgba(20, 20, 30, 0.95);
  backdrop-filter: blur(10px);
  border: 2px solid rgba(255, 255, 255, 0.2);
  border-radius: 24px;
  padding: 40px;
  max-width: 600px;
  width: 90%;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
  color: white;
}

.completion-icon {
  font-size: 5rem;
  animation: scaleIn 0.5s ease-out;
}

@keyframes scaleIn {
  from {
    transform: scale(0);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}

.completion-title {
  font-size: 2rem;
  font-weight: 700;
  margin: 0;
  text-align: center;
  color: #ffca3a;
}

.completion-stats {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 20px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 12px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
}

.stat-label {
  font-size: 1rem;
  color: rgba(255, 255, 255, 0.8);
}

.stat-value {
  font-size: 1.2rem;
  font-weight: 600;
  color: #ffca3a;
}

.stat-item.stat-error .stat-value {
  color: #f5576c;
}

.completion-chats-info {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 20px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
}

.chat-info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.chat-info-label {
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.6);
}

.chat-info-name {
  font-size: 1.1rem;
  font-weight: 600;
  color: white;
}

.completion-errors {
  width: 100%;
  padding: 16px;
  background: rgba(245, 87, 108, 0.1);
  border: 1px solid rgba(245, 87, 108, 0.3);
  border-radius: 12px;
}

.completion-errors h3 {
  margin: 0 0 12px 0;
  font-size: 1rem;
  color: #f5576c;
}

.completion-errors ul {
  margin: 0;
  padding-left: 20px;
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.9rem;
}

.completion-errors li {
  margin: 4px 0;
}

.completion-actions {
  display: flex;
  gap: 16px;
  width: 100%;
  margin-top: 8px;
}

.btn-select-another,
.btn-finish-session {
  flex: 1;
  padding: 14px 24px;
  font-size: 1rem;
  font-weight: 600;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-select-another {
  background: rgba(255, 255, 255, 0.1);
  color: white;
  border: 2px solid rgba(255, 255, 255, 0.3);
}

.btn-select-another:hover {
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.5);
  transform: translateY(-2px);
}

.btn-finish-session {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-finish-session:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

@media (max-width: 768px) {
  .title { font-size: 2.5rem; }
  .planet-wa { 
    width: 60px; 
    height: 60px; 
    left: 25%;
    top: 50%;
    transform: translate(-50%, -50%);
  }
  .planet-tg { 
    width: 180px; 
    height: 180px; 
    left: 75%;
    top: 50%;
    transform: translate(-50%, -50%);
  }
}
</style>
