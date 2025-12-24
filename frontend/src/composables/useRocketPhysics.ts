import { ref, reactive, type Ref } from 'vue'
import { PHYSICS, ROCKET_UI_SIZES } from '../constants/rocketConstants'
import { clamp01, clampMag, normalizeAngle, lerp, easeInOutCubic } from '../utils/rocketUtils'

export interface ShipState {
  x: number
  y: number
  vx: number
  vy: number
  rotation: number
  vRotation: number
  mainEngine: boolean
  throttle: number
  rcsLeft: boolean
  rcsRight: boolean
}

export interface FlightState {
  launched: boolean
  dockedAt: 'wa' | 'tg'
}

export interface MissionState {
  mode: 'idle' | 'transfer' | 'hover_tg'
  transferT: number
}

export interface GravityViz {
  wa: number
  tg: number
}

export interface PlanetRefs {
  wa: Ref<HTMLElement | null>
  tg: Ref<HTMLElement | null>
}

export interface RocketPhysicsOptions {
  planetRefs: PlanetRefs
  hideStage: Ref<number>
  onGravityUpdate?: (gravityViz: GravityViz) => void
}

export function useRocketPhysics(options: RocketPhysicsOptions) {
  const { planetRefs, hideStage, onGravityUpdate } = options

  // State
  const flightState = reactive<FlightState>({
    launched: false,
    dockedAt: 'wa',
  })

  const missionState = reactive<MissionState>({
    mode: 'idle',
    transferT: 0,
  })

  const shipState = reactive<ShipState>({
    x: PHYSICS.SHIP_INITIAL_X,
    y: PHYSICS.SHIP_INITIAL_Y,
    vx: 0,
    vy: 0,
    rotation: 0,
    vRotation: 0,
    mainEngine: false,
    throttle: 0,
    rcsLeft: false,
    rcsRight: false,
  })

  const gravityViz = reactive<GravityViz>({
    wa: 0,
    tg: 0,
  })

  let animationFrameId: number | null = null

  // Constants (extracted for easier access)
  const {
    ENGINE_POWER,
    ROTATION_POWER,
    ROTATION_DRAG,
    VELOCITY_DRAG,
    MAX_CONTROL_ACCEL,
    WA_MU,
    TG_MU,
    GRAVITY_SOFTENING_PX,
    GRAVITY_VISUALIZATION_SCALE,
    WAYPOINT_SWITCH_X_PX,
    IDLE_HOVER_GAP_PX,
    IDLE_HOVER_KP,
    IDLE_HOVER_KD,
    PLANET_CLEARANCE_PX,
    SCREEN_MARGIN_PX,
    LANDING_ZONE_PX,
    TRANSFER_SPEED_MIN,
    TRANSFER_SPEED_MAX,
    TRANSFER_EASE_RATE,
    TRANSFER_SPEED_RAMP_FACTOR,
    HOVER_TG_DIST_PX,
    HOVER_TG_SPEED,
    LAZY_MIN_TOWARD_SPEED,
    LAZY_MAX_TOWARD_SPEED,
    LAZY_Y_ERROR_ALLOW_PX,
    LAZY_DIST_MIN_PX,
    ROTATION_ERROR_THRESHOLD,
    ROTATION_ALIGNED_THRESHOLD,
    HOVER_THROTTLE_MAX,
    MAX_TILT,
    TILT_FACTOR,
    SHIP_RADIUS,
    NOSE_UP_ANGLE,
  } = PHYSICS

  const { TOP_PADDING, CRUISE_ALTITUDE_MIN, CRUISE_ALTITUDE_MAX, CRUISE_ALTITUDE_RATIO } = ROCKET_UI_SIZES

  /**
   * Spawn ship above WhatsApp planet
   */
  function spawnShipAboveWhatsApp() {
    if (!planetRefs.wa.value) return
    const waRect = planetRefs.wa.value.getBoundingClientRect()
    const waCenterX = waRect.left + waRect.width / 2

    shipState.x = waCenterX
    shipState.y = TOP_PADDING
    shipState.vx = 0
    shipState.vy = 0
    shipState.vRotation = 0
    shipState.rotation = NOSE_UP_ANGLE
    shipState.mainEngine = false
    shipState.throttle = 0
    shipState.rcsLeft = false
    shipState.rcsRight = false
  }

  /**
   * Launch mission on click
   */
  function launchMission() {
    if (flightState.launched) return
    flightState.launched = true
    missionState.mode = 'transfer'
    missionState.transferT = 0
  }

  /**
   * Calculate gravity vector from a planet
   */
  function gravityVector(mu: number, centerX: number, centerY: number) {
    const gx = centerX - shipState.x
    const gy = centerY - shipState.y
    const r = Math.hypot(gx, gy) + 1e-6
    const r2 = gx * gx + gy * gy + GRAVITY_SOFTENING_PX * GRAVITY_SOFTENING_PX
    const a = mu / r2
    const ax = (gx / r) * a
    const ay = (gy / r) * a
    return { ax, ay, a }
  }

  /**
   * Project ship outside planet boundary
   */
  function projectOut(centerX: number, centerY: number, radius: number) {
    const minDist = radius + SHIP_RADIUS + PLANET_CLEARANCE_PX
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

  /**
   * Main physics loop
   */
  function physicsLoop() {
    if (!planetRefs.wa.value || !planetRefs.tg.value) return

    const waRect = planetRefs.wa.value.getBoundingClientRect()
    const tgRect = planetRefs.tg.value.getBoundingClientRect()

    // Define Colliders
    const waCenter = { x: waRect.left + waRect.width / 2, y: waRect.top + waRect.height / 2 }
    const waRadius = waRect.width / 2 * 0.9 // 90% visual radius for hitbox

    const tgCenter = { x: tgRect.left + tgRect.width / 2, y: tgRect.top + tgRect.height / 2 }
    const tgRadius = tgRect.width / 2 * 0.95 // 95% visual radius

    // Destination: hover above Telegram
    const tgHover = {
      x: tgCenter.x,
      y: Math.max(TOP_PADDING, tgRect.top - IDLE_HOVER_GAP_PX),
    }

    // Guidance target:
    // - transfer: go through a height corridor, then descend to tgHover
    // - hover_tg: hold tgHover
    const cruiseAltitudeY = Math.max(
      CRUISE_ALTITUDE_MIN,
      Math.min(window.innerHeight * CRUISE_ALTITUDE_RATIO, CRUISE_ALTITUDE_MAX)
    )
    const transferFar = Math.abs(tgHover.x - shipState.x) > WAYPOINT_SWITCH_X_PX
    const guidancePos =
      missionState.mode === 'hover_tg'
        ? tgHover
        : { x: tgHover.x, y: transferFar ? cruiseAltitudeY : tgHover.y }

    // Telemetry
    const dx = guidancePos.x - shipState.x
    const dy = guidancePos.y - shipState.y
    const speed = Math.sqrt(shipState.vx * shipState.vx + shipState.vy * shipState.vy)

    // --- GRAVITY (planetary attraction) ---
    const gWa = gravityVector(WA_MU, waCenter.x, waCenter.y)
    const gTg = gravityVector(TG_MU, tgCenter.x, tgCenter.y)

    // Visualize gravity as colored glow strength (scaled from acceleration)
    gravityViz.wa = clamp01(gWa.a * GRAVITY_VISUALIZATION_SCALE)
    gravityViz.tg = clamp01(gTg.a * GRAVITY_VISUALIZATION_SCALE)
    onGravityUpdate?.(gravityViz)

    // IDLE: captain holds a hover above WhatsApp until user clicks.
    if (!flightState.launched) {
      // Hover point: above the WhatsApp planet, aligned by X.
      const hoverTarget = {
        x: waCenter.x,
        y: Math.max(TOP_PADDING, waRect.top - IDLE_HOVER_GAP_PX),
      }

      // Keep nose up; we don't use RCS while idle.
      shipState.rotation = NOSE_UP_ANGLE
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
      const hoverThrottle = Math.min(HOVER_THROTTLE_MAX, throttle)

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

    // --- CAPTAIN'S BRAIN (now gravity-aware) ---
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
    const desiredSpeed = Math.min(speedCap, dist * TRANSFER_SPEED_RAMP_FACTOR) // ramps down as we approach
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
    const noseUp = NOSE_UP_ANGLE
    const maxTilt = MAX_TILT
    const tilt = Math.max(-maxTilt, Math.min(maxTilt, (toTarget.x / TILT_FACTOR) * maxTilt))
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

    // --- ROTATION VIA RCS ---
    const rotationError = normalizeAngle(desiredRotation - shipState.rotation)
    shipState.rcsLeft = false
    shipState.rcsRight = false

    if (rotationError > ROTATION_ERROR_THRESHOLD) {
      // Need to rotate right (clockwise) -> activate left RCS
      shipState.rcsLeft = true
      shipState.vRotation += ROTATION_POWER
    } else if (rotationError < -ROTATION_ERROR_THRESHOLD) {
      // Need to rotate left (counter-clockwise) -> activate right RCS
      shipState.rcsRight = true
      shipState.vRotation -= ROTATION_POWER
    } else {
      shipState.vRotation *= 0.8
    }

    // --- THRUST ---
    const aligned = Math.abs(rotationError) < ROTATION_ALIGNED_THRESHOLD
    shipState.throttle = aligned ? desiredThrottle : 0
    shipState.mainEngine = shipState.throttle > 0.01

    const thrustAx = Math.cos(shipState.rotation) * (ENGINE_POWER * shipState.throttle)
    const thrustAy = Math.sin(shipState.rotation) * (ENGINE_POWER * shipState.throttle)

    // Apply accelerations (thrust + gravity)
    shipState.vx += thrustAx + g.x
    shipState.vy += thrustAy + g.y

    // PHYSICS INTEGRATION
    shipState.vx *= VELOCITY_DRAG
    shipState.vy *= VELOCITY_DRAG
    shipState.vRotation *= ROTATION_DRAG

    shipState.x += shipState.vx
    shipState.y += shipState.vy
    shipState.rotation += shipState.vRotation

    // Constraints: captain must NOT allow touching planets or leaving the screen.
    const w = window.innerWidth
    const h = window.innerHeight

    // Screen bounds (invisible walls)
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

    // Planet clearance (project ship outside with a buffer)
    projectOut(waCenter.x, waCenter.y, waRadius)
    projectOut(tgCenter.x, tgCenter.y, tgRadius)

    // Stop physics loop if rocket is hidden
    if (hideStage.value >= 5) {
      return
    }

    // Only continue animation if component is still mounted
    animationFrameId = requestAnimationFrame(physicsLoop)
  }

  /**
   * Start physics loop
   */
  function startPhysics() {
    if (animationFrameId === null) {
      animationFrameId = requestAnimationFrame(physicsLoop)
    }
  }

  /**
   * Stop physics loop
   */
  function stopPhysics() {
    if (animationFrameId !== null) {
      cancelAnimationFrame(animationFrameId)
      animationFrameId = null
    }
  }

  return {
    shipState,
    flightState,
    missionState,
    gravityViz,
    spawnShipAboveWhatsApp,
    launchMission,
    startPhysics,
    stopPhysics,
  }
}

