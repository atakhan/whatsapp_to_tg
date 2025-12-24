import { ref } from 'vue'
import { STARS_CONFIG } from '../constants/starsConstants'

export interface Star {
  x: number
  y: number
  size: number
  opacity: number
  duration: number
  delay: number
}

/**
 * Composable for generating and managing stars
 */
export function useStars() {
  const stars = ref<Star[]>([])

  /**
   * Generate random stars based on configuration
   */
  function generateStars() {
    const newStars: Star[] = []
    for (let i = 0; i < STARS_CONFIG.COUNT; i++) {
      newStars.push({
        x: Math.random() * STARS_CONFIG.POSITION_MAX,
        y: Math.random() * STARS_CONFIG.POSITION_MAX,
        size: Math.random() * (STARS_CONFIG.SIZE_MAX - STARS_CONFIG.SIZE_MIN) + STARS_CONFIG.SIZE_MIN,
        opacity: Math.random() * (STARS_CONFIG.OPACITY_MAX - STARS_CONFIG.OPACITY_MIN) + STARS_CONFIG.OPACITY_MIN,
        duration: Math.random() * (STARS_CONFIG.DURATION_MAX - STARS_CONFIG.DURATION_MIN) + STARS_CONFIG.DURATION_MIN,
        delay: Math.random() * STARS_CONFIG.DELAY_MAX
      })
    }
    stars.value = newStars
  }

  return {
    stars,
    generateStars
  }
}

