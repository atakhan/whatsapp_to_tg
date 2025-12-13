<template>
  <div class="welcome-page">
    <div class="welcome-card">
      <h2>Добро пожаловать!</h2>
      <p class="description">
        Это приложение поможет вам перенести чаты из WhatsApp в Telegram
        со всеми медиафайлами в максимальном качестве.
      </p>
      
      <div class="features">
        <div class="feature">
          <span class="icon">📸</span>
          <span>Фото и видео</span>
        </div>
        <div class="feature">
          <span class="icon">🎵</span>
          <span>Аудио и голосовые</span>
        </div>
        <div class="feature">
          <span class="icon">📄</span>
          <span>Документы</span>
        </div>
        <div class="feature">
          <span class="icon">🎨</span>
          <span>Стикеры и GIF</span>
        </div>
      </div>
      
      <button @click="startMigration" class="btn-primary">
        Начать перенос
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Welcome',
  methods: {
    startMigration() {
      this.$router.push('/upload')
    }
  }
}
</script>

<style scoped>
.welcome-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}

.welcome-card {
  background: white;
  border-radius: 16px;
  padding: 3rem;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  max-width: 600px;
  width: 100%;
  text-align: center;
}

.welcome-card h2 {
  color: #333;
  font-size: 2rem;
  margin-bottom: 1rem;
}

.description {
  color: #666;
  font-size: 1.1rem;
  line-height: 1.6;
  margin-bottom: 2rem;
}

.features {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
  margin-bottom: 2rem;
}

.feature {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  background: #f5f5f5;
  border-radius: 8px;
}

.feature .icon {
  font-size: 1.5rem;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 1rem 2rem;
  font-size: 1.1rem;
  border-radius: 8px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  font-weight: 600;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
}

.btn-primary:active {
  transform: translateY(0);
}

@media (max-width: 768px) {
  .welcome-card {
    padding: 2rem;
  }
  
  .features {
    grid-template-columns: 1fr;
  }
}
</style>
