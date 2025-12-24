<template>
  <svg class="space-traffic" :class="{ 'element-hidden': hidden }" width="100%" height="100%">
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
      <g :transform="`scale(${SHIP_VISUAL.SHIP_SCALE})`" v-show="shipState.mainEngine">
        <!-- Flame size depends on throttle level -->
        <path fill="#ffca3a" d="M-2 10 Q0 25 2 10 Z" opacity="0.9">
          <animate
            attributeName="d"
            values="M-2 10 Q0 25 2 10 Z; M-2 10 Q0 20 2 10 Z; M-2 10 Q0 25 2 10 Z"
            :dur="SHIP_VISUAL.FLAME_ANIMATION_DURATION"
            repeatCount="indefinite"
          />
          <!-- Dynamic flame scaling based on throttle -->
          <animateTransform
            attributeName="transform"
            type="scale"
            :values="shipState.throttle > SHIP_VISUAL.FLAME_THROTTLE_THRESHOLD ? SHIP_VISUAL.FLAME_SCALE_HIGH : SHIP_VISUAL.FLAME_SCALE_LOW"
            :dur="SHIP_VISUAL.FLAME_TRANSFORM_DURATION"
            repeatCount="indefinite"
          />
        </path>
      </g>

      <!-- RCS THRUSTERS -->
      <g :transform="`scale(${SHIP_VISUAL.SHIP_SCALE})`">
        <!-- Left RCS (Rotates Ship Right / Clockwise) -->
        <path
          v-show="shipState.rcsLeft"
          fill="#ffca3a"
          d="M -4 -9 Q -9 -9.5 -4 -10 Z"
        >
          <animate
            attributeName="d"
            values="M -4 -9 Q -9 -9.5 -4 -10 Z; M -4 -9 Q -7 -9.5 -4 -10 Z"
            :dur="SHIP_VISUAL.RCS_ANIMATION_DURATION"
            repeatCount="indefinite"
          />
        </path>

        <!-- Right RCS (Rotates Ship Left / Counter-Clockwise) -->
        <path
          v-show="shipState.rcsRight"
          fill="#ffca3a"
          d="M 4 -9 Q 9 -9.5 4 -10 Z"
        >
          <animate
            attributeName="d"
            values="M 4 -9 Q 9 -9.5 4 -10 Z; M 4 -9 Q 7 -9.5 4 -10 Z"
            :dur="SHIP_VISUAL.RCS_ANIMATION_DURATION"
            repeatCount="indefinite"
          />
        </path>
      </g>
    </g>
  </svg>
</template>

<script setup lang="ts">
import { SHIP_VISUAL } from '../constants/rocketConstants'
import type { ShipState } from '../composables/useRocketPhysics'

defineProps<{
  shipState: ShipState
  hidden?: boolean
}>()
</script>

<style scoped>
.space-traffic {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 10;
}

.element-hidden {
  display: none;
}
</style>

