// Animation & Timing
export const ANIMATION = {
  // Migration sequence delays (ms)
  MIGRATION_DELAYS: [0, 25, 45, 60, 70, 75, 77] as const,
  // General delays
  PLANET_CENTER_DELAY: 200,
  PLANET_SHRINK_DELAY: 1000,
  OVERLAY_FADE_DELAY: 300,
  CONNECTED_MESSAGE_DELAY: 1000,
  TELEGRAM_CENTER_DELAY: 800,
  CORNER_ANIMATION_DELAY: 500,
  // Chat animation
  CHAT_APPEAR_DELAY: 50, // ms between each chat appearing (smooth but fast)
  CHAT_ANIMATION_MIN_DELAY: 30,
  CHAT_ANIMATION_BASE_DELAY: 150,
  CHAT_ANIMATION_DELAY_FACTOR: 2,
  // Scroll delays
  SCROLL_DELAY: 100,
  LOGS_SCROLL_DELAY: 100,
} as const

// Messages Configuration
export const MESSAGES = {
  INITIAL_LIMIT: 3, // Start with 3 messages
  FUZZY_MATCH_THRESHOLD: 0.7,
} as const

// Polling & Intervals
export const POLLING = {
  STATUS_POLL_INTERVAL: 2000, // ms
} as const

