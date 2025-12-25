# 📋 План рефакторинга парсера чатов WhatsApp Web

## 🎯 Цель рефакторинга

Преобразовать монолитный DOM-парсер в модульную архитектуру с разделением ответственности, поддержкой множественных источников данных и детерминированными критериями завершения.

---

## 📊 Текущее состояние

### Проблемы текущей реализации:

1. **Монолитная архитектура** - вся логика в `ChatParser` (803 строки)
2. **Только DOM-парсинг** - хрупкий, зависит от структуры HTML
3. **Нет доступа к Store** - не используем внутренний state WhatsApp Web
4. **Нет CDP-интеграции** - не перехватываем network payloads
5. **Нет детерминированного завершения** - эвристики на основе скролла
6. **Смешанная ответственность** - скролл, парсинг, нормализация в одном месте
7. **Нет проверки целостности** - не сверяем данные между источниками
8. **Хрупкая идентификация** - ID извлекается из aria-label через regex

---

## 🏗️ Целевая архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    ChatParsingOrchestrator                  │
│  (координирует все компоненты, выбирает источник)           │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ IChatSource  │   │  Normalizer  │   │ IdentityRes. │
│  (абстракция)│   │              │   │              │
└──────────────┘   └──────────────┘   └──────────────┘
        │                   │                   │
        ├─── StoreChatSource                    │
        ├─── CDPNetworkChatSource               │
        └─── DOMChatSource (fallback)           │
                            │                   │
                            ▼                   ▼
                    ┌──────────────┐   ┌──────────────┐
                    │  Completion  │   │  Publisher   │
                    │  Controller  │   │              │
                    └──────────────┘   └──────────────┘
                            │                   │
                            └─────────┬─────────┘
                                      ▼
                              ┌──────────────┐
                              │   ChatDTO    │
                              │   (модель)   │
                              └──────────────┘
```

---

## 📦 Структура модулей

### 1. Модели данных (`models/`)

#### `chat_dto.py`
```python
from dataclasses import dataclass
from typing import Literal, Optional

@dataclass
class ChatDTO:
    id: str
    type: Literal["personal", "group", "broadcast"]
    name: Optional[str]
    avatar: Optional[str]
    unread_count: int
    source: Literal["store", "network", "dom"]
    integrity: Literal["verified", "fallback", "ambiguous"]
    raw_data: dict  # Сохраняем исходные данные для диагностики
```

#### `parsing_result.py`
```python
from dataclasses import dataclass
from typing import List, Literal, Optional
from .chat_dto import ChatDTO

@dataclass
class ParsingResult:
    chats: List[ChatDTO]
    completeness: Literal["complete", "partial"]
    collected: int
    expected: Optional[int]
    missing_ids: List[str]
    source_type: str
    anomalies: List[dict]
    metadata: dict
```

---

### 2. Источники данных (`sources/`)

#### `base.py` - Интерфейс источника
```python
from abc import ABC, abstractmethod
from typing import List, Optional
from ..models.chat_dto import ChatDTO

class RawChat:
    """Сырые данные чата из источника"""
    pass

class IChatSource(ABC):
    @abstractmethod
    async def init(self) -> None:
        """Инициализация источника"""
        pass
    
    @abstractmethod
    async def fetch_batch(self) -> List[RawChat]:
        """Получить батч чатов"""
        pass
    
    @abstractmethod
    async def is_complete(self) -> bool:
        """Проверка завершения"""
        pass
    
    @abstractmethod
    async def total_expected(self) -> Optional[int]:
        """Ожидаемое общее количество"""
        pass
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Имя источника для логирования"""
        pass
```

#### `store_chat_source.py` - Store источник (приоритетный)
```python
from playwright.async_api import Page
from .base import IChatSource, RawChat

class StoreChatSource(IChatSource):
    """Получение чатов из window.Store WhatsApp Web"""
    
    def __init__(self, page: Page):
        self.page = page
        self._initialized = False
        self._total_count = None
    
    async def init(self) -> None:
        """Проверяем доступность Store"""
        # Проверяем наличие window.Store
        # Получаем total_chat_count
        pass
    
    async def fetch_batch(self) -> List[RawChat]:
        """Получаем все чаты из Store"""
        # window.Store.Chat.models или аналогичная структура
        pass
    
    async def is_complete(self) -> bool:
        """Всегда true для Store (данные уже полные)"""
        return True
    
    async def total_expected(self) -> Optional[int]:
        """Возвращаем total_chat_count из Store"""
        return self._total_count
```

#### `cdp_network_chat_source.py` - CDP Network источник
```python
from playwright.async_api import Page, CDPSession
from .base import IChatSource, RawChat

class CDPNetworkChatSource(IChatSource):
    """Перехват network payloads через CDP"""
    
    def __init__(self, page: Page):
        self.page = page
        self.cdp_session: Optional[CDPSession] = None
        self._collected_payloads = []
        self._total_count = None
    
    async def init(self) -> None:
        """Инициализируем CDP сессию и включаем Network domain"""
        # page.context.new_cdp_session(page)
        # cdp_session.send('Network.enable')
        # Подписываемся на Network.responseReceived
        pass
    
    async def fetch_batch(self) -> List[RawChat]:
        """Извлекаем чаты из перехваченных network payloads"""
        # Парсим protobuf / JSON из network responses
        pass
    
    async def is_complete(self) -> bool:
        """Проверяем по total_chat_count из payload"""
        pass
```

#### `dom_chat_source.py` - DOM fallback источник
```python
from playwright.async_api import Page
from .base import IChatSource, RawChat

class DOMChatSource(IChatSource):
    """DOM-парсинг как fallback (текущая логика)"""
    
    def __init__(self, page: Page):
        self.page = page
        self._seen_ids = set()
        self._scroll_iterations = 0
        self._no_new_chats_count = 0
    
    async def init(self) -> None:
        """Инициализация DOM-парсинга"""
        # Ждем загрузки страницы
        # Ищем контейнер списка чатов
        pass
    
    async def fetch_batch(self) -> List[RawChat]:
        """Парсим видимые чаты из DOM"""
        # Текущая логика _parse_all_visible_chats
        # Но возвращаем RawChat вместо Dict
        pass
    
    async def is_complete(self) -> bool:
        """Эвристика завершения (улучшенная)"""
        # Достигли конца И нет новых чатов
        pass
    
    async def total_expected(self) -> Optional[int]:
        """Неизвестно для DOM"""
        return None
```

#### `source_selector.py` - Выбор источника
```python
from typing import Optional
from playwright.async_api import Page
from .store_chat_source import StoreChatSource
from .cdp_network_chat_source import CDPNetworkChatSource
from .dom_chat_source import DOMChatSource
from .base import IChatSource

class SourceSelector:
    """Выбирает оптимальный источник данных"""
    
    @staticmethod
    async def select_source(page: Page) -> IChatSource:
        """Пробуем источники в порядке приоритета"""
        # 1. StoreChatSource
        # 2. CDPNetworkChatSource
        # 3. DOMChatSource (fallback)
        pass
```

---

### 3. Нормализация (`normalizers/`)

#### `chat_normalizer.py`
```python
from typing import List
from ..models.chat_dto import ChatDTO
from ..sources.base import RawChat

class ChatNormalizer:
    """Преобразует RawChat в ChatDTO"""
    
    def normalize(self, raw_chat: RawChat, source: str) -> ChatDTO:
        """Нормализует один чат"""
        # Извлекаем id, type, name, avatar, unread_count
        # Определяем integrity статус
        pass
    
    def normalize_batch(self, raw_chats: List[RawChat], source: str) -> List[ChatDTO]:
        """Нормализует батч чатов"""
        pass
```

---

### 4. Идентификация (`identity/`)

#### `identity_resolver.py`
```python
from typing import List, Set
from ..models.chat_dto import ChatDTO

class IdentityResolver:
    """Надежная идентификация чатов"""
    
    def extract_id(self, raw_chat: RawChat, source: str) -> Optional[str]:
        """Извлекает ID из сырых данных"""
        # Приоритет:
        # 1. jid из store
        # 2. wid из store
        # 3. id.server_id из network
        # 4. user_id из network
        # НЕ используем aria-label, textContent, regex на номер
        pass
    
    def detect_ambiguities(self, chats: List[ChatDTO]) -> List[dict]:
        """Детектирует расхождения в данных"""
        # Разные имена у одного ID
        # ID есть в одном источнике, но нет в другом
        pass
```

---

### 5. Контроль завершения (`completion/`)

#### `completion_controller.py`
```python
from typing import List, Optional
from ..models.chat_dto import ChatDTO
from ..sources.base import IChatSource

class CompletionController:
    """Детерминированные критерии завершения"""
    
    def check_completion(
        self,
        collected_chats: List[ChatDTO],
        source: IChatSource
    ) -> tuple[bool, Optional[int], List[str]]:
        """
        Проверяет завершение парсинга
        
        Returns:
            (is_complete, expected_total, missing_ids)
        """
        # 1. Получаем total_expected из источника
        # 2. Сравниваем len(collected_chats) с total_expected
        # 3. Если source.is_complete() == True, считаем завершенным
        # 4. Вычисляем missing_ids если есть расхождения
        pass
```

---

### 6. Публикация результатов (`publishers/`)

#### `result_publisher.py`
```python
from typing import AsyncGenerator, List
from ..models.chat_dto import ChatDTO
from ..models.parsing_result import ParsingResult

class ResultPublisher:
    """Публикует результаты парсинга"""
    
    async def publish_stream(
        self,
        chats: AsyncGenerator[List[ChatDTO], None]
    ) -> AsyncGenerator[ParsingResult, None]:
        """Стримит результаты по мере получения"""
        pass
    
    async def publish_final(
        self,
        chats: List[ChatDTO],
        completeness: str,
        metadata: dict
    ) -> ParsingResult:
        """Публикует финальный результат"""
        pass
```

---

### 7. Оркестратор (`orchestrator.py`)

#### `chat_parsing_orchestrator.py`
```python
from typing import AsyncGenerator, List
from playwright.async_api import Page
from ..models.chat_dto import ChatDTO
from ..models.parsing_result import ParsingResult
from ..sources.source_selector import SourceSelector
from ..normalizers.chat_normalizer import ChatNormalizer
from ..identity.identity_resolver import IdentityResolver
from ..completion.completion_controller import CompletionController
from ..publishers.result_publisher import ResultPublisher

class ChatParsingOrchestrator:
    """Главный оркестратор парсинга чатов"""
    
    def __init__(self):
        self.source_selector = SourceSelector()
        self.normalizer = ChatNormalizer()
        self.identity_resolver = IdentityResolver()
        self.completion_controller = CompletionController()
        self.publisher = ResultPublisher()
    
    async def parse_chats_streaming(
        self,
        page: Page
    ) -> AsyncGenerator[ParsingResult, None]:
        """Основной метод парсинга с стримингом"""
        # 1. Выбираем источник
        # 2. Инициализируем источник
        # 3. В цикле:
        #    - fetch_batch()
        #    - normalize()
        #    - resolve_identity()
        #    - publish()
        #    - check_completion()
        # 4. Публикуем финальный результат
        pass
```

---

## 🔄 Этапы реализации

### Этап 1: Подготовка инфраструктуры (1-2 дня)

**Задачи:**
1. ✅ Создать структуру директорий
2. ✅ Создать модели данных (`ChatDTO`, `ParsingResult`, `RawChat`)
3. ✅ Создать базовый интерфейс `IChatSource`
4. ✅ Написать unit-тесты для моделей

**Файлы:**
- `backend/app/services/whatsapp/parsing/models/__init__.py`
- `backend/app/services/whatsapp/parsing/models/chat_dto.py`
- `backend/app/services/whatsapp/parsing/models/parsing_result.py`
- `backend/app/services/whatsapp/parsing/models/raw_chat.py`

---

### Этап 2: Реализация источников данных (3-4 дня)

**Задачи:**
1. ✅ Реализовать `StoreChatSource` (приоритетный)
   - Исследовать структуру `window.Store` в WhatsApp Web
   - Реализовать доступ к `Store.Chat.models`
   - Извлечение `total_chat_count`
   
2. ✅ Реализовать `CDPNetworkChatSource`
   - Настроить CDP сессию
   - Перехватить network requests
   - Парсинг protobuf/JSON payloads
   
3. ✅ Реализовать `DOMChatSource` (рефакторинг текущего кода)
   - Вынести логику из `ChatParser._parse_all_visible_chats`
   - Адаптировать под интерфейс `IChatSource`
   
4. ✅ Реализовать `SourceSelector`
   - Логика выбора источника по приоритету
   - Логирование причин переключения

**Файлы:**
- `backend/app/services/whatsapp/parsing/sources/__init__.py`
- `backend/app/services/whatsapp/parsing/sources/base.py`
- `backend/app/services/whatsapp/parsing/sources/store_chat_source.py`
- `backend/app/services/whatsapp/parsing/sources/cdp_network_chat_source.py`
- `backend/app/services/whatsapp/parsing/sources/dom_chat_source.py`
- `backend/app/services/whatsapp/parsing/sources/source_selector.py`

---

### Этап 3: Нормализация и идентификация (2 дня)

**Задачи:**
1. ✅ Реализовать `ChatNormalizer`
   - Преобразование `RawChat` → `ChatDTO`
   - Определение типа чата (personal/group/broadcast)
   - Определение integrity статуса
   
2. ✅ Реализовать `IdentityResolver`
   - Извлечение ID из разных источников
   - Детекция аномалий (расхождения данных)
   - Валидация уникальности ID

**Файлы:**
- `backend/app/services/whatsapp/parsing/normalizers/__init__.py`
- `backend/app/services/whatsapp/parsing/normalizers/chat_normalizer.py`
- `backend/app/services/whatsapp/parsing/identity/__init__.py`
- `backend/app/services/whatsapp/parsing/identity/identity_resolver.py`

---

### Этап 4: Контроль завершения и публикация (1-2 дня)

**Задачи:**
1. ✅ Реализовать `CompletionController`
   - Детерминированные критерии завершения
   - Вычисление `missing_ids`
   - Определение completeness статуса
   
2. ✅ Реализовать `ResultPublisher`
   - Стриминг промежуточных результатов
   - Формирование финального `ParsingResult`

**Файлы:**
- `backend/app/services/whatsapp/parsing/completion/__init__.py`
- `backend/app/services/whatsapp/parsing/completion/completion_controller.py`
- `backend/app/services/whatsapp/parsing/publishers/__init__.py`
- `backend/app/services/whatsapp/parsing/publishers/result_publisher.py`

---

### Этап 5: Оркестратор и интеграция (2-3 дня)

**Задачи:**
1. ✅ Реализовать `ChatParsingOrchestrator`
   - Координация всех компонентов
   - Основной метод `parse_chats_streaming()`
   - Обработка ошибок и деградации
   
2. ✅ Интегрировать в `WhatsAppConnectService`
   - Заменить `ChatParser` на `ChatParsingOrchestrator`
   - Адаптировать API методы
   - Сохранить обратную совместимость
   
3. ✅ Обновить API endpoints
   - Адаптировать под новый формат `ParsingResult`
   - Обновить SSE события

**Файлы:**
- `backend/app/services/whatsapp/parsing/__init__.py`
- `backend/app/services/whatsapp/parsing/orchestrator.py`
- `backend/app/services/whatsapp/whatsapp_service.py` (обновление)
- `backend/app/api/whatsapp.py` (обновление)

---

### Этап 6: Тестирование и документация (2-3 дня)

**Задачи:**
1. ✅ Unit-тесты для каждого модуля
2. ✅ Integration-тесты для оркестратора
3. ✅ Тесты деградации (fallback между источниками)
4. ✅ Обновить документацию
5. ✅ Миграционный гайд

**Файлы:**
- `backend/tests/services/whatsapp/parsing/` (тесты)
- `backend/app/services/whatsapp/parsing/README.md`
- `backend/app/services/whatsapp/parsing/MIGRATION.md`

---

### Этап 7: Рефакторинг и оптимизация (1-2 дня)

**Задачи:**
1. ✅ Удалить старый `ChatParser`
2. ✅ Очистить неиспользуемый код
3. ✅ Оптимизация производительности
4. ✅ Финальный code review

---

## 📝 Детали реализации ключевых компонентов

### StoreChatSource - Исследование структуры

**Шаг 1: Исследование**
```javascript
// В page.evaluate()
const store = window.Store || window.WWebJS;
console.log('Store keys:', Object.keys(store));
console.log('Chat models:', store.Chat?.models);
console.log('Total count:', store.Chat?.models?.length);
```

**Шаг 2: Извлечение данных**
```javascript
const chats = store.Chat.models.map(chat => ({
    jid: chat.id?._serialized || chat.id,
    name: chat.name || chat.contact?.name,
    isGroup: chat.isGroup,
    unreadCount: chat.unreadCount,
    // ... другие поля
}));
```

### CDPNetworkChatSource - Перехват network

**Шаг 1: Настройка CDP**
```python
cdp_session = await page.context.new_cdp_session(page)
await cdp_session.send('Network.enable')

# Подписываемся на события
async def handle_response(event):
    if 'chat' in event.get('response', {}).get('url', ''):
        # Парсим payload
        pass

cdp_session.on('Network.responseReceived', handle_response)
```

**Шаг 2: Парсинг protobuf**
- Использовать библиотеку для декодирования protobuf
- Или парсить JSON если доступен

### IdentityResolver - Надежная идентификация

**Приоритет источников ID:**
1. `raw_chat.jid` (из Store)
2. `raw_chat.wid` (из Store)
3. `raw_chat.id.server_id` (из Network)
4. `raw_chat.user_id` (из Network)

**Запрещено:**
- ❌ Regex на номер телефона из aria-label
- ❌ Извлечение из textContent
- ❌ Использование title атрибута

---

## 🧪 Стратегия тестирования

### Unit-тесты

**Для каждого источника:**
- Mock Page/CDP session
- Тест `init()`, `fetch_batch()`, `is_complete()`, `total_expected()`

**Для нормализатора:**
- Тест преобразования RawChat → ChatDTO
- Тест определения типа чата
- Тест integrity статусов

**Для IdentityResolver:**
- Тест извлечения ID из разных источников
- Тест детекции аномалий

### Integration-тесты

**Сценарии:**
1. Store источник работает → получаем все чаты
2. Store недоступен → fallback на CDP
3. CDP недоступен → fallback на DOM
4. Частичный результат → корректный completeness статус
5. Аномалии → корректное логирование

---

## 📊 Метрики успеха

### Функциональные:
- ✅ Все чаты извлекаются (100% completeness)
- ✅ ID извлекаются надежно (не из aria-label)
- ✅ Детерминированное завершение (не эвристики)
- ✅ Fallback работает при недоступности Store

### Качественные:
- ✅ Код разделен на модули (< 200 строк на модуль)
- ✅ Каждый модуль тестируем изолированно
- ✅ Логирование причин выбора источника
- ✅ Детекция и отчет об аномалиях

---

## 🚨 Риски и митигация

### Риск 1: Store структура изменится
**Митигация:**
- Документировать структуру
- Fallback на CDP/DOM
- Версионирование парсера Store

### Риск 2: CDP payloads зашифрованы
**Митигация:**
- Использовать Store как основной источник
- DOM как надежный fallback

### Риск 3: Производительность
**Митигация:**
- Store быстрее DOM (нет скролла)
- Кэширование результатов
- Оптимизация batch размеров

---

## 📅 Оценка времени

**Общая оценка: 12-16 дней**

- Этап 1: 1-2 дня
- Этап 2: 3-4 дня (самый сложный - исследование Store/CDP)
- Этап 3: 2 дня
- Этап 4: 1-2 дня
- Этап 5: 2-3 дня
- Этап 6: 2-3 дня
- Этап 7: 1-2 дня

---

## ✅ Чеклист готовности

### Перед началом:
- [ ] Согласован план с командой
- [ ] Создана ветка для рефакторинга
- [ ] Исследована структура window.Store в WhatsApp Web
- [ ] Протестирован доступ к CDP через Playwright

### После завершения:
- [ ] Все тесты проходят
- [ ] Документация обновлена
- [ ] Code review пройден
- [ ] Миграция на production протестирована
- [ ] Старый код удален

---

## 🔗 Связанные документы

- `CHAT_PARSING_ANALYSIS.md` - анализ текущей реализации
- `backend/app/services/whatsapp/chat_parser.py` - текущий код (будет удален)
- Требования к реализации (в запросе пользователя)

---

## 📌 Следующие шаги

1. **Согласовать план** с командой
2. **Начать с Этапа 1** - создание моделей и интерфейсов
3. **Параллельно исследовать** структуру window.Store в WhatsApp Web
4. **Итеративно реализовывать** каждый этап с тестами


