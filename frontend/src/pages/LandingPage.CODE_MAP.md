# Карта кода: LandingPage.vue

**Размер файла:** ~3163 строк  
**Дата создания карты:** 2025-01-XX

---

## 📋 Содержание

1. [Template структура](#template-структура)
2. [Импорты и зависимости](#импорты-и-зависимости)
3. [Константы](#константы)
4. [Состояние (State)](#состояние-state)
5. [Интерфейсы и типы](#интерфейсы-и-типы)
6. [Функции и методы](#функции-и-методы)
7. [Lifecycle hooks](#lifecycle-hooks)
8. [Стили (CSS)](#стили-css)
9. [Кандидаты на рефакторинг](#кандидаты-на-рефакторинг)

---

## 🎨 Template структура

### Основные секции (в порядке отображения):

```
LandingPage.vue
├── StarsBackground (компонент) ✅ ВЫНЕСЕНО
├── Background logs container (строки 6-20)
│   └── Логи загрузки сообщений (дизайн-элемент)
├── RocketShip (компонент) ✅ ВЫНЕСЕНО
│   └── Физика ракеты через useRocketPhysics
├── WhatsApp Chat Circles (строки 25-43)
│   ├── v-for по visibleChats
│   ├── Позиционирование: getChatCircleStyle()
│   └── Состояния: visible, selected, dimmed, moving-to-corner
├── Loading chats message (строки 45-48)
├── Chat selection title (строки 50-56)
├── Chat search form (строки 58-70)
│   └── filterChatsBySearch()
├── Selected chat name (строки 72-79)
├── Selected chat panel (строки 81-96)
│   └── Кнопки: Назад, Перенести в телеграм
├── MessagesList (компонент) ✅ ВЫНЕСЕНО
│   └── useMessages composable
├── Destination selection panel (строки 108-144)
│   ├── Выбранный WhatsApp чат
│   ├── Загрузка Telegram чатов
│   └── Кнопка "Начать перенос"
├── Telegram Chat Circles (строки 146-161)
│   ├── v-for по visibleTelegramChats
│   └── Позиционирование: getTelegramChatCircleStyle()
├── Header section (строки 163-167)
│   ├── Badge "TETRAKOM"
│   └── Title "Миграция чатов"
├── Split screen wrapper (строки 169-336)
│   ├── WhatsApp section
│   │   ├── Planet (строки 174-229)
│   │   │   ├── Логотип WhatsApp
│   │   │   └── Overlay (строки 189-228)
│   │   │       ├── Connect prompt
│   │   │       ├── Loading state
│   │   │       ├── QR Code
│   │   │       ├── Connected state
│   │   │       └── Error state
│   │   └── Title & Description
│   └── Telegram section
│       ├── Planet (строки 244-325)
│       │   ├── Логотип Telegram
│       │   └── Auth overlay (строки 259-324)
│       │       ├── Connect prompt
│       │       ├── Phone input
│       │       ├── Code input
│       │       ├── Password input
│       │       └── Connected state
│       └── Title & Description
└── Launch button (строки 338-344)
```

---

## 📦 Импорты и зависимости

### Vue Core
- `onMounted`, `onUnmounted`, `ref`, `computed`

### Компоненты
- ✅ `StarsBackground` (components/landing/StarsBackground.vue)
- ✅ `RocketShip` (components/RocketShip.vue)
- ✅ `MessagesList` (components/landing/MessagesList.vue)

### Composables
- ✅ `useRocketPhysics` (composables/useRocketPhysics.ts)
- ✅ `useMessages` (composables/useMessages.ts)

### Константы
- `PLANET_VISUAL` (constants/rocketConstants.ts)
- `ANIMATION`, `MESSAGES`, `POLLING` (constants/landingConstants.ts)

### Утилиты
- `shadowForPlanet` (utils/rocketUtils.ts)

### Внешние зависимости
- `api` (api/client)
- `store` (store)

---

## 🔧 Константы

### UI_SIZES (строки 365-382)
```typescript
{
  CHAT_CIRCLE_SIZE: 52,
  PLANET_SHRUNK_SIZE: 105,
  RING_GAP: 20,
  TG_CHAT_CIRCLE_SIZE: 52,
  TG_PLANET_SHRUNK_SIZE: 70,
  TG_RING_GAP: 20,
  SHIP_SCALE: 3.5,
  TOP_PADDING: 24,
  CRUISE_ALTITUDE_MIN: 80,
  CRUISE_ALTITUDE_MAX: 220,
  CRUISE_ALTITUDE_RATIO: 0.22,
}
```

### Transliteration Maps (строки 893-920)
- `transliterationMap`: Russian → Latin
- `reverseTransliterationMap`: Latin → Russian

---

## 📊 Состояние (State)

### DOM Refs
- `planetWa` (HTMLElement) - WhatsApp планета
- `planetTg` (HTMLElement) - Telegram планета

### Migration Animation State
- `migrationStarted` (boolean)
- `hideStage` (0-6) - контроль скрытия элементов
- `whatsappCentered` (boolean)
- `showWaOverlay` (boolean)
- `whatsappShrunk` (boolean)
- `whatsappInCorner` (boolean)
- `telegramCentered` (boolean)
- `telegramShrunk` (boolean)

### Rocket Physics (через composable)
- `shipState`, `flightState`, `missionState`, `gravityViz`
- `waBoxShadow`, `tgBoxShadow` - тени планет

### WhatsApp Connection State
- `waStatus`: 'idle' | 'loading' | 'qr' | 'connecting' | 'connected'
- `qrCode` (string | null)
- `waError` (string | null)
- `waSessionId` (string | null)
- `whatsappStatusMessage` (string)
- `statusPollInterval` (number | null)

### Chats State
- `chatsLoading` (boolean)
- `chats` (Chat[]) - все чаты
- `visibleChats` (Chat[]) - видимые чаты (после фильтрации)
- `selectedChat` (Chat | null)
- `chatMovingToCorner` (boolean)
- `chatSearchQuery` (string)

### Messages State (через useMessages composable)
- `showMessages` (boolean)
- `messages`, `messagesLoading`, `messagesProgress`, `messagesLogs`

### Telegram Connection State
- `tgPhase`: 'hidden' | 'entering' | 'phone' | 'code' | 'password' | 'connected'
- `tgPhone`, `tgCode`, `tgPassword` (string)
- `tgPhoneCodeHash` (string | null)
- `tgSessionId` (string | null)
- `tgError` (string | null)
- `tgLoading` (boolean)
- `tgUserInfo` (any)

### Telegram Chats State
- `showDestinationSelection` (boolean)
- `destinationType`: 'saved' | 'existing' | 'new_group' | null
- `telegramChats` (TelegramChat[])
- `visibleTelegramChats` (TelegramChat[])
- `telegramChatsLoading` (boolean)
- `telegramChatsError` (string | null)
- `selectedTelegramChat` (TelegramChat | null)
- `newGroupName` (string)

### Event Sources & Timeouts
- `chatsEventSource` (EventSource | null)
- `activeTimeouts` (number[])

---

## 🏷️ Интерфейсы и типы

### Chat (строки 440-445)
```typescript
interface Chat {
  id: string
  name: string
  avatar: string | null
  visible: boolean
}
```

### TelegramChat (строки 511-515)
```typescript
interface TelegramChat {
  id: string
  name: string
  visible: boolean
}
```

---

## ⚙️ Функции и методы

### Migration Flow
- `startMigration()` - запуск миграции, анимация скрытия элементов
- `onAnyLeftClick()` - обработчик клика для запуска миссии

### Planet Click Handlers
- `onWhatsAppPlanetClick()` - клик по WhatsApp планете
- `onTelegramPlanetClick()` - клик по Telegram планете

### WhatsApp Connection
- `startWhatsAppAuth()` - начало авторизации WhatsApp
- `startWhatsAppConnection()` - подключение к WhatsApp
  - Проверка существующих сессий
  - Создание новой сессии
  - Обработка QR-кода
- `startStatusPolling()` - опрос статуса подключения
- `stopStatusPolling()` - остановка опроса
- `retryConnection()` - повторная попытка подключения
- `onWhatsAppConnected()` - обработка успешного подключения
- `restoreWhatsAppSession()` - восстановление сохраненной сессии

### Chats Management
- `loadChats()` - загрузка чатов через SSE
- `getChatCircleStyle(index)` - расчет позиции чата в орбите
- `getChatsPerRing(ringIndex)` - расчет количества чатов в кольце
- `getChatInitial(name)` - получение первой буквы имени
- `selectChat(chat)` - выбор чата
- `onAvatarError(event, chat)` - обработка ошибки загрузки аватара

### Chat Search & Filtering
- `transliterateToLatin(text)` - транслитерация RU → EN
- `transliterateToRussian(text)` - транслитерация EN → RU
- `getSearchVariants(text)` - получение вариантов поиска
- `normalizeString(str)` - нормализация строки
- `matchesAnyVariant(chatName, queryVariants)` - проверка совпадения
- `isChatMatch(chatName, query)` - проверка совпадения с fuzzy match
- `filterChatsBySearch()` - фильтрация чатов по поисковому запросу

### Chat Selection Flow
- `proceedWithSelectedChat()` - продолжение с выбранным чатом
- `goBackToChatSelection()` - возврат к выбору чата
- `goBackToWhatsAppChats()` - возврат к WhatsApp чатам

### Messages Flow
- `loadAndShowMessages()` - загрузка и отображение сообщений
- `proceedToTelegramAuth()` - переход к авторизации Telegram

### Telegram Connection
- `startTelegramAuth()` - начало авторизации Telegram
- `sendTelegramCode()` - отправка кода
- `verifyTelegramCode()` - проверка кода
- `verifyTelegramPassword()` - проверка пароля 2FA
- `onTelegramConnected()` - обработка успешной авторизации
- `restoreTelegramSession()` - восстановление сохраненной сессии

### Telegram Chats
- `loadTelegramChats()` - загрузка Telegram чатов
- `animateTelegramChatsAppearing()` - анимация появления чатов
- `getTelegramChatCircleStyle(index)` - расчет позиции Telegram чата
- `getTelegramChatsPerRing(ringIndex)` - расчет количества Telegram чатов в кольце
- `selectTelegramChat(chat)` - выбор Telegram чата

### Migration
- `canStartMigration` (computed) - можно ли начать миграцию
- `startDataMigration()` - начало миграции данных

---

## 🔄 Lifecycle hooks

### onMounted (строки 1576-1596)
1. Инициализация физики ракеты
2. Подписка на клики мыши
3. Спавн ракеты над WhatsApp
4. Запуск физики
5. Восстановление сохраненных сессий (WhatsApp, Telegram)

### onUnmounted (строки 1598-1615)
1. Отписка от событий мыши
2. Остановка физики
3. Остановка опроса статуса
4. Закрытие EventSource соединений
5. Очистка всех setTimeout

---

## 🎨 Стили (CSS)

### Основные секции стилей:

1. **Kurzgesagt Palette** (CSS переменные)
2. **Landing Page** - основной контейнер
3. **Space Traffic SVG** - стили для ракеты
4. **Header Section** - заголовок страницы
5. **Split Screen Layout** - разделенный экран
6. **Planet Styles** - стили планет (WhatsApp, Telegram)
   - Размеры, позиционирование
   - Состояния: centered, shrunk, corner, exiting
   - Overlay стили
7. **Chat Circles** - стили чатов
   - WhatsApp chat circles
   - Telegram chat circles
   - Состояния: visible, selected, dimmed, moving-to-corner
8. **Chat Selection UI**
   - Search input
   - Selection title
   - Selected chat name
   - Selected chat panel
9. **Destination Selection Panel**
10. **Messages styles** ✅ ПЕРЕНЕСЕНО в MessagesList.vue
11. **Background Logs** - стили логов
12. **Buttons** - различные кнопки (launch, back, next, continue)
13. **Animations** - keyframes и transitions

---

## 🎯 Кандидаты на рефакторинг

### ✅ Уже вынесено:
1. **StarsBackground** - компонент + composable + константы
2. **RocketShip** - компонент + composable + константы + утилиты
3. **MessagesList** - компонент + composable + утилиты

### 🔍 Следующие кандидаты:

#### 1. **Chat Circles (WhatsApp + Telegram)** ⭐ РЕКОМЕНДУЕТСЯ
**Размер:** ~40 строк template + ~100 строк логики  
**Проблемы:**
- Дублирование кода между WhatsApp и Telegram чатами
- Логика позиционирования (`getChatCircleStyle`, `getTelegramChatCircleStyle`)
- Похожие стили

**Что вынести:**
- Компонент `ChatOrbit.vue` (универсальный для обоих типов)
- Composable `useChatOrbit.ts` (логика позиционирования)
- Утилиты `chatOrbitUtils.ts` (расчет позиций)

**Выгода:** Устранение дублирования, ~150 строк кода

---

#### 2. **Background Logs**
**Размер:** ~15 строк template  
**Проблемы:** Простой компонент, но быстро вынести

**Что вынести:**
- Компонент `BackgroundLogs.vue`

**Выгода:** Быстро, ~20 строк кода

---

#### 3. **Planet Components (WhatsApp + Telegram)**
**Размер:** ~150 строк template + логика подключения  
**Проблемы:**
- Большой блок с оверлеями
- Тесно связан с логикой подключения
- Дублирование между WhatsApp и Telegram

**Что вынести:**
- Компонент `Planet.vue` (универсальный)
- Composable `usePlanetConnection.ts` (логика подключения)
- Компоненты оверлеев: `WhatsAppOverlay.vue`, `TelegramOverlay.vue`

**Выгода:** ~200+ строк кода, но сложнее из-за связи с логикой

---

#### 4. **Chat Search & Filtering**
**Размер:** ~200 строк логики  
**Проблемы:** Большая логика поиска с транслитерацией

**Что вынести:**
- Composable `useChatSearch.ts`
- Утилиты `transliterationUtils.ts`
- Утилиты `searchUtils.ts`

**Выгода:** ~200 строк кода, изоляция сложной логики

---

#### 5. **Destination Selection Panel**
**Размер:** ~40 строк template  
**Проблемы:** Отдельная секция UI

**Что вынести:**
- Компонент `DestinationSelectionPanel.vue`

**Выгода:** ~50 строк кода

---

#### 6. **WhatsApp Connection Logic**
**Размер:** ~300 строк логики  
**Проблемы:** Большая логика подключения

**Что вынести:**
- Composable `useWhatsAppConnection.ts`
- Утилиты для работы с сессиями

**Выгода:** ~300 строк кода, изоляция сложной логики

---

#### 7. **Telegram Connection Logic**
**Размер:** ~200 строк логики  
**Проблемы:** Логика авторизации Telegram

**Что вынести:**
- Composable `useTelegramConnection.ts`
- Компонент `TelegramAuthForm.vue`

**Выгода:** ~200 строк кода

---

## 📈 Статистика

- **Всего строк:** ~3163
- **Template:** ~345 строк
- **Script:** ~1270 строк
- **Style:** ~1548 строк
- **Уже вынесено:** ~400+ строк (Stars, Rocket, Messages)
- **Потенциал для выноса:** ~1000+ строк

---

## 🔗 Зависимости между секциями

```
LandingPage
├── StarsBackground (независимый)
├── RocketShip ← useRocketPhysics
│   └── Зависит от: planetWa, planetTg, hideStage
├── MessagesList ← useMessages
│   └── Зависит от: waSessionId, selectedChat
├── WhatsApp Chat Circles
│   ├── Зависит от: visibleChats, selectedChat
│   └── Использует: getChatCircleStyle()
├── Telegram Chat Circles
│   ├── Зависит от: visibleTelegramChats, selectedTelegramChat
│   └── Использует: getTelegramChatCircleStyle()
├── WhatsApp Planet
│   ├── Зависит от: waStatus, whatsappCentered, whatsappShrunk
│   └── Использует: startWhatsAppConnection()
└── Telegram Planet
    ├── Зависит от: tgPhase, telegramCentered, telegramShrunk
    └── Использует: startTelegramAuth()
```

---

## 💡 Рекомендации по приоритетам

1. **Высокий приоритет:**
   - Chat Circles (дублирование, переиспользование)
   - Chat Search & Filtering (сложная логика)

2. **Средний приоритет:**
   - Planet Components (большой блок, но сложная связь)
   - WhatsApp/Telegram Connection Logic (изоляция сложности)

3. **Низкий приоритет:**
   - Background Logs (простой, но быстро)
   - Destination Selection Panel (небольшой блок)

---

*Карта обновлена после выноса: Stars, Rocket, Messages*

