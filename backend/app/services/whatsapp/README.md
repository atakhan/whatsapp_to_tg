# WhatsApp Service - Декомпозированная структура

## Структура модулей

```
whatsapp/
├── __init__.py              # Экспорт сервиса и глобального экземпляра
├── browser_manager.py       # Управление Playwright браузером (~100 строк)
├── session_manager.py       # Управление сессиями на диске (~200 строк)
├── connection_manager.py    # QR-коды и подключение (~540 строк)
├── chat_parser.py           # Парсинг чатов (~400 строк)
├── message_parser.py        # Парсинг сообщений (~600 строк)
└── whatsapp_service.py      # Главный сервис-фасад (~200 строк)
```

**Итого:** ~2138 строк (было 2595 в одном файле)

## Компоненты

### 1. BrowserManager
**Ответственность:** Управление Playwright браузером

**Методы:**
- `initialize()` - инициализация Playwright
- `shutdown()` - закрытие браузера
- `create_persistent_context()` - создание persistent context
- `create_page()` - создание страницы с настройками

### 2. SessionManager
**Ответственность:** Управление сессиями (создание, переиспользование, очистка)

**Методы:**
- `get_session_path()` - путь к сессии
- `list_existing_sessions()` - список сессий на диске
- `check_session_exists()` - проверка существования
- `try_reuse_session()` - переиспользование сессии
- `cleanup_session()` - очистка сессии
- `is_connected()` - проверка подключения
- `get_session()` / `set_session()` - работа с кешем в памяти

### 3. ConnectionManager
**Ответственность:** Подключение к WhatsApp, QR-коды, мониторинг

**Методы:**
- `start_connection()` - начало подключения
- `_monitor_connection()` - мониторинг подключения (фоновый)
- `get_status()` - статус подключения
- `_find_qr_code()` - поиск QR-кода
- `_check_connection_status()` - проверка статуса

### 4. ChatParser
**Ответственность:** Парсинг чатов из WhatsApp Web

**Методы:**
- `parse_chats_streaming()` - потоковый парсинг
- `parse_chats()` - полный парсинг
- `_parse_chats_batch()` - парсинг батча

### 5. MessageParser
**Ответственность:** Парсинг сообщений из чата

**Методы:**
- `parse_messages_streaming()` - потоковый парсинг
- `parse_messages()` - полный парсинг
- `_parse_all_messages()` - парсинг всех сообщений
- `_find_message_container()` - поиск контейнера
- `_open_chat()` - открытие чата

### 6. WhatsAppConnectService
**Ответственность:** Главный сервис-фасад, композиция всех компонентов

**Роль:** Предоставляет единый интерфейс, делегирует вызовы компонентам, сохраняет обратную совместимость

## Преимущества новой структуры

1. ✅ **Разделение ответственности** - каждый модуль отвечает за одну область
2. ✅ **Легче тестировать** - можно мокировать отдельные компоненты
3. ✅ **Легче поддерживать** - изменения изолированы в отдельных модулях
4. ✅ **Легче понимать** - один файл = одна ответственность
5. ✅ **Обратная совместимость** - главный сервис остается фасадом
6. ✅ **Переиспользование** - компоненты можно использовать отдельно

## Использование

```python
from app.services.whatsapp import whatsapp_service

# Все методы работают так же, как раньше
await whatsapp_service.start_connection(session_id)
await whatsapp_service.get_chats_streaming(session_id)
await whatsapp_service.get_chat_messages_streaming(session_id, chat_id)
```

## Миграция

Все импорты обновлены:
- ✅ `backend/app/api/whatsapp.py`
- ✅ `backend/app/main.py`
- ✅ `backend/app/api/migrate.py`

Старый файл `whatsapp_connect.py` удален.
