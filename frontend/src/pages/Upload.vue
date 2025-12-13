<template>
  <div class="upload-page">
    <div class="upload-card">
      <h2>Загрузите экспорт WhatsApp</h2>
      <p class="description">
        Выберите ZIP файл с экспортом чата из WhatsApp
      </p>
      
      <div class="upload-area" 
           @drop="handleDrop"
           @dragover.prevent
           @dragenter.prevent
           :class="{ 'dragover': isDragging }">
        <input 
          type="file" 
          ref="fileInput"
          @change="handleFileSelect"
          accept=".zip"
          style="display: none"
        />
        
        <div v-if="!uploading && !uploaded" class="upload-content">
          <span class="upload-icon">📦</span>
          <p>Перетащите ZIP файл сюда или</p>
          <button @click="$refs.fileInput.click()" class="btn-select">
            Выбрать файл
          </button>
          <p class="file-info" v-if="selectedFile">
            Выбран: {{ selectedFile.name }} ({{ formatSize(selectedFile.size) }})
          </p>
        </div>
        
        <div v-if="uploading" class="upload-progress">
          <div class="spinner"></div>
          <p>Загрузка файла...</p>
        </div>
        
        <div v-if="uploaded && !uploading" class="upload-success">
          <span class="success-icon">✅</span>
          <p>Файл успешно загружен!</p>
          <button @click="continueToAuth" class="btn-primary">
            Продолжить
          </button>
        </div>
      </div>
      
      <div v-if="error" class="error-message">
        {{ error }}
      </div>
    </div>
  </div>
</template>

<script>
import { useMigrationStore } from '../store/migration'
import api from '../api/client'

export default {
  name: 'Upload',
  data() {
    return {
      selectedFile: null,
      uploading: false,
      uploaded: false,
      isDragging: false,
      error: null
    }
  },
  setup() {
    const store = useMigrationStore()
    return { store }
  },
  methods: {
    handleFileSelect(event) {
      const file = event.target.files[0]
      if (file) {
        this.selectedFile = file
        this.uploadFile(file)
      }
    },
    
    handleDrop(event) {
      event.preventDefault()
      this.isDragging = false
      const file = event.dataTransfer.files[0]
      if (file && file.name.endsWith('.zip')) {
        this.selectedFile = file
        this.uploadFile(file)
      }
    },
    
    async uploadFile(file) {
      this.uploading = true
      this.error = null
      
      const formData = new FormData()
      formData.append('file', file)
      
      try {
        const response = await api.post('/upload', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        })
        
        this.store.setSessionId(response.data.session_id)
        this.uploaded = true
        this.uploading = false
      } catch (error) {
        this.error = error.response?.data?.detail || 'Ошибка загрузки файла'
        this.uploading = false
      }
    },
    
    continueToAuth() {
      this.$router.push('/auth')
    },
    
    formatSize(bytes) {
      if (bytes === 0) return '0 Bytes'
      const k = 1024
      const sizes = ['Bytes', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
    }
  }
}
</script>

<style scoped>
.upload-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}

.upload-card {
  background: white;
  border-radius: 16px;
  padding: 3rem;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  max-width: 600px;
  width: 100%;
}

.upload-card h2 {
  color: #333;
  font-size: 2rem;
  margin-bottom: 0.5rem;
  text-align: center;
}

.description {
  color: #666;
  text-align: center;
  margin-bottom: 2rem;
}

.upload-area {
  border: 3px dashed #ddd;
  border-radius: 12px;
  padding: 3rem;
  text-align: center;
  transition: all 0.3s;
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-area.dragover {
  border-color: #667eea;
  background: #f0f4ff;
}

.upload-content {
  width: 100%;
}

.upload-icon {
  font-size: 4rem;
  display: block;
  margin-bottom: 1rem;
}

.upload-content p {
  color: #666;
  margin: 1rem 0;
}

.btn-select {
  background: #667eea;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  margin: 1rem 0;
}

.file-info {
  font-size: 0.9rem;
  color: #667eea;
  font-weight: 600;
}

.upload-progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.upload-success {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.success-icon {
  font-size: 4rem;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 1rem 2rem;
  font-size: 1.1rem;
  border-radius: 8px;
  cursor: pointer;
  transition: transform 0.2s;
  font-weight: 600;
}

.btn-primary:hover {
  transform: translateY(-2px);
}

.error-message {
  margin-top: 1rem;
  padding: 1rem;
  background: #fee;
  color: #c33;
  border-radius: 8px;
  text-align: center;
}
</style>
