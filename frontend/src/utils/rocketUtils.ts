/**
 * Clamp value between 0 and 1
 */
export function clamp01(v: number): number {
  return Math.max(0, Math.min(1, v))
}

/**
 * Clamp vector magnitude to maxMag
 */
export function clampMag(x: number, y: number, maxMag: number): { x: number; y: number } {
  const m = Math.hypot(x, y)
  if (m <= maxMag || m === 0) return { x, y }
  const k = maxMag / m
  return { x: x * k, y: y * k }
}

/**
 * Normalize angle to [-PI, PI] range
 */
export function normalizeAngle(angle: number): number {
  let normalized = angle
  while (normalized > Math.PI) normalized -= Math.PI * 2
  while (normalized < -Math.PI) normalized += Math.PI * 2
  return normalized
}

/**
 * Linear interpolation
 */
export function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t
}

/**
 * Ease in-out cubic easing function
 */
export function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
}

/**
 * Generate box shadow for planet based on gravity visualization
 */
export function shadowForPlanet(color: 'wa' | 'tg', glow01: number, planetVisual: typeof import('../constants/rocketConstants').PLANET_VISUAL): string {
  const rgb = color === 'wa' ? planetVisual.WA_COLOR_RGB : planetVisual.TG_COLOR_RGB
  const alpha = planetVisual.GLOW_ALPHA_MIN + (planetVisual.GLOW_ALPHA_MAX - planetVisual.GLOW_ALPHA_MIN) * glow01
  const glowPx = planetVisual.GLOW_SIZE_MIN + (planetVisual.GLOW_SIZE_MAX - planetVisual.GLOW_SIZE_MIN) * glow01
  return `inset ${planetVisual.INSET_SHADOW}px ${planetVisual.INSET_SHADOW}px 0 rgba(0,0,0,0.1), 0 0 ${glowPx}px rgba(${rgb}, ${alpha})`
}

