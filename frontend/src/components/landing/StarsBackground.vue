<template>
  <div 
    v-for="(star, index) in stars" 
    :key="index"
    class="star"
    :style="getStarStyle(star)"
  ></div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useStars, type Star } from '../../composables/useStars'

const { stars, generateStars } = useStars()

onMounted(() => {
  generateStars()
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

<style scoped>
.star {
  position: absolute;
  background: white;
  border-radius: 50%;
  animation: twinkle linear infinite;
}

@keyframes twinkle {
  0%, 100% { 
    opacity: 0.2; 
    transform: scale(0.8); 
  }
  50% { 
    opacity: 1; 
    transform: scale(1.2); 
  }
}
</style>

