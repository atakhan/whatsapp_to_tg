# Сохранение и переиспользование сессий

Система автоматически сохраняет авторизацию в WhatsApp и Telegram, чтобы не вводить данные каждый раз заново во время тестов.

## Telegram

Сессии Telegram сохраняются автоматически в файлы `.session` в директории `sessions/`. Файл называется `{user_id}.session`.

### Как это работает:

1. При первой авторизации через `/api/telegram-phone-auth` и `/api/telegram-verify-code` создается файл сессии
2. При последующих запросах система автоматически проверяет наличие файла сессии
3. Если сессия существует и валидна, авторизация не требуется

### Проверка существующей сессии:

```bash
# Проверить, существует ли сессия для user_id=123456789
curl http://localhost:8000/api/telegram-login \
  -H "Content-Type: application/json" \
  -d '{"auth_data": {...}}'
```

Если сессия существует, вернется `"session_exists": true`.

## WhatsApp

Сессии WhatsApp сохраняются в директории `sessions/whatsapp/{session_id}/browser_data/` с использованием persistent browser context.

### Список существующих сессий:

```bash
# Получить список всех сохраненных сессий WhatsApp
curl http://localhost:8000/api/whatsapp/sessions
```

Ответ:
```json
{
  "sessions": ["session-id-1", "session-id-2"],
  "count": 2
}
```

### Переиспользование существующей сессии:

#### Вариант 1: Указать session_id при создании подключения

```bash
# Переиспользовать существующую сессию
curl -X POST http://localhost:8000/api/whatsapp/connect \
  -H "Content-Type: application/json" \
  -d '{"session_id": "your-existing-session-id"}'
```

#### Вариант 2: Использовать отдельный endpoint для переиспользования

```bash
# Попытаться переиспользовать сессию
curl -X POST http://localhost:8000/api/whatsapp/sessions/{session_id}/reuse
```

Ответ при успехе:
```json
{
  "reused": true,
  "session_id": "your-session-id",
  "status": {
    "session_id": "your-session-id",
    "status": "ready",
    "connected_at": "2025-12-16T10:30:00"
  }
}
```

Ответ при неудаче:
```json
{
  "reused": false,
  "session_id": "your-session-id",
  "reason": "Session directory not found"
}
```

### Создание новой сессии:

```bash
# Создать новую сессию (без указания session_id)
curl -X POST http://localhost:8000/api/whatsapp/connect \
  -H "Content-Type: application/json" \
  -d '{}'
```

## Удаление сессий

### WhatsApp:

```bash
# Удалить сессию WhatsApp
curl -X DELETE http://localhost:8000/api/whatsapp/session/{session_id}
```

### Telegram:

Сессии Telegram хранятся в файлах `sessions/{user_id}.session`. Для удаления просто удалите соответствующий файл:

```bash
rm sessions/123456789.session
```

## Важные замечания

1. **WhatsApp сессии**: Сохраняются автоматически при первом подключении через QR-код. При перезапуске сервера сессии остаются на диске, но нужно переиспользовать их через API.

2. **Telegram сессии**: Сохраняются автоматически и переиспользуются автоматически. Если сессия существует, система попытается использовать её без запроса авторизации.

3. **Безопасность**: Сессии содержат токены авторизации. Не коммитьте их в git и не передавайте третьим лицам.

4. **Очистка**: После завершения тестирования рекомендуется удалить сессии для безопасности.

## Docker и сохранение сессий

### Сессии сохраняются между перезапусками

В `docker-compose.yml` настроены volumes для сохранения сессий:

```yaml
volumes:
  - ./backend/sessions:/app/sessions
  - ./backend/tmp:/app/tmp
```

Это означает, что сессии хранятся на хосте в `./backend/sessions/` и сохраняются между перезапусками контейнера.

### Что происходит при перезапуске:

1. **Обычный перезапуск** (`docker-compose restart` или `docker-compose down` + `docker-compose up`):
   - ✅ Сессии сохраняются на диске
   - ⚠️ Сессии в памяти контейнера теряются
   - ✅ Нужно переиспользовать через API (см. ниже)

2. **Пересборка образа** (`docker-compose up --build`):
   - ✅ Сессии сохраняются (volumes не затрагиваются)
   - ✅ После запуска можно переиспользовать

3. **Удаление volumes** (`docker-compose down -v`):
   - ❌ **ВНИМАНИЕ**: Все сессии будут удалены!
   - ❌ Придется авторизоваться заново

### После перезапуска контейнера:

**WhatsApp:**
```bash
# 1. Проверить сохраненные сессии
curl http://localhost:8000/api/whatsapp/sessions

# 2. Переиспользовать сессию
curl -X POST http://localhost:8000/api/whatsapp/sessions/{session_id}/reuse
```

**Telegram:**
Сессии переиспользуются автоматически при первом запросе, если файл `sessions/{user_id}.session` существует.

### Где хранятся сессии:

- **Telegram**: `backend/sessions/{user_id}.session`
- **WhatsApp**: `backend/sessions/whatsapp/{session_id}/browser_data/`

Эти директории монтируются в контейнер, поэтому данные сохраняются на хосте.

## Пример использования в тестах

```python
import requests

# 1. Проверить существующие WhatsApp сессии
sessions = requests.get("http://localhost:8000/api/whatsapp/sessions").json()
print(f"Найдено сессий: {sessions['count']}")

# 2. Если есть сохраненная сессия, переиспользовать её
if sessions['count'] > 0:
    session_id = sessions['sessions'][0]
    reuse_result = requests.post(
        f"http://localhost:8000/api/whatsapp/sessions/{session_id}/reuse"
    ).json()
    
    if reuse_result['reused']:
        print(f"Сессия {session_id} успешно переиспользована!")
    else:
        print(f"Не удалось переиспользовать: {reuse_result['reason']}")
else:
    # 3. Создать новую сессию
    new_session = requests.post(
        "http://localhost:8000/api/whatsapp/connect",
        json={}
    ).json()
    print(f"Создана новая сессия: {new_session['session_id']}")
```
