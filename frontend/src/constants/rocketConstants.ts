// Physics & Flight Constants
export const PHYSICS = {
  // Engine
  ENGINE_POWER: 0.3, // max thrust acceleration per frame (px/frame^2)
  MAX_CONTROL_ACCEL_FACTOR: 0.6, // Increased from 0.2 to allow more control authority
  ROTATION_POWER: 0.003,
  ROTATION_DRAG: 0.94,
  VELOCITY_DRAG: 0.99,
  // Gravity (reduced for gentle drifting between planets)
  WA_MU: 800,  // Reduced from 3200 for gentle drift
  TG_MU: 800,  // Same as WhatsApp for balanced gravity
  GRAVITY_SOFTENING_PX: 180,
  GRAVITY_VISUALIZATION_SCALE: 18,
  // Flight behavior
  WAYPOINT_SWITCH_X_PX: 320,
  IDLE_HOVER_GAP_PX: 80, // Reduced from 160 (half the original height)
  IDLE_HOVER_KP: 0.0008,
  IDLE_HOVER_KD: 0.12,
  PLANET_CLEARANCE_PX: 25,
  SCREEN_MARGIN_PX: 16,
  LANDING_ZONE_PX: 220,
  // Transfer
  TRANSFER_SPEED_MIN: 0.7,
  TRANSFER_SPEED_MAX: 2.2,
  TRANSFER_EASE_RATE: 0.0025,
  TRANSFER_SPEED_RAMP_FACTOR: 0.03,
  // Hover
  HOVER_TG_DIST_PX: 35,
  HOVER_TG_SPEED: 0.6,
  // Control
  MAX_CONTROL_ACCEL: 0.3 * 0.2, // ENGINE_POWER * MAX_CONTROL_ACCEL_FACTOR
  ROTATION_ERROR_THRESHOLD: 0.05,
  ROTATION_ALIGNED_THRESHOLD: 0.25,
  HOVER_THROTTLE_MAX: 0.7,
  // Landing
  MAX_TILT: 0.35,
  TILT_FACTOR: 500,
  // Ship
  SHIP_RADIUS: 25,
  SHIP_INITIAL_X: -100,
  SHIP_INITIAL_Y: -100,
  NOSE_UP_ANGLE: -Math.PI / 2,
} as const

// Ship Visual Effects
export const SHIP_VISUAL = {
  SHIP_SCALE: 2.1, // 3.5 * 0.6 = 2.1
  FLAME_SCALE_HIGH: '1 1.5; 1 2.5; 1 1.5',
  FLAME_SCALE_LOW: '1 0.5; 1 0.8; 1 0.5',
  FLAME_THROTTLE_THRESHOLD: 0.5,
  FLAME_ANIMATION_DURATION: '0.05s',
  FLAME_TRANSFORM_DURATION: '0.1s',
  RCS_ANIMATION_DURATION: '0.05s',
} as const

// UI Sizes related to rocket
export const ROCKET_UI_SIZES = {
  TOP_PADDING: 24,
  CRUISE_ALTITUDE_MIN: 80,
  CRUISE_ALTITUDE_MAX: 220,
  CRUISE_ALTITUDE_RATIO: 0.22,
} as const

// Planet Visual Effects
export const PLANET_VISUAL = {
  WA_COLOR_RGB: '37, 211, 102',
  TG_COLOR_RGB: '34, 158, 217',
  GLOW_ALPHA_MIN: 0.25,
  GLOW_ALPHA_MAX: 0.8, // 0.25 + 0.55
  GLOW_SIZE_MIN: 80,
  GLOW_SIZE_MAX: 220, // 80 + 140
  INSET_SHADOW: -40,
} as const

