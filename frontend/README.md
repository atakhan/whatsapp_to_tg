# WhatsApp → Telegram Migrator Frontend

Vue 3 + TypeScript + Vite frontend for the WhatsApp to Telegram migration service.

## Tech Stack

- **Vue 3** - Progressive JavaScript framework
- **TypeScript** - Type-safe JavaScript
- **Vite** - Fast build tool and dev server
- **Vue Router** - Official router for Vue.js
- **Vanilla CSS** - Custom styling with CSS variables

## Project Structure

```
frontend/
├── src/
│   ├── pages/          # Page components (7 steps of migration flow)
│   ├── components/     # Reusable components (ProgressBar, etc.)
│   ├── router.ts      # Vue Router configuration
│   ├── store.ts       # Reactive state management
│   ├── styles.css     # Global CSS styles
│   ├── main.ts        # Application entry point
│   └── App.vue        # Root component
├── index.html         # HTML entry point
├── vite.config.ts     # Vite configuration
└── package.json       # Dependencies and scripts
```

## Development

### Prerequisites

- Node.js 18+ and npm

### Installation

```bash
npm install
```

### Development Server

Start the development server:

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Build

Build for production:

```bash
npm run build
```

The production build will be in the `dist/` directory.

### Preview Production Build

Preview the production build locally:

```bash
npm run preview
```

## Migration Flow

The application implements a 7-step migration flow:

1. **Landing** (`/`) - Welcome page with CTA
2. **Connect WhatsApp** (`/whatsapp`) - QR code for WhatsApp Web connection
3. **Select Chats** (`/select`) - Choose WhatsApp chats to migrate
4. **Authorize Telegram** (`/telegram`) - Telegram authentication
5. **Map Chats** (`/map`) - Map WhatsApp chats to Telegram destinations
6. **Migration** (`/migrate`) - Progress tracking during migration
7. **Completion** (`/done`) - Success page with report download

## State Management

The app uses a simple reactive store (`src/store.ts`) built with Vue's `reactive()` API. It manages:

- WhatsApp session and chat list
- Selected chats
- Telegram session and chat list
- Chat mappings
- Migration progress and reports

## Styling

Global styles are defined in `src/styles.css` using CSS variables for theming. The design uses:

- Gradient backgrounds
- Card-based layouts
- Responsive design (mobile-friendly)
- Consistent button styles
- Progress indicators

## API Integration

The frontend is configured to proxy API requests to the backend:

- Development: `http://localhost:8000` (configurable via `VITE_API_URL`)
- Proxy path: `/api/*`

## TypeScript

The project is fully typed with TypeScript. Type definitions are included for:

- Store state and actions
- Router routes
- Component props
- API responses (to be added)

