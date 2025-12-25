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
  messagesLoading?: Ref<boolean>
}

export function useRocketPhysics(options: RocketPhysicsOptions) {
  const { planetRefs, hideStage, onGravityUpdate, messagesLoading } = options

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
   * Spawn ship above screen (off-screen at top)
   */
  function spawnShipAboveWhatsApp() {
    // Position rocket above screen, at center horizontally
    const centerX = window.innerWidth / 2
    const offScreenY = -50 // Above the top edge of screen, slightly lower

    shipState.x = centerX
    shipState.y = offScreenY
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
   * @param targetPlanet - 'wa' for WhatsApp, 'tg' for Telegram
   */
  function launchMission(targetPlanet: 'wa' | 'tg' = 'tg') {
    if (flightState.launched) return
    flightState.launched = true
    flightState.dockedAt = targetPlanet
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
    // Use full radius for collision detection to ensure no penetration
    const waRadius = waRect.width / 2

    const tgCenter = { x: tgRect.left + tgRect.width / 2, y: tgRect.top + tgRect.height / 2 }
    // Use full radius for collision detection to ensure no penetration
    const tgRadius = tgRect.width / 2

    // --- Mission state management (BEFORE calculating target) ---
    // Priority: messages loading > planet hover
    // If messages are loading and we're at WhatsApp, ALWAYS go to bottom left corner
    // This must happen BEFORE calculating targetHover so the target is correct
    // CRITICAL: This check must happen regardless of current mode to force transition
    if (messagesLoading?.value && flightState.dockedAt === 'wa' && flightState.launched) {
      // Calculate distance to bottom left target
      const bottomLeftX = window.innerWidth * 0.25
      const bottomLeftY = window.innerHeight - 32
      const distToBottomLeft = Math.hypot(bottomLeftX - shipState.x, bottomLeftY - shipState.y)
      
      // ALWAYS switch to transfer mode if not already close to target
      // This works regardless of current mode (hover_tg or transfer) - force the transition
      if (distToBottomLeft > HOVER_TG_DIST_PX) {
        // Need to fly to bottom left - FORCE switch to transfer mode
        missionState.mode = 'transfer'
        missionState.transferT = 0
      } else {
        // Already close to bottom left - switch to hover mode to stay there
        missionState.mode = 'hover_tg'
      }
    }

    // Destination: if messages are loading, go to bottom left corner (left of search)
    // Otherwise, hover above target planet (based on flightState.dockedAt)
    let targetHover: { x: number; y: number }
    
    if (messagesLoading?.value && flightState.dockedAt === 'wa' && flightState.launched) {
      // Bottom left corner, left of search (search is centered at 50%, so left is at ~25% of screen width)
      // Search container is in left section (WhatsApp section), so we position left of it
      const searchLeftX = window.innerWidth * 0.25 // 25% from left edge (left of centered search)
      const searchBottomY = window.innerHeight - 32 // 2rem = 32px from bottom (same as search)
      targetHover = {
        x: searchLeftX,
        y: searchBottomY,
      }
    } else {
      const targetPlanet = flightState.dockedAt
      const targetCenter = targetPlanet === 'wa' ? waCenter : tgCenter
      const targetRect = targetPlanet === 'wa' ? waRect : tgRect
      
      targetHover = {
        x: targetCenter.x,
        y: Math.max(TOP_PADDING, targetRect.top - IDLE_HOVER_GAP_PX),
      }
    }

    // Guidance target:
    // - transfer: go through a height corridor, then descend to targetHover
    // - hover: hold targetHover
    const cruiseAltitudeY = Math.max(
      CRUISE_ALTITUDE_MIN,
      Math.min(window.innerHeight * CRUISE_ALTITUDE_RATIO, CRUISE_ALTITUDE_MAX)
    )
    const transferFar = Math.abs(targetHover.x - shipState.x) > WAYPOINT_SWITCH_X_PX
    const hoverMode = missionState.mode === 'hover_tg'
    const guidancePos =
      hoverMode
        ? targetHover
        : { x: targetHover.x, y: transferFar ? cruiseAltitudeY : targetHover.y }

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

    // IDLE: rocket drifts down under gravity until user clicks.
    if (!flightState.launched) {
      // Keep nose up; we don't use RCS while idle.
      shipState.rotation = NOSE_UP_ANGLE
      shipState.vRotation = 0
      shipState.rcsLeft = false
      shipState.rcsRight = false

      // No active control - just let gravity pull the rocket down
      // Rocket will drift naturally between planets
      shipState.throttle = 0
      shipState.mainEngine = false

      // Apply only gravity (no thrust)
      const gTotal = { x: gWa.ax + gTg.ax, y: gWa.ay + gTg.ay }
      
      shipState.vx += gTotal.x
      shipState.vy += gTotal.y

      shipState.vx *= VELOCITY_DRAG
      shipState.vy *= VELOCITY_DRAG
      shipState.x += shipState.vx
      shipState.y += shipState.vy

      animationFrameId = requestAnimationFrame(physicsLoop)
      return
    }

    // --- Mission state (transfer -> hover over target) ---
    if (missionState.mode === 'transfer') {
      missionState.transferT = Math.min(1, missionState.transferT + TRANSFER_EASE_RATE)
      const distToTargetHover = Math.hypot(targetHover.x - shipState.x, targetHover.y - shipState.y)
      // Switch to hover mode when close to target (regardless of messagesLoading state)
      // The target is already set correctly above based on messagesLoading
      if (distToTargetHover < HOVER_TG_DIST_PX && speed < HOVER_TG_SPEED) {
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

    // --- COLLISION AVOIDANCE (captain's collision detection) ---
    // Check distance to both planets and add avoidance acceleration if too close
    const minSafeDistWA = waRadius + SHIP_RADIUS + PLANET_CLEARANCE_PX
    const distToWA = Math.hypot(shipState.x - waCenter.x, shipState.y - waCenter.y)
    let isNearPlanet = false
    let criticalCollisionRisk = false
    
    if (distToWA < minSafeDistWA) {
      isNearPlanet = true
      // Critical risk if very close (within half of clearance zone)
      criticalCollisionRisk = (minSafeDistWA - distToWA) > (PLANET_CLEARANCE_PX * 0.5)
      
      // Too close to WhatsApp planet - add avoidance acceleration
      const dirFromWA = {
        x: (shipState.x - waCenter.x) / (distToWA + 1e-6),
        y: (shipState.y - waCenter.y) / (distToWA + 1e-6)
      }
      // Avoidance strength increases as we get closer (inverse distance)
      // Use ENGINE_POWER for critical situations to ensure we have enough thrust
      const avoidanceStrength = Math.min(1.0, (minSafeDistWA - distToWA) / PLANET_CLEARANCE_PX)
      const avoidanceAccel = criticalCollisionRisk 
        ? ENGINE_POWER * avoidanceStrength  // Full power in critical situations
        : MAX_CONTROL_ACCEL * avoidanceStrength
      aCmd.x += dirFromWA.x * avoidanceAccel
      aCmd.y += dirFromWA.y * avoidanceAccel
    }

    const minSafeDistTG = tgRadius + SHIP_RADIUS + PLANET_CLEARANCE_PX
    const distToTG = Math.hypot(shipState.x - tgCenter.x, shipState.y - tgCenter.y)
    if (distToTG < minSafeDistTG) {
      isNearPlanet = true
      // Critical risk if very close
      if (!criticalCollisionRisk) {
        criticalCollisionRisk = (minSafeDistTG - distToTG) > (PLANET_CLEARANCE_PX * 0.5)
      }
      
      // Too close to Telegram planet - add avoidance acceleration
      const dirFromTG = {
        x: (shipState.x - tgCenter.x) / (distToTG + 1e-6),
        y: (shipState.y - tgCenter.y) / (distToTG + 1e-6)
      }
      // Avoidance strength increases as we get closer (inverse distance)
      const avoidanceStrength = Math.min(1.0, (minSafeDistTG - distToTG) / PLANET_CLEARANCE_PX)
      const avoidanceAccel = criticalCollisionRisk
        ? ENGINE_POWER * avoidanceStrength  // Full power in critical situations
        : MAX_CONTROL_ACCEL * avoidanceStrength
      aCmd.x += dirFromTG.x * avoidanceAccel
      aCmd.y += dirFromTG.y * avoidanceAccel
    }

    // Clamp total acceleration command (but allow up to ENGINE_POWER in critical situations)
    const maxCmdAccel = criticalCollisionRisk ? ENGINE_POWER : MAX_CONTROL_ACCEL
    aCmd = clampMag(aCmd.x, aCmd.y, maxCmdAccel)

    // Gravity acceleration we will apply this frame
    const g = { x: gWa.ax + gTg.ax, y: gWa.ay + gTg.ay }

    // Required thrust acceleration (what the engine must provide)
    // This can be up to ENGINE_POWER (the actual engine capability)
    let aThrust = { x: aCmd.x - g.x, y: aCmd.y - g.y }
    aThrust = clampMag(aThrust.x, aThrust.y, ENGINE_POWER)

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
    const desiredThrottle = clamp01(neededAlongNose / ENGINE_POWER)

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
    // In critical collision situations, allow thrust even if not perfectly aligned
    // This gives the captain emergency control authority
    const aligned = Math.abs(rotationError) < ROTATION_ALIGNED_THRESHOLD
    const allowThrustWhenMisaligned = criticalCollisionRisk && Math.abs(rotationError) < (ROTATION_ALIGNED_THRESHOLD * 2)
    shipState.throttle = (aligned || allowThrustWhenMisaligned) ? desiredThrottle : 0
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

    // Planet clearance (last resort safety net - should rarely trigger if avoidance works)
    // Only project out if we're actually inside the planet (not just close)
    const minDistWA = waRadius + SHIP_RADIUS
    const distWA = Math.hypot(shipState.x - waCenter.x, shipState.y - waCenter.y)
    if (distWA < minDistWA) {
      projectOut(waCenter.x, waCenter.y, waRadius)
    }

    const minDistTG = tgRadius + SHIP_RADIUS
    const distTG = Math.hypot(shipState.x - tgCenter.x, shipState.y - tgCenter.y)
    if (distTG < minDistTG) {
      projectOut(tgCenter.x, tgCenter.y, tgRadius)
    }

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

