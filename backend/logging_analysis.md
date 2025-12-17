# Анализ логирования (backend)

## Соответствие стандарту
- Включено централизованное JSON-логирование с обязательными полями и кореляцией: модуль `app/core/logging_setup.py` реализует формат, contextvars, trace_id/request_id, middleware FastAPI и настройку root/uvicorn.
- Подключение на старте сервиса: `app/main.py` вызывает `configure_logging(...)` и вешает `request_logging_middleware` → HTTP-трафик получает trace/request ID, latency, статус.
- Конфиг содержит `SERVICE_NAME`/`ENV` и пример в `.env.example`, что позволяет унифицировать имя сервиса и окружение.

## Обнаруженные отклонения
- Использование `print(...)` вместо структурных логов (теряется контекст, нет trace/request ID):\
  - `app/services/whatsapp_connect.py` (cleanup errors)\
  - `app/services/file_manager.py` (cleanup errors)\
  - `app/services/telegram_client.py` (send/connect errors)\
  - `app/api/migrate.py` (migration error)\
  - `app/services/whatsapp_parser.py` (parse errors)\
  - `app/services/migration_manager.py` (status load/save, validation)
- Ошибки логируются без `error_code` и без дополнительного контекста (entity ids, paths), хотя формат это поддерживает через `extra`.
- Фоновые/asynchronous задачи: при создании задач (например, `asyncio.create_task` в `whatsapp_connect.py`) кореляция должна сохраняться; стоит подтвердить/зафиксировать явной установкой `set_correlation_ids` при старте фоновых работ.

## Рекомендации
- Заменить `print` на `logging.getLogger(__name__)` и писать через наш формат, передавая `extra={"error_code": "...", "extra_data": {...}}` и полезные идентификаторы (session_id, chat_id, file, user).
- Для фоновых задач при старте задавать контекст: `trace_id, request_id = set_correlation_ids(trace_id_ctx.get(), request_id_ctx.get())` или генерировать новый, плюс `set_request_context(user_id=..., ...)` если есть данные.
- Для ошибок сети/интеграций добавить коды, например: `error_code="TELEGRAM_SEND_FAIL"`, `error_code="WHATSAPP_PARSE_FAIL"`.
- Проверить чувствительные данные: исключить токены/PII из логов; в текущих вызовах параметры безопасны, но при добавлении контекста не логировать секреты.
- Опционально: добавить небольшой helper для ошибок, чтобы сократить дублирование (`log_error(logger, msg, error_code, **context)`).

## Краткий чек-лист правок
- [ ] `print` → структурные логи в перечисленных модулях.  
- [ ] Добавить `error_code` и `extra_data` с ключевым контекстом в ошибках.  
- [ ] Зафиксировать/проверить перенос trace/request ID в фоновые задачи.  
- [ ] Не логировать секреты/PII при добавлении контекста.
