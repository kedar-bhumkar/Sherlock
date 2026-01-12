# Sherlock Frontend

A React-based frontend for the Sherlock Image Knowledge Extraction System.

## Features

- Three-column layout with Header, Sidebar Navigation, and Content Grid
- Collapsible category tree navigation
- Image thumbnail grid with pagination
- Modal view for detailed knowledge item inspection
- Responsive design with minimal, clean UI
- Type-safe with TypeScript
- Integration with FastAPI backend

## Tech Stack

- **React 18** with TypeScript
- **Vite** for fast development and building
- **Lucide React** for consistent iconography
- **CSS Modules** for component styling

## Project Structure

```
frontend/
├── src/
│   ├── components/       # React components
│   │   ├── Header.tsx
│   │   ├── Sidebar.tsx
│   │   ├── ContentGrid.tsx
│   │   ├── Modal.tsx
│   │   └── Pagination.tsx
│   ├── hooks/           # Custom React hooks
│   │   ├── useKnowledge.ts
│   │   └── useModal.ts
│   ├── services/        # API client and data fetching
│   │   └── api.ts
│   ├── types/           # TypeScript type definitions
│   │   └── index.ts
│   ├── utils/           # Helper functions and constants
│   │   ├── constants.ts
│   │   └── helpers.ts
│   ├── App.tsx          # Main application component
│   ├── main.tsx         # Application entry point
│   └── index.css        # Global styles
├── public/              # Static assets
├── index.html           # HTML template
├── vite.config.ts       # Vite configuration
└── package.json         # Dependencies and scripts
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8000`

### Installation

1. Install dependencies:
```bash
npm install
```

2. Configure environment variables (optional):
```bash
cp .env.example .env
```

Edit `.env` to configure the API base URL if needed.

### Development

Start the development server:
```bash
npm run dev
```

The application will be available at `http://localhost:3000`.

### Building for Production

Build the production bundle:
```bash
npm run build
```

The built files will be in the `dist/` folder.

### Preview Production Build

Preview the production build locally:
```bash
npm run preview
```

## Components Overview

### Header
App branding with Sherlock name, icon, and global actions (settings).

### Sidebar
Tree-style category/subcategory navigation with collapsible sections. Allows filtering of knowledge items.

**Categories:**
- Design (documentation, architecture, other)
- Code (frontend, backend, other)
- Domain (clinical, non clinical, other)
- Misc (roadmap, strategy, performance, other)

### ContentGrid
Displays image thumbnails in a responsive grid layout with:
- Image preview
- Title and category badges
- Pagination controls
- Loading and error states

### Modal
Full-screen modal view for knowledge items with:
- Full-size image display
- Two-column layout for raw and paraphrased data
- Metadata (category, subcategory, timestamps)
- Status indicators for failed/processing items

### Pagination
Smart pagination component with:
- First/previous/next/last navigation
- Page number buttons
- Ellipsis for large page counts

## API Integration

The frontend communicates with the backend via the following endpoints:

### GET /api/knowledge
Fetch knowledge items with filters and pagination.

**Query Parameters:**
- `category` - Filter by category (default: "All")
- `subcategory` - Filter by subcategory (default: "All")
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20)

**Response:**
```json
{
  "data": [...],
  "metadata": {
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  }
}
```

## Styling

The application uses a minimal, clean design with:
- Custom CSS for each component
- Global CSS variables for consistent theming
- Responsive design patterns
- Smooth transitions and animations
- Custom scrollbar styling

### Color Scheme
- Primary: Purple gradient (#667eea to #764ba2)
- Background: Light gray (#f8f9fa)
- Text: Dark gray (#212529)
- Borders: Light gray (#dee2e6)

## Keyboard Navigation

- Arrow keys to navigate through grid items
- Enter/Space to open modal
- Escape to close modal
- Tab for focus navigation

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

## Future Enhancements

- Settings modal for configuration
- Bulk operations (retry, delete)
- Advanced search and filtering
- Real-time updates via WebSocket
- Image upload interface
- RAG query interface

## License

Part of the Sherlock Image Knowledge Extraction System.
