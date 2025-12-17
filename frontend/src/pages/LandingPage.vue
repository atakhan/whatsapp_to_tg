<template>
  <div class="page landing-page">
    <!-- Stars -->
    <div 
      v-for="(star, index) in stars" 
      :key="index"
      class="star"
      :style="{
        left: star.x + '%',
        top: star.y + '%',
        width: star.size + 'px',
        height: star.size + 'px',
        opacity: star.opacity,
        animationDuration: star.duration + 's',
        animationDelay: star.delay + 's'
      }"
    ></div>

    <!-- Space layer: ship + engines (physics-driven) -->
    <svg class="space-traffic" :class="{ 'element-hidden': hideStage >= 5 }" width="100%" height="100%">
      <defs>
        <g id="rocket-ship">
           <!-- Scale wrapper -->
           <g transform="scale(3.5)">
             <!-- Ship Body -->
             <path fill="#ffffff" d="M0-10 C-5-10 -5 5 0 10 C5 5 5-10 0-10 Z" />
             <path fill="#ff4757" d="M0-10 C-5-10 -5 -5 0 -8 C5 -5 5 -10 0-10 Z" />
             <path fill="#ff4757" d="M-5 5 L-7 12 L-3 10 Z" />
             <path fill="#ff4757" d="M5 5 L7 12 L3 10 Z" />
             <circle cx="0" cy="-2" r="2" fill="#40a7e3" />
           </g>
        </g>
      </defs>

      <!-- Ship (rendered from physics state) -->
      <g :transform="`translate(${shipState.x}, ${shipState.y}) rotate(${shipState.rotation * 180 / Math.PI + 90})`">
          <use href="#rocket-ship" />

          <!-- MAIN ENGINE FLAME -->
          <g transform="scale(3.5)" v-show="shipState.mainEngine">
               <!-- Flame size depends on throttle level -->
               <path fill="#ffca3a" d="M-2 10 Q0 25 2 10 Z" opacity="0.9">
                  <animate attributeName="d" values="M-2 10 Q0 25 2 10 Z; M-2 10 Q0 20 2 10 Z; M-2 10 Q0 25 2 10 Z" dur="0.05s" repeatCount="indefinite" />
                  <!-- Dynamic flame scaling based on throttle -->
                   <animateTransform 
                      attributeName="transform" 
                      type="scale" 
                      :values="shipState.throttle > 0.5 ? '1 1.5; 1 2.5; 1 1.5' : '1 0.5; 1 0.8; 1 0.5'"
                      dur="0.1s" 
                      repeatCount="indefinite"
                  />
               </path>
          </g>

          <!-- RCS THRUSTERS -->
          <g transform="scale(3.5)">
              <!-- Left RCS (Rotates Ship Right / Clockwise) -->
              <path 
                  v-show="shipState.rcsLeft"
                  fill="#ffca3a" 
                  d="M -4 -9 Q -9 -9.5 -4 -10 Z"
              >
                   <animate attributeName="d" values="M -4 -9 Q -9 -9.5 -4 -10 Z; M -4 -9 Q -7 -9.5 -4 -10 Z" dur="0.05s" repeatCount="indefinite" />
              </path>
              
              <!-- Right RCS (Rotates Ship Left / Counter-Clockwise) -->
              <path 
                  v-show="shipState.rcsRight"
                  fill="#ffca3a" 
                  d="M 4 -9 Q 9 -9.5 4 -10 Z"
              >
                  <animate attributeName="d" values="M 4 -9 Q 9 -9.5 4 -10 Z; M 4 -9 Q 7 -9.5 4 -10 Z" dur="0.05s" repeatCount="indefinite" />
              </path>
          </g>
      </g>
    </svg>

    <!-- Planets -->
    <div class="planet planet-wa" ref="planetWa" :style="{ boxShadow: waBoxShadow }" :class="{ 
      'planet-wa-centered': whatsappCentered && !whatsappShrunk && !whatsappInCorner, 
      'planet-wa-shrunk': whatsappShrunk && !whatsappInCorner,
      'planet-wa-corner': whatsappInCorner,
      'planet-wa-pulsing': chatsLoading 
    }">
      <img src="https://upload.wikimedia.org/wikipedia/commons/6/6b/WhatsApp.svg" class="planet-logo" :class="{ 'logo-pulsing': chatsLoading }" alt="WhatsApp Planet" />
      
      <!-- WhatsApp connection overlay -->
      <div v-if="whatsappCentered" class="wa-overlay" :class="{ 'overlay-visible': showWaOverlay }">
        <!-- Loading state -->
        <div v-if="waStatus === 'loading'" class="wa-loading">
          <div class="wa-spinner"></div>
          <p class="wa-loading-text">Пробуем подключиться к WhatsApp<br>и получить QR-код для входа...</p>
        </div>
        
        <!-- QR Code state -->
        <div v-else-if="waStatus === 'qr' && qrCode" class="wa-qr">
          <img :src="`data:image/png;base64,${qrCode}`" alt="QR Code" class="wa-qr-image" />
          <p class="wa-qr-hint">Отсканируйте в WhatsApp</p>
        </div>
        
        <!-- Connected state -->
        <div v-else-if="waStatus === 'connected'" class="wa-connected">
          <span class="wa-success-icon">✓</span>
          <p class="wa-connected-text">Подключено!</p>
        </div>
        
        <!-- Error state -->
        <div v-if="waError" class="wa-error">
          <p>{{ waError }}</p>
          <button @click="retryConnection" class="wa-retry-btn">Попробовать снова</button>
        </div>
      </div>
    </div>
    
    <!-- Chat circles orbiting around WhatsApp planet -->
    <div 
      v-for="(chat, index) in visibleChats" 
      :key="chat.id"
      class="chat-circle"
      :class="{ 
        'chat-visible': chat.visible, 
        'has-avatar': chat.avatar,
        'chat-selected': selectedChat?.id === chat.id,
        'chat-dimmed': selectedChat && selectedChat.id !== chat.id,
        'chat-moving-to-corner': chatMovingToCorner && selectedChat?.id === chat.id
      }"
      :style="getChatCircleStyle(index)"
      @click="selectChat(chat)"
      :title="chat.name"
    >
      <img v-if="chat.avatar" :src="chat.avatar" :alt="chat.name" class="chat-avatar" @error="onAvatarError($event, chat)" />
      <span v-else class="chat-initial">{{ getChatInitial(chat.name) }}</span>
    </div>
    
    <!-- Loading chats message -->
    <div v-if="chatsLoading" class="chats-loading-message">
      <p>Подгружаем чаты...</p>
    </div>
    
    <!-- Selected chat name (separate element for positioning) -->
    <p 
      v-if="selectedChat" 
      class="selected-chat-name" 
      :class="{ 'selected-chat-name-floating': chatMovingToCorner }"
    >
      {{ selectedChat.name }}
    </p>
    
    <!-- Selected chat info and Next button -->
    <div 
      v-if="selectedChat && !showDestinationSelection" 
      class="selected-chat-panel"
    >
      <div class="selected-chat-buttons">
        <button @click="goBackToWhatsAppChats" class="btn-back" v-if="telegramCentered">
          <span class="btn-arrow">←</span>
          Назад
        </button>
        <button @click="proceedWithSelectedChat" class="btn-next">
          Далее
          <span class="btn-arrow">→</span>
        </button>
      </div>
    </div>
    
    <!-- Destination selection panel: show Telegram chats as icons -->
    <div v-if="showDestinationSelection" class="destination-selection-panel">
      <h3 class="destination-title">Выберите чат в Telegram</h3>
      
      <div class="telegram-chats-container">
        <p v-if="telegramChatsLoading" class="chats-loading-text">Загрузка чатов...</p>
        <p v-else-if="telegramChatsError" class="chats-error-text">
          {{ telegramChatsError }}
          <button @click="loadTelegramChats" class="chats-retry-btn">Повторить</button>
        </p>
        <div v-else-if="telegramChats.length > 0" class="telegram-chats-list">
          <button
            v-for="tgChat in telegramChats"
            :key="tgChat.id"
            @click="selectTelegramChat(tgChat)"
            class="telegram-chat-item"
            :class="{ 'telegram-chat-selected': selectedTelegramChat?.id === tgChat.id }"
          >
            <span class="telegram-chat-initial">{{ getChatInitial(tgChat.name) }}</span>
            <span class="telegram-chat-name">{{ tgChat.name }}</span>
          </button>
        </div>
        <p v-else class="chats-empty-text">Чаты не найдены</p>
      </div>
      
      <!-- Start migration button -->
      <button 
        @click="startDataMigration" 
        class="btn-start-migration"
        :disabled="!canStartMigration"
      >
        Начать перенос
        <span class="btn-arrow">→</span>
      </button>
    </div>
    
    <div class="planet planet-tg" ref="planetTg" :style="{ boxShadow: tgBoxShadow }" :class="{ 
      'planet-tg-exiting': hideStage >= 6 && tgPhase === 'hidden',
      'planet-tg-centered': telegramCentered && !telegramShrunk,
      'planet-tg-shrunk': telegramShrunk
    }">
      <img src="https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg" class="planet-logo" :class="{ 'logo-pulsing': tgLoading }" alt="Telegram Planet" />
      
      <!-- Telegram auth overlay -->
      <div v-if="tgPhase !== 'hidden'" class="tg-overlay" :class="{ 'overlay-visible': tgPhase === 'phone' || tgPhase === 'code' || tgPhase === 'password' }">
        <!-- Phone input -->
        <div v-if="tgPhase === 'phone'" class="tg-auth-form">
          <p class="tg-auth-title">Введите номер телефона</p>
          <input 
            v-model="tgPhone" 
            type="tel" 
            placeholder="+7 999 123 45 67"
            class="tg-input"
            @keyup.enter="sendTelegramCode"
          />
          <button @click="sendTelegramCode" class="tg-btn" :disabled="tgLoading || !tgPhone">
            {{ tgLoading ? 'Отправка...' : 'Получить код' }}
          </button>
        </div>
        
        <!-- Code input -->
        <div v-else-if="tgPhase === 'code'" class="tg-auth-form">
          <p class="tg-auth-title">Введите код из Telegram</p>
          <input 
            v-model="tgCode" 
            type="text" 
            placeholder="12345"
            class="tg-input tg-input-code"
            maxlength="6"
            @keyup.enter="verifyTelegramCode"
          />
          <button @click="verifyTelegramCode" class="tg-btn" :disabled="tgLoading || !tgCode">
            {{ tgLoading ? 'Проверка...' : 'Подтвердить' }}
          </button>
        </div>
        
        <!-- Password input (2FA) -->
        <div v-else-if="tgPhase === 'password'" class="tg-auth-form">
          <p class="tg-auth-title">Введите пароль 2FA</p>
          <input 
            v-model="tgPassword" 
            type="password" 
            placeholder="Пароль"
            class="tg-input"
            @keyup.enter="verifyTelegramPassword"
          />
          <button @click="verifyTelegramPassword" class="tg-btn" :disabled="tgLoading || !tgPassword">
            {{ tgLoading ? 'Проверка...' : 'Подтвердить' }}
          </button>
        </div>
        
        <!-- Connected state -->
        <div v-else-if="tgPhase === 'connected'" class="tg-connected">
          <span class="tg-success-icon">✓</span>
          <p class="tg-connected-text">Подключено!</p>
        </div>
        
        <!-- Error -->
        <p v-if="tgError" class="tg-error">{{ tgError }}</p>
      </div>
    </div>

    <div class="content-wrapper" :class="{ 'fade-out': migrationStarted }">
      <div class="badge" :class="{ 'element-hidden': hideStage >= 2 }">TETRAKOM</div>
      <h1 class="title" :class="{ 'element-hidden': hideStage >= 3 }">Миграция чатов</h1>
      <p class="description" :class="{ 'element-hidden': hideStage >= 4 }">
        Помогу перенести ваши чаты из <strong>WhatsApp</strong> в <strong>Telegram</strong>.
        <br>
        <span class="sub-text">Потребуется разовая авторизицая в ватсапп и в телегу</span>
      </p>
      
      <button @click="startMigration" class="btn btn-launch" :class="{ 'element-hidden': hideStage >= 1 }">
        <span class="icon">🚀</span>
        Запустить перенос
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { onMounted, onUnmounted, ref, reactive, computed } from 'vue'
import api from '../api/client'
import { store } from '../store'

const router = useRouter()

// ----------------------------
// DOM refs
// ----------------------------
const planetWa = ref<HTMLElement | null>(null)
const planetTg = ref<HTMLElement | null>(null)

// ----------------------------
// Simulation state
// ----------------------------
const flightState = reactive({
  launched: false,
  dockedAt: 'wa' as 'wa' | 'tg', // where the ship is parked when not launched
})

const missionState = reactive({
  mode: 'idle' as 'idle' | 'transfer' | 'hover_tg',
  transferT: 0, // 0..1
})

const shipState = reactive({
  x: -100,
  y: -100,
  vx: 0,
  vy: 0,
  rotation: 0, 
  vRotation: 0,
  mainEngine: false,
  throttle: 0, // 0 to 1
  rcsLeft: false,
  rcsRight: false
})

let animationFrameId: number

// ----------------------------
// Visualized gravity (planet glow)
// ----------------------------
const gravityViz = reactive({
  wa: 0,
  tg: 0,
})

const waBoxShadow = ref('')
const tgBoxShadow = ref('')

// ----------------------------
// Migration animation state
// ----------------------------
const migrationStarted = ref(false)
const hideStage = ref(0) // 0-6: controls which elements are hidden
const whatsappCentered = ref(false) // true when WhatsApp planet moves to center
const showWaOverlay = ref(false) // true when overlay content should be visible
const whatsappShrunk = ref(false) // true when WhatsApp planet shrinks after connection

// ----------------------------
// WhatsApp connection state
// ----------------------------
const waStatus = ref<'idle' | 'loading' | 'qr' | 'connecting' | 'connected'>('idle')
const qrCode = ref<string | null>(null)
const waError = ref<string | null>(null)
const waSessionId = ref<string | null>(null)
let statusPollInterval: number | null = null

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

// Chat circle sizing
const CHAT_CIRCLE_SIZE = 52 // Half of shrunk planet (105/2)
const PLANET_SHRUNK_SIZE = 105
const RING_GAP = 20 // Gap between planet and first ring, and between rings

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
const telegramCentered = ref(false) // Telegram planet centered
const telegramShrunk = ref(false) // Telegram planet shrunk after auth

// ----------------------------
// Migration destination selection
// ----------------------------
const showDestinationSelection = ref(false)
const destinationType = ref<'saved' | 'existing' | 'new_group' | null>(null)
const telegramChats = ref<any[]>([])
const telegramChatsLoading = ref(false)
const telegramChatsError = ref<string | null>(null)
const selectedTelegramChat = ref<any>(null)
const newGroupName = ref('')

// ----------------------------
// Tunables (flight computer + physics)
// ----------------------------
const ENGINE_POWER = 0.3 // max thrust acceleration per frame (px/frame^2)
const ROTATION_POWER = 0.003
const ROTATION_DRAG = 0.94
const VELOCITY_DRAG = 0.99
const MAX_CONTROL_ACCEL = ENGINE_POWER * 0.2
const LANDING_ZONE_PX = 220

// Planet gravity tuning (bigger = stronger pull)
const WA_MU = 3200
const TG_MU = 5200
const GRAVITY_SOFTENING_PX = 180

// Launch behavior
const WAYPOINT_SWITCH_X_PX = 320
const IDLE_HOVER_GAP_PX = 160
const IDLE_HOVER_KP = 0.0008
const IDLE_HOVER_KD = 0.12
const PLANET_CLEARANCE_PX = 22
const SCREEN_MARGIN_PX = 16
const TRANSFER_SPEED_MIN = 0.7
const TRANSFER_SPEED_MAX = 2.2
const TRANSFER_EASE_RATE = 0.0025
const HOVER_TG_DIST_PX = 35
const HOVER_TG_SPEED = 0.6
const LAZY_MIN_TOWARD_SPEED = 0.25
const LAZY_MAX_TOWARD_SPEED = 0.55
const LAZY_Y_ERROR_ALLOW_PX = 70
const LAZY_DIST_MIN_PX = 160

// ----------------------------
// Small math helpers
// ----------------------------
function clamp01(v: number) {
  return Math.max(0, Math.min(1, v))
}

function clampMag(x: number, y: number, maxMag: number) {
  const m = Math.hypot(x, y)
  if (m <= maxMag || m === 0) return { x, y }
  const k = maxMag / m
  return { x: x * k, y: y * k }
}

function normalizeAngle(angle: number) {
  while (angle > Math.PI) angle -= Math.PI * 2
  while (angle < -Math.PI) angle += Math.PI * 2
  return angle
}

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t
}

function easeInOutCubic(t: number) {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
}

function shadowForPlanet(color: 'wa' | 'tg', glow01: number) {
  const rgb = color === 'wa' ? '37, 211, 102' : '34, 158, 217'
  const alpha = 0.25 + 0.55 * glow01
  const glowPx = 80 + 140 * glow01
  return `inset -40px -40px 0 rgba(0,0,0,0.1), 0 0 ${glowPx}px rgba(${rgb}, ${alpha})`
}

function spawnShipAboveWhatsApp() {
  if (!planetWa.value) return
  const waRect = planetWa.value.getBoundingClientRect()
  const waCenterX = waRect.left + waRect.width / 2

  shipState.x = waCenterX
  shipState.y = 24 // visible near the top with small padding
  shipState.vx = 0
  shipState.vy = 0
  shipState.vRotation = 0
  shipState.rotation = -Math.PI / 2 // Nose up
  shipState.mainEngine = false
  shipState.throttle = 0
  shipState.rcsLeft = false
  shipState.rcsRight = false
}

function onAnyLeftClick(e: MouseEvent) {
  if (e.button !== 0) return // only left click
  if (flightState.launched) return

  // Start mission from the CURRENT ship state (no teleport).
  flightState.launched = true
  missionState.mode = 'transfer'
  missionState.transferT = 0
}

// --- CAPTAIN AI & PHYSICS LOOP ---
function physicsLoop() {
  if (!planetWa.value || !planetTg.value) return

  const waRect = planetWa.value.getBoundingClientRect()
  const tgRect = planetTg.value.getBoundingClientRect()
  
  // Define Colliders
  const waCenter = { x: waRect.left + waRect.width/2, y: waRect.top + waRect.height/2 }
  const waRadius = waRect.width / 2 * 0.9 // 90% visual radius for hitbox
  
  const tgCenter = { x: tgRect.left + tgRect.width/2, y: tgRect.top + tgRect.height/2 }
  const tgRadius = tgRect.width / 2 * 0.95 // 95% visual radius
  
  const shipRadius = 25 // Approximate hitbox

  // Destination: hover above Telegram
  const tgHover = {
    x: tgCenter.x,
    y: Math.max(24, tgRect.top - IDLE_HOVER_GAP_PX),
  }

  // Guidance target:
  // - transfer: go through a height corridor, then descend to tgHover
  // - hover_tg: hold tgHover
  const cruiseAltitudeY = Math.max(80, Math.min(window.innerHeight * 0.22, 220))
  const transferFar = Math.abs(tgHover.x - shipState.x) > WAYPOINT_SWITCH_X_PX
  const guidancePos = missionState.mode === 'hover_tg'
    ? tgHover
    : { x: tgHover.x, y: transferFar ? cruiseAltitudeY : tgHover.y }

  // 2. Telemetry
  const dx = guidancePos.x - shipState.x
  const dy = guidancePos.y - shipState.y
  const speed = Math.sqrt(shipState.vx*shipState.vx + shipState.vy*shipState.vy)

  // --- GRAVITY (planetary attraction) ---
  // Acceleration is proportional to mu / (r^2 + soft^2), direction toward planet center.
  const soft2 = GRAVITY_SOFTENING_PX * GRAVITY_SOFTENING_PX

  function gravityVector(mu: number, centerX: number, centerY: number) {
    const gx = centerX - shipState.x
    const gy = centerY - shipState.y
    const r = Math.hypot(gx, gy) + 1e-6
    const r2 = gx * gx + gy * gy + soft2
    const a = mu / r2
    const ax = (gx / r) * a
    const ay = (gy / r) * a
    return { ax, ay, a }
  }

  const gWa = gravityVector(WA_MU, waCenter.x, waCenter.y)
  const gTg = gravityVector(TG_MU, tgCenter.x, tgCenter.y)

  // Visualize gravity as colored glow strength (scaled from acceleration)
  gravityViz.wa = clamp01(gWa.a * 18)
  gravityViz.tg = clamp01(gTg.a * 18)
  waBoxShadow.value = shadowForPlanet('wa', gravityViz.wa)
  tgBoxShadow.value = shadowForPlanet('tg', gravityViz.tg)

  // IDLE: captain holds a hover above WhatsApp until user clicks.
  if (!flightState.launched) {
    // Hover point: above the WhatsApp planet, aligned by X.
    // Note: Y grows downward in screen coords.
    const hoverTarget = {
      x: waCenter.x,
      y: Math.max(24, waRect.top - IDLE_HOVER_GAP_PX),
    }

    // Keep nose up; we don't use RCS while idle.
    shipState.rotation = -Math.PI / 2
    shipState.vRotation = 0
    shipState.rcsLeft = false
    shipState.rcsRight = false

    // Lock X on the WhatsApp vertical line (simple + stable).
    shipState.x = hoverTarget.x
    shipState.vx = 0

    // Vertical hover controller (PD) compensating WA gravity.
    const errY = hoverTarget.y - shipState.y
    const desiredAy = IDLE_HOVER_KP * errY + IDLE_HOVER_KD * (0 - shipState.vy)
    const thrustAyNeeded = desiredAy - gWa.ay

    // With nose up, thrustAy = -ENGINE_POWER * throttle
    const throttle = clamp01(Math.max(0, -thrustAyNeeded / ENGINE_POWER))
    const hoverThrottle = Math.min(0.7, throttle)

    shipState.throttle = hoverThrottle
    shipState.mainEngine = shipState.throttle > 0.01

    const thrustAy = Math.sin(shipState.rotation) * (ENGINE_POWER * shipState.throttle)
    shipState.vy += thrustAy + gWa.ay

    shipState.vy *= VELOCITY_DRAG
    shipState.y += shipState.vy

    animationFrameId = requestAnimationFrame(physicsLoop)
    return
  }

  // --- Mission state (transfer -> hover over Telegram) ---
  if (missionState.mode === 'transfer') {
    missionState.transferT = Math.min(1, missionState.transferT + TRANSFER_EASE_RATE)
    const distToTgHover = Math.hypot(tgHover.x - shipState.x, tgHover.y - shipState.y)
    if (distToTgHover < HOVER_TG_DIST_PX && speed < HOVER_TG_SPEED) {
      missionState.mode = 'hover_tg'
    }
  }

  // --- 3. CAPTAIN'S BRAIN (now gravity-aware) ---
  // Goal: reach target point with ~0 velocity AND land nose-up.
  // Controller: compute a desired acceleration to reduce position error and velocity error (PD),
  // then subtract gravity to get the needed engine thrust vector.

  // Desired velocity:
  // - transfer: gentle motion toward guidance target (speed ramps up smoothly)
  // - hover_tg: hold position (target speed ~0)
  const toTarget = { x: dx, y: dy }
  const dist = Math.hypot(toTarget.x, toTarget.y) + 1e-6
  const dirToTarget = { x: toTarget.x / dist, y: toTarget.y / dist }

  const transferCap = lerp(TRANSFER_SPEED_MIN, TRANSFER_SPEED_MAX, easeInOutCubic(missionState.transferT))
  const speedCap = missionState.mode === 'hover_tg' ? 0 : transferCap
  const desiredSpeed = Math.min(speedCap, dist * 0.03) // ramps down as we approach
  const vDesired = { x: dirToTarget.x * desiredSpeed, y: dirToTarget.y * desiredSpeed }

  // PD gains (tuned for per-frame integration)
  const KP = 0.0026
  const KD = 0.25

  // Acceleration command to drive (pos, vel) -> (target, desiredVel)
  let aCmd = {
    x: KP * toTarget.x + KD * (vDesired.x - shipState.vx),
    y: KP * toTarget.y + KD * (vDesired.y - shipState.vy),
  }
  aCmd = clampMag(aCmd.x, aCmd.y, MAX_CONTROL_ACCEL)

  // Gravity acceleration we will apply this frame
  const g = { x: gWa.ax + gTg.ax, y: gWa.ay + gTg.ay }

  // Required thrust acceleration (what the engine must provide)
  let aThrust = { x: aCmd.x - g.x, y: aCmd.y - g.y }
  aThrust = clampMag(aThrust.x, aThrust.y, MAX_CONTROL_ACCEL)

  // In the landing zone we force a near-vertical attitude (nose up), allowing a small tilt for x-correction.
  const landingBlend = clamp01((LANDING_ZONE_PX - dist) / LANDING_ZONE_PX)
  const noseUp = -Math.PI / 2
  const maxTilt = 0.35
  const tilt = Math.max(-maxTilt, Math.min(maxTilt, (toTarget.x / 500) * maxTilt))
  const desiredRotationLanding = noseUp + tilt

  // Default: point nose along thrust vector (engine pushes toward nose direction)
  let desiredRotation = Math.atan2(aThrust.y, aThrust.x)
  if (landingBlend > 0) {
    // Blend toward nose-up landing orientation
    const angleErr = normalizeAngle(desiredRotationLanding - desiredRotation)
    desiredRotation = normalizeAngle(desiredRotation + angleErr * landingBlend)
  }

  // Throttle needed to achieve thrust along current nose direction (project onto nose)
  const noseDir = { x: Math.cos(shipState.rotation), y: Math.sin(shipState.rotation) }
  const neededAlongNose = aThrust.x * noseDir.x + aThrust.y * noseDir.y
  let desiredThrottle = clamp01(neededAlongNose / ENGINE_POWER)

  // "Lazy acceleration": if we're already moving toward the target at a calm speed,
  // keep engines off and let inertia do the work.
  // (Never apply this in hover mode — we must hold position there.)
  const vToward = shipState.vx * dirToTarget.x + shipState.vy * dirToTarget.y
  const yErr = Math.abs(toTarget.y)
  const isCalmTransfer =
    missionState.mode === 'transfer' &&
    dist > LAZY_DIST_MIN_PX &&
    yErr < LAZY_Y_ERROR_ALLOW_PX &&
    vToward >= LAZY_MIN_TOWARD_SPEED &&
    vToward <= LAZY_MAX_TOWARD_SPEED

  if (isCalmTransfer) {
    desiredThrottle = 0
  }

  // --- 4. ROTATION VIA RCS ---
  const rotationError = normalizeAngle(desiredRotation - shipState.rotation)
  shipState.rcsLeft = false
  shipState.rcsRight = false

  if (rotationError > 0.05) {
    // Need to rotate right (clockwise) -> activate left RCS
    shipState.rcsLeft = true
    shipState.vRotation += ROTATION_POWER
  } else if (rotationError < -0.05) {
    // Need to rotate left (counter-clockwise) -> activate right RCS
    shipState.rcsRight = true
    shipState.vRotation -= ROTATION_POWER
  } else {
    shipState.vRotation *= 0.8
  }

  // --- 5. THRUST ---
  const aligned = Math.abs(rotationError) < 0.25
  shipState.throttle = aligned ? desiredThrottle : 0
  shipState.mainEngine = shipState.throttle > 0.01

  const thrustAx = Math.cos(shipState.rotation) * (ENGINE_POWER * shipState.throttle)
  const thrustAy = Math.sin(shipState.rotation) * (ENGINE_POWER * shipState.throttle)

  // Apply accelerations (thrust + gravity)
  shipState.vx += thrustAx + g.x
  shipState.vy += thrustAy + g.y

  // 6. PHYSICS INTEGRATION
  shipState.vx *= VELOCITY_DRAG
  shipState.vy *= VELOCITY_DRAG
  shipState.vRotation *= ROTATION_DRAG
  
  shipState.x += shipState.vx
  shipState.y += shipState.vy
  shipState.rotation += shipState.vRotation

  // 7. Constraints: captain must NOT allow touching planets or leaving the screen.
  const w = window.innerWidth
  const h = window.innerHeight

  // 7.1 Screen bounds (invisible walls)
  if (shipState.x < SCREEN_MARGIN_PX) {
    shipState.x = SCREEN_MARGIN_PX
    shipState.vx = Math.max(0, shipState.vx)
  } else if (shipState.x > w - SCREEN_MARGIN_PX) {
    shipState.x = w - SCREEN_MARGIN_PX
    shipState.vx = Math.min(0, shipState.vx)
  }
  if (shipState.y < SCREEN_MARGIN_PX) {
    shipState.y = SCREEN_MARGIN_PX
    shipState.vy = Math.max(0, shipState.vy)
  } else if (shipState.y > h - SCREEN_MARGIN_PX) {
    shipState.y = h - SCREEN_MARGIN_PX
    shipState.vy = Math.min(0, shipState.vy)
  }

  // 7.2 Planet clearance (project ship outside with a buffer)
  function projectOut(centerX: number, centerY: number, radius: number) {
    const minDist = radius + shipRadius + PLANET_CLEARANCE_PX
    const rx = shipState.x - centerX
    const ry = shipState.y - centerY
    const d = Math.hypot(rx, ry) + 1e-6
    if (d < minDist) {
      const nx = rx / d
      const ny = ry / d
      shipState.x = centerX + nx * minDist
      shipState.y = centerY + ny * minDist
      const vDot = shipState.vx * nx + shipState.vy * ny
      if (vDot < 0) {
        shipState.vx -= vDot * nx
        shipState.vy -= vDot * ny
      }
    }
  }

  projectOut(waCenter.x, waCenter.y, waRadius)
  projectOut(tgCenter.x, tgCenter.y, tgRadius)

  // Stop physics loop if rocket is hidden
  if (hideStage.value >= 5) {
    return
  }

  animationFrameId = requestAnimationFrame(physicsLoop)
}

// --- STARS ---
const stars = ref<{x: number, y: number, size: number, opacity: number, duration: number, delay: number}[]>([])

function generateStars() {
  const count = 50
  const newStars = []
  for (let i = 0; i < count; i++) {
    newStars.push({
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: Math.random() * 3 + 1,
      opacity: Math.random() * 0.7 + 0.1,
      duration: Math.random() * 3 + 2,
      delay: Math.random() * 5
    })
  }
  stars.value = newStars
}

async function startMigration() {
  if (migrationStarted.value) return
  
  migrationStarted.value = true
  
  // Animate elements out one by one with delays
  // Order: button -> badge -> title -> description -> rocket -> telegram planet
  const delays = [0, 25, 45, 60, 70, 75, 77] // ms between each stage
  
  for (let i = 1; i <= 6; i++) {
    await new Promise(resolve => setTimeout(resolve, delays[i - 1]))
    hideStage.value = i
  }
  
  // After all elements hidden, animate WhatsApp planet to center
  await new Promise(resolve => setTimeout(resolve, 200))
  whatsappCentered.value = true
  
  // Wait for planet animation to complete, then show overlay and start connection
  await new Promise(resolve => setTimeout(resolve, 1000))
  showWaOverlay.value = true
  await startWhatsAppConnection()
}

// ----------------------------
// WhatsApp Connection Logic
// ----------------------------
async function startWhatsAppConnection() {
  waStatus.value = 'loading'
  waError.value = null
  qrCode.value = null
  
  try {
    // Try to reuse existing session first
    const sessionsResponse = await api.get('/whatsapp/sessions')
    const sessions = sessionsResponse.data.sessions || []
    
    if (sessions.length > 0) {
      const lastSessionId = sessions[sessions.length - 1]
      try {
        const reuseResponse = await api.post(`/whatsapp/sessions/${lastSessionId}/reuse`)
        if (reuseResponse.data.reused && reuseResponse.data.status === 'ready') {
          waSessionId.value = lastSessionId
          store.setWhatsAppSessionId(lastSessionId)
          waStatus.value = 'connected'
          await onWhatsAppConnected()
          return
        }
      } catch (e) {
        // Session reuse failed, continue with new connection
      }
    }
    
    // Start new connection
    const response = await api.post('/whatsapp/connect')
    waSessionId.value = response.data.session_id
    store.setWhatsAppSessionId(response.data.session_id)
    
    if (response.data.qr_code) {
      qrCode.value = response.data.qr_code
      waStatus.value = 'qr'
    }
    
    // Start polling for status updates
    startStatusPolling()
    
  } catch (err: any) {
    waError.value = err.response?.data?.detail || 'Ошибка подключения к WhatsApp'
    waStatus.value = 'idle'
  }
}

function startStatusPolling() {
  if (statusPollInterval) {
    clearInterval(statusPollInterval)
  }
  
  statusPollInterval = window.setInterval(async () => {
    if (!waSessionId.value) return
    
    try {
      const response = await api.get(`/whatsapp/status/${waSessionId.value}`)
      const status = response.data.status
      
      if (status === 'ready') {
        waStatus.value = 'connected'
        stopStatusPolling()
        // Show connected message, then shrink planet
        await onWhatsAppConnected()
      } else if (status === 'qr' && response.data.qr_code) {
        qrCode.value = response.data.qr_code
        waStatus.value = 'qr'
      } else if (status === 'connecting') {
        waStatus.value = 'connecting'
      } else if (status === 'failed') {
        waError.value = response.data.error || 'Подключение не удалось'
        stopStatusPolling()
      }
    } catch (err) {
      // Ignore polling errors
    }
  }, 2000)
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

async function onWhatsAppConnected() {
  // Wait 1 second to show the "Connected" message
  await new Promise(resolve => setTimeout(resolve, 1000))
  
  // Hide overlay content before shrinking
  showWaOverlay.value = false
  
  // Wait for overlay to fade out
  await new Promise(resolve => setTimeout(resolve, 300))
  
  // Shrink the planet
  whatsappShrunk.value = true
  
  // Wait for shrink animation to complete
  await new Promise(resolve => setTimeout(resolve, 1000))
  
  // Start loading chats
  await loadChats()
}

async function loadChats() {
  chatsLoading.value = true
  
  try {
    const response = await api.get(`/whatsapp/chats/${waSessionId.value}`)
    const chatList = response.data.chats || []
    
    // Prepare chats with visibility flag
    chats.value = chatList.map((chat: any) => ({
      id: chat.id || chat.name,
      name: chat.name,
      avatar: chat.avatar || null,
      visible: false
    }))
    
    chatsLoading.value = false
    
    // Animate chats appearing one by one
    await animateChatsAppearing()
    
  } catch (err: any) {
    chatsLoading.value = false
    waError.value = err.response?.data?.detail || 'Ошибка загрузки чатов'
  }
}

async function animateChatsAppearing() {
  for (let i = 0; i < chats.value.length; i++) {
    const chat = { ...chats.value[i], visible: true }
    visibleChats.value.push(chat)
    
    // Delay between each chat appearing (faster for more chats)
    const delay = Math.max(30, 150 - chats.value.length * 2)
    await new Promise(resolve => setTimeout(resolve, delay))
  }
}

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
  
  // Calculate angle (clockwise from top)
  const totalInRing = getChatsPerRing(ringIndex)
  const angleStep = (2 * Math.PI) / totalInRing
  const angle = -Math.PI / 2 + positionInRing * angleStep // Start from top (-90°)
  
  // Calculate radius for this ring
  const baseRadius = PLANET_SHRUNK_SIZE / 2 + RING_GAP + CHAT_CIRCLE_SIZE / 2
  const ringRadius = baseRadius + ringIndex * (CHAT_CIRCLE_SIZE + RING_GAP)
  
  // Calculate position (center of screen)
  const centerX = window.innerWidth / 2
  const centerY = window.innerHeight / 2
  
  const x = centerX + Math.cos(angle) * ringRadius - CHAT_CIRCLE_SIZE / 2
  const y = centerY + Math.sin(angle) * ringRadius - CHAT_CIRCLE_SIZE / 2
  
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
  const baseRadius = PLANET_SHRUNK_SIZE / 2 + RING_GAP + CHAT_CIRCLE_SIZE / 2
  const ringRadius = baseRadius + ringIndex * (CHAT_CIRCLE_SIZE + RING_GAP)
  const circumference = 2 * Math.PI * ringRadius
  
  // How many circles fit with some spacing
  return Math.floor(circumference / (CHAT_CIRCLE_SIZE + 8))
}

function getChatInitial(name: string): string {
  if (!name) return '?'
  return name.charAt(0).toUpperCase()
}

function selectChat(chat: Chat) {
  // Toggle selection - click again to deselect
  if (selectedChat.value?.id === chat.id) {
    selectedChat.value = null
  } else {
    selectedChat.value = chat
  }
}

async function proceedWithSelectedChat() {
  if (!selectedChat.value) return
  
  // Store selected chat for migration
  store.setSelectedWhatsAppChats([selectedChat.value.id])
  
  // Move selected chat to top-left corner
  chatMovingToCorner.value = true
  
  // Start WhatsApp planet move to corner
  whatsappInCorner.value = true
  
  // Start Telegram planet centering
  telegramCentered.value = true
  tgPhase.value = 'entering'
  
  // Hide other chat circles (keep selected chat visible)
  if (selectedChat.value) {
    visibleChats.value = visibleChats.value.filter(chat => chat.id === selectedChat.value?.id)
  }
  
  // Wait for Telegram planet animation
  await new Promise(resolve => setTimeout(resolve, 800))
  
  // Generate session ID for Telegram
  tgSessionId.value = `tg_${Date.now()}_${Math.random().toString(36).substring(7)}`
  
  // Show phone input
  tgPhase.value = 'phone'
}

async function goBackToWhatsAppChats() {
  // Hide Telegram planet and reset Telegram state
  telegramCentered.value = false
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
  newGroupName.value = ''
  
  // Reset chat moving state
  chatMovingToCorner.value = false
  
  // Wait for Telegram planet to hide
  await new Promise(resolve => setTimeout(resolve, 500))
  
  // Return WhatsApp planet from corner to center (shrunk state)
  whatsappInCorner.value = false
  
  // Wait for animation
  await new Promise(resolve => setTimeout(resolve, 500))
  
  // Restore WhatsApp chats visibility
  visibleChats.value = chats.value.map(chat => ({ ...chat, visible: true }))
  
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
  } catch (err: any) {
    tgError.value = err.response?.data?.detail || 'Ошибка отправки кода'
  } finally {
    tgLoading.value = false
  }
}

async function verifyTelegramCode() {
  if (!tgCode.value || !tgSessionId.value || !tgPhoneCodeHash.value) return
  
  tgLoading.value = true
  tgError.value = null
  
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
    
    // Wait to show success
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // Shrink Telegram planet
    await onTelegramConnected()
    
  } catch (err: any) {
    const errorDetail = err.response?.data?.detail || ''
    if (errorDetail.includes('2FA') || errorDetail.includes('password')) {
      // Switch to password input
      tgPhase.value = 'password'
      tgError.value = 'Требуется пароль 2FA'
    } else {
      tgError.value = errorDetail || 'Неверный код'
    }
  } finally {
    tgLoading.value = false
  }
}

async function verifyTelegramPassword() {
  if (!tgPassword.value || !tgSessionId.value || !tgPhoneCodeHash.value) return
  
  tgLoading.value = true
  tgError.value = null
  
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
    
    // Wait to show success
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // Shrink Telegram planet
    await onTelegramConnected()
    
  } catch (err: any) {
    tgError.value = err.response?.data?.detail || 'Неверный пароль'
  } finally {
    tgLoading.value = false
  }
}

async function onTelegramConnected() {
  // Shrink Telegram planet
  telegramShrunk.value = true
  
  // Wait for animation
  await new Promise(resolve => setTimeout(resolve, 800))
  
  // Show destination selection (Telegram chats)
  showDestinationSelection.value = true

  // Auto-load Telegram chats list
  await loadTelegramChats()
}

async function loadTelegramChats() {
  if (!tgUserInfo.value?.id) {
    console.error('Cannot load Telegram chats: user_id is missing', tgUserInfo.value)
    telegramChatsError.value = 'Ошибка: не найден ID пользователя Telegram'
    return
  }
  
  telegramChatsLoading.value = true
  telegramChats.value = []
  telegramChatsError.value = null
  
  try {
    console.log('Loading Telegram chats for user_id:', tgUserInfo.value.id)
    const response = await api.post('/telegram/contacts', {
      user_id: tgUserInfo.value.id
    })
    
    console.log('Telegram chats response:', response.data)
    telegramChats.value = response.data.contacts || []
    
    if (telegramChats.value.length === 0) {
      console.warn('No Telegram chats found')
    } else {
      console.log(`Loaded ${telegramChats.value.length} Telegram chats`)
    }
  } catch (err: any) {
    console.error('Error loading Telegram chats:', err)
    const errorMessage = err.response?.data?.detail || err.message || 'Ошибка загрузки чатов'
    telegramChatsError.value = errorMessage
  } finally {
    telegramChatsLoading.value = false
  }
}

function selectTelegramChat(chat: any) {
  selectedTelegramChat.value = chat
}

const canStartMigration = computed(() => {
  return selectedTelegramChat.value !== null
})

async function startDataMigration() {
  if (!canStartMigration.value || !selectedChat.value) return
  
  // TODO: Start actual migration
  console.log('Starting migration:', {
    whatsappChat: selectedChat.value,
    telegramChat: selectedTelegramChat.value,
  })
}

function onAvatarError(event: Event, chat: Chat) {
  // If avatar fails to load, hide it and show initial instead
  const img = event.target as HTMLImageElement
  img.style.display = 'none'
  chat.avatar = null
}

onMounted(() => {
  generateStars()
  flightState.launched = false
  flightState.dockedAt = 'wa'
  window.addEventListener('mousedown', onAnyLeftClick)
  // Start visible near the top, aligned to WhatsApp. It will hover until user clicks.
  spawnShipAboveWhatsApp()
  physicsLoop()
})

onUnmounted(() => {
  window.removeEventListener('mousedown', onAnyLeftClick)
  cancelAnimationFrame(animationFrameId)
  stopStatusPolling()
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
  display: flex;
  justify-content: center;
  align-items: center;
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

/* Content Layout */
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
  margin-top: 2rem;
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

.icon {
  font-size: 1.5rem;
}

/* Cosmic Decorations - STATIC NOW */
.planet {
  position: absolute;
  border-radius: 50%;
  z-index: 6;
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
  bottom: -40px;
  left: -40px;
  top: auto;
  box-shadow: inset -40px -40px 0 rgba(0,0,0,0.1), 0 0 80px rgba(37, 211, 102, 0.5);
  z-index: 20;
  transition: all 1s ease-in-out;
}

/* WhatsApp planet centered state */
.planet-wa-centered {
  width: 500px;
  height: 500px;
  bottom: 50% !important;
  left: 50% !important;
  transform: translate(-50%, 50%);
  box-shadow: inset -70px -70px 0 rgba(0,0,0,0.1), 0 0 150px rgba(37, 211, 102, 0.6);
}

.planet-wa-centered .planet-logo {
  opacity: 0.03;
  transition: opacity 1s ease-in-out;
}

/* WhatsApp planet shrunk state (after connection) */
.planet-wa-shrunk {
  width: 105px;
  height: 105px;
  bottom: 50% !important;
  left: 50% !important;
  transform: translate(-50%, 50%);
  box-shadow: inset -15px -15px 0 rgba(0,0,0,0.1), 0 0 40px rgba(37, 211, 102, 0.5);
  z-index: 10 !important; /* Lower than chat circles (z-index: 15) */
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
  bottom: -40px;
  right: -40px;
  left: auto;
  top: auto;
  box-shadow: inset -40px -40px 0 rgba(0,0,0,0.1), 0 0 80px rgba(34, 158, 217, 0.5);
  z-index: 20;
  transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1),
              height 0.5s cubic-bezier(0.4, 0, 0.2, 1),
              transform 0.5s cubic-bezier(0.4, 0, 0.2, 1),
              box-shadow 0.5s cubic-bezier(0.4, 0, 0.2, 1);
  transform: translate(0, 0);
  transform-origin: center center;
}

/* Telegram planet centered state */
.planet-tg-centered {
  width: 500px !important;
  height: 500px !important;
  bottom: -40px !important;
  right: -40px !important;
  left: auto !important;
  top: auto !important;
  transform: translate(calc(-50vw + 250px - 40px), calc(-50vh + 250px - 40px)) !important;
  box-shadow: inset -70px -70px 0 rgba(0,0,0,0.1), 0 0 150px rgba(34, 158, 217, 0.6) !important;
  z-index: 20;
  transition: width 1s cubic-bezier(0.25, 0.46, 0.45, 0.94),
              height 1s cubic-bezier(0.25, 0.46, 0.45, 0.94),
              transform 1s cubic-bezier(0.25, 0.46, 0.45, 0.94),
              box-shadow 1s cubic-bezier(0.25, 0.46, 0.45, 0.94) !important;
}

.planet-tg-centered .planet-logo {
  opacity: 0.15;
  transition: opacity 0.8s ease-in-out;
}

/* Telegram planet shrunk state */
.planet-tg-shrunk {
  width: 70px;
  height: 70px;
  bottom: auto !important;
  right: 30px !important;
  left: auto !important;
  top: 30px !important;
  transform: none;
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

/* Stars */
.star {
  position: absolute;
  background: white;
  border-radius: 50%;
  animation: twinkle linear infinite;
}

@keyframes twinkle {
  0%, 100% { opacity: 0.2; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.2); }
}

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
.space-traffic {
  transition: opacity 0.4s ease-out, transform 0.4s ease-out;
}

/* When migration started, prevent interactions with content */
.content-wrapper.fade-out {
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
  color: white;
  font-size: 1.1rem;
  font-weight: 500;
  line-height: 1.5;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
  max-width: 280px;
}

.wa-qr {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.wa-qr-image {
  width: 200px;
  height: 200px;
  border-radius: 16px;
  background: white;
  padding: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.wa-qr-hint {
  color: white;
  font-size: 1rem;
  font-weight: 600;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
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

/* Chat circles */
.chat-circle {
  position: fixed;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 15;
  opacity: 0;
  transform: scale(0);
  transition: opacity 0.3s ease-out, transform 0.3s ease-out, box-shadow 0.2s ease, z-index 0s, left 0.6s cubic-bezier(0.4, 0, 0.2, 1), top 0.6s cubic-bezier(0.4, 0, 0.2, 1), width 0.6s cubic-bezier(0.4, 0, 0.2, 1), height 0.6s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
}

.chat-circle.chat-visible {
  opacity: 1;
  transform: scale(1);
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

/* Dimmed (non-selected) chats */
.chat-circle.chat-dimmed {
  opacity: 0.4 !important;
  transform: scale(0.9) !important;
  filter: grayscale(30%);
}

.chat-circle.chat-dimmed:hover {
  opacity: 0.7 !important;
  transform: scale(1) !important;
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

.selected-chat-name {
  position: fixed;
  left: 50%;
  top: calc(100vh - 13.0rem);
  transform: translateX(-50%);
  color: white;
  font-size: 1.2rem;
  font-weight: 600;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
  background: rgba(0, 0, 0, 0.3);
  padding: 8px 20px;
  border-radius: 20px;
  backdrop-filter: blur(10px);
  transition: 
    color 0.25s ease-out,
    background 0.25s ease-out,
    padding 0.25s ease-out,
    border-radius 0.25s ease-out,
    transform 0.6s cubic-bezier(0.4, 0, 0.2, 1),
    left 0.6s cubic-bezier(0.4, 0, 0.2, 1),
    top 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.selected-chat-name-floating {
  left: 90px !important;
  top: 56px !important;
  transform: translate(0, -50%) !important;
  border-radius: 999px;
  padding: 6px 16px;
  background: rgba(0, 0, 0, 0.45);
  font-size: 0.95rem;
  max-width: 220px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  z-index: 35;
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
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  z-index: 50;
  max-width: 500px;
  width: 90%;
  animation: slideUp 0.3s ease-out;
}

.destination-title {
  color: white;
  font-size: 1.5rem;
  font-weight: 700;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
  margin-bottom: 8px;
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

.telegram-chats-container {
  width: 100%;
  max-height: 300px;
  overflow-y: auto;
  margin-top: 8px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
}

.telegram-chats-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.telegram-chat-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.1);
  border: 2px solid transparent;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.telegram-chat-item:hover {
  background: rgba(255, 255, 255, 0.15);
}

.telegram-chat-item.telegram-chat-selected {
  background: rgba(34, 158, 217, 0.3);
  border-color: #229ED9;
}

.telegram-chat-initial {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 700;
  font-size: 1rem;
  flex-shrink: 0;
}

.telegram-chat-name {
  color: white;
  font-size: 1rem;
  font-weight: 500;
}

.chats-loading-text,
.chats-empty-text {
  color: rgba(255, 255, 255, 0.7);
  text-align: center;
  padding: 20px;
  font-size: 0.95rem;
}

.chats-error-text {
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
  background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
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
  box-shadow: 0 6px 20px rgba(37, 211, 102, 0.4);
  transition: all 0.2s ease;
  margin-top: 8px;
}

.btn-start-migration:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(37, 211, 102, 0.5);
}

.btn-start-migration:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .title { font-size: 2.5rem; }
  .planet-wa { width: 60px; height: 60px; left: -10px; }
  .planet-tg { width: 180px; height: 180px; right: -40px; }
}
</style>
