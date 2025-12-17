# WhatsApp → Telegram Migrator

Веб-приложение для переноса чатов из WhatsApp в Telegram со всеми медиафайлами в максимальном качестве.

## Технологии

- **Backend**: Python + FastAPI
- **Frontend**: Vue.js 3 + Vite
- **Telegram API**: Telethon (MTProto)

## Структура проекта

```
whatsapp_to_tg/
├── backend/
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── core/         # Конфигурация и безопасность
│   │   ├── services/     # Бизнес-логика
│   │   └── main.py       # Точка входа FastAPI
│   ├── sessions/         # Telegram сессии
│   ├── tmp/              # Временные файлы
│   ├── Dockerfile        # Docker образ для backend
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/        # Страницы приложения
│   │   ├── components/   # Компоненты
│   │   ├── store/        # Pinia store
│   │   └── router/       # Vue Router
│   ├── Dockerfile        # Docker образ для frontend
│   └── package.json
├── docker-compose.yml    # Docker Compose конфигурация
└── README.md
```

## Установка

### Docker (Рекомендуется)

1. Убедитесь, что у вас установлены Docker и Docker Compose

2. Создайте файл `.env` в корне проекта:
```env
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_BOT_TOKEN=your_bot_token_optional
SECRET_KEY=your-secret-key-change-in-production
```

3. Запустите проект:
```bash
docker-compose up -d
```

4. Приложение будет доступно по адресу `http://localhost:5173`

5. Для остановки:
```bash
docker-compose down
```

6. Для просмотра логов:
```bash
docker-compose logs -f
```

### Локальная установка

#### Backend

1. Создайте виртуальное окружение:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Установите браузеры для Playwright (требуется для WhatsApp Web):
```bash
playwright install chromium
```

3. Создайте файл `.env` в папке `backend/`:
```env
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_BOT_TOKEN=your_bot_token_optional
SECRET_KEY=your-secret-key-change-in-production
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

4. Установите браузеры для Playwright (требуется для WhatsApp Web):
```bash
playwright install chromium
```

5. Запустите сервер:
```bash
uvicorn app.main:app --reload --port 8000
```

### Frontend

1. Установите зависимости:
```bash
cd frontend
npm install
```

2. Запустите dev сервер:
```bash
npm run dev
```

Приложение будет доступно по адресу `http://localhost:5173`

## Получение Telegram API credentials

1. Перейдите на https://my.telegram.org/apps
2. Войдите в свой аккаунт Telegram
3. Создайте новое приложение
4. Скопируйте `api_id` и `api_hash`

## Использование

1. Откройте приложение в браузере
2. Нажмите "Начать перенос"
3. Подключите WhatsApp Web (отсканируйте QR-код)
4. Выберите чаты для переноса
5. Авторизуйтесь в Telegram
6. Сопоставьте чаты WhatsApp с Telegram
7. Дождитесь завершения миграции

## WhatsApp Web подключение

Приложение использует Playwright для автоматизации WhatsApp Web:
- QR-код генерируется автоматически при запросе `/api/whatsapp/connect`
- Статус подключения можно отслеживать через `/api/whatsapp/status/{session_id}`
- Сессии сохраняются в `sessions/whatsapp/` для повторного использования

## Сохранение и переиспользование сессий

Система автоматически сохраняет авторизацию в WhatsApp и Telegram, чтобы не вводить данные каждый раз заново во время тестов.

**Подробная документация:** [SESSION_REUSE.md](SESSION_REUSE.md)

### Быстрый старт:

**Telegram:** Сессии сохраняются автоматически. При повторном использовании авторизация не требуется.

**WhatsApp:** 
- Получить список сохраненных сессий: `GET /api/whatsapp/sessions`
- Переиспользовать сессию: `POST /api/whatsapp/sessions/{session_id}/reuse`
- Или указать `session_id` при создании подключения: `POST /api/whatsapp/connect` с `{"session_id": "..."}`

## Особенности

- Поддержка всех типов медиа (фото, видео, аудио, документы, стикеры, GIF)
- Отправка медиа в максимальном качестве через `sendDocument`
- Группировка фото в альбомы
- Отслеживание прогресса в реальном времени
- Обработка ошибок с возможностью продолжения

## Ограничения

- Максимальный размер ZIP: 20GB
- Максимальный размер файла: 2GB (лимит Telegram)
- Скорость отправки: ~10-40 сообщений/мин (зависит от Telegram API)

## Лицензия

MIT
