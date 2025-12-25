# 📁 Структура директорий после рефакторинга

## Текущая структура

```
backend/app/services/whatsapp/
├── __init__.py
├── browser_manager.py
├── chat_parser.py              ❌ Будет удален
├── connection_manager.py
├── message_parser.py
├── session_manager.py
└── whatsapp_service.py
```

## Новая структура

```
backend/app/services/whatsapp/
├── __init__.py
├── browser_manager.py
├── connection_manager.py
├── message_parser.py
├── session_manager.py
├── whatsapp_service.py
│
└── parsing/                    ✨ Новая директория
    ├── __init__.py
    │
    ├── orchestrator.py         # ChatParsingOrchestrator
    │
    ├── models/                 # Модели данных
    │   ├── __init__.py
    │   ├── chat_dto.py         # ChatDTO
    │   ├── parsing_result.py   # ParsingResult
    │   └── raw_chat.py         # RawChat
    │
    ├── sources/                # Источники данных
    │   ├── __init__.py
    │   ├── base.py             # IChatSource интерфейс
    │   ├── store_chat_source.py      # StoreChatSource (приоритетный)
    │   ├── cdp_network_chat_source.py # CDPNetworkChatSource
    │   ├── dom_chat_source.py        # DOMChatSource (fallback)
    │   └── source_selector.py        # SourceSelector
    │
    ├── normalizers/            # Нормализация данных
    │   ├── __init__.py
    │   └── chat_normalizer.py  # ChatNormalizer
    │
    ├── identity/               # Идентификация чатов
    │   ├── __init__.py
    │   └── identity_resolver.py # IdentityResolver
    │
    ├── completion/             # Контроль завершения
    │   ├── __init__.py
    │   └── completion_controller.py # CompletionController
    │
    └── publishers/             # Публикация результатов
        ├── __init__.py
        └── result_publisher.py # ResultPublisher
```

## Импорты после рефакторинга

### В `whatsapp_service.py`:

```python
# Старый импорт (удалить):
from app.services.whatsapp.chat_parser import ChatParser

# Новый импорт:
from app.services.whatsapp.parsing.orchestrator import ChatParsingOrchestrator

# Использование:
class WhatsAppConnectService:
    def __init__(self):
        # ...
        self.chat_parser = ChatParsingOrchestrator()  # Вместо ChatParser()
```

### В API endpoints:

```python
# Старый код:
async for batch in service.get_chats_streaming(session_id):
    yield batch

# Новый код (формат может измениться):
async for result in service.get_chats_streaming(session_id):
    # result - это ParsingResult
    yield result.chats  # или адаптировать под текущий формат SSE
```

## Миграция данных

### Старый формат чата:
```python
{
    'id': '1234567890@c.us',
    'name': 'Chat Name',
    'type': 'personal',
    'avatar': 'https://...',
    'message_count': 5,
    'is_group': False
}
```

### Новый формат (ChatDTO):
```python
ChatDTO(
    id='1234567890@c.us',
    type='personal',
    name='Chat Name',
    avatar='https://...',
    unread_count=5,
    source='store',  # или 'network', 'dom'
    integrity='verified',  # или 'fallback', 'ambiguous'
    raw_data={...}  # исходные данные для диагностики
)
```

## Обратная совместимость

Для сохранения обратной совместимости можно добавить адаптер:

```python
class ChatDTOAdapter:
    """Адаптирует ChatDTO к старому формату"""
    
    @staticmethod
    def to_dict(chat_dto: ChatDTO) -> dict:
        return {
            'id': chat_dto.id,
            'name': chat_dto.name,
            'type': chat_dto.type,
            'avatar': chat_dto.avatar,
            'message_count': chat_dto.unread_count,
            'is_group': chat_dto.type == 'group'
        }
```


