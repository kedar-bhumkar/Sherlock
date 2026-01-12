# Sherlock Frontend - Project Structure

## Complete File Tree

```
frontend/
├── public/                          # Static assets
│   └── vite.svg
├── src/
│   ├── components/                  # React UI components
│   │   ├── Header.tsx              # App header with branding
│   │   ├── Header.css
│   │   ├── Sidebar.tsx             # Category navigation tree
│   │   ├── Sidebar.css
│   │   ├── ContentGrid.tsx         # Image thumbnail grid
│   │   ├── ContentGrid.css
│   │   ├── Pagination.tsx          # Pagination controls
│   │   ├── Pagination.css
│   │   ├── Modal.tsx               # Detail view modal
│   │   ├── Modal.css
│   │   └── index.ts                # Component exports
│   │
│   ├── hooks/                       # Custom React hooks
│   │   ├── useKnowledge.ts         # Hook for fetching knowledge items
│   │   ├── useModal.ts             # Hook for modal state management
│   │   └── index.ts                # Hook exports
│   │
│   ├── services/                    # API integration layer
│   │   └── api.ts                  # API client functions
│   │
│   ├── types/                       # TypeScript type definitions
│   │   └── index.ts                # All type definitions
│   │
│   ├── utils/                       # Utility functions
│   │   ├── constants.ts            # App constants and categories
│   │   └── helpers.ts              # Helper functions
│   │
│   ├── App.tsx                      # Main application component
│   ├── App.css                      # App layout styles
│   ├── main.tsx                     # Application entry point
│   └── index.css                    # Global styles and CSS variables
│
├── .env                             # Environment variables
├── .env.example                     # Environment variables template
├── .gitignore                       # Git ignore rules
├── index.html                       # HTML template
├── package.json                     # Dependencies and scripts
├── README.md                        # Frontend documentation
├── tsconfig.json                    # TypeScript configuration
├── tsconfig.node.json               # TypeScript Node configuration
└── vite.config.ts                   # Vite configuration

```

## Component Hierarchy

```
App
├── Header
│   └── Settings Button
│
├── App Layout
│   ├── Sidebar
│   │   ├── All Categories
│   │   └── Category Tree
│   │       ├── Category (collapsible)
│   │       └── Subcategories
│   │
│   └── Main Content
│       └── ContentGrid
│           ├── Loading State
│           ├── Error State
│           ├── Empty State
│           └── Content Cards
│               └── Pagination
│
└── Modal (conditional)
    ├── Header with Metadata
    ├── Image Display
    └── Two-Column Data View
        ├── Raw Data
        └── Paraphrased Data
```

## Data Flow

```
User Interaction
      ↓
Category Selection (Sidebar)
      ↓
Update Filter State (App)
      ↓
useKnowledge Hook
      ↓
API Call (services/api.ts)
      ↓
Backend API (GET /api/knowledge)
      ↓
Response with Data + Metadata
      ↓
Update Component State
      ↓
Render ContentGrid
      ↓
User Clicks Item
      ↓
Open Modal with Item Details
```

## Key Features by Component

### Header
- App branding with Sherlock logo
- Settings button placeholder
- Gradient background styling

### Sidebar
- Tree-style category navigation
- Collapsible sections
- Active state highlighting
- "All Categories" filter option
- Pre-configured categories:
  - Design (documentation, architecture, other)
  - Code (frontend, backend, other)
  - Domain (clinical, non clinical, other)
  - Misc (roadmap, strategy, performance, other)

### ContentGrid
- Responsive grid layout
- Image thumbnails with category badges
- Loading spinner state
- Error message display
- Empty state messaging
- Hover effects and animations

### Pagination
- First/Previous/Next/Last navigation
- Smart page number display with ellipsis
- Disabled state handling
- Keyboard accessible

### Modal
- Full-screen overlay
- Image display with external link
- Two-column data comparison (raw vs paraphrased)
- Metadata badges
- Status indicators for failed/processing items
- Keyboard navigation (ESC to close)
- Click outside to close

## State Management

### App Level State
- `selectedCategory` - Current category filter
- `selectedSubcategory` - Current subcategory filter
- `currentPage` - Pagination state

### Hook State (useKnowledge)
- `data` - Array of knowledge items
- `metadata` - Pagination metadata
- `loading` - Loading state
- `error` - Error state

### Hook State (useModal)
- `isOpen` - Modal visibility
- `data` - Selected item data

## API Integration

### Endpoints Used
1. `GET /api/knowledge` - Fetch filtered and paginated knowledge items

### Request Parameters
- `category` - Filter by category (optional)
- `subcategory` - Filter by subcategory (optional)
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20)

### Response Structure
```typescript
{
  data: KnowledgeItem[],
  metadata: {
    total: number,
    page: number,
    page_size: number,
    total_pages: number
  }
}
```

## Styling Approach

### Global Styles (index.css)
- CSS custom properties for theming
- Typography system
- Reset and normalize
- Utility classes
- Scrollbar styling

### Component Styles
- Dedicated CSS file per component
- BEM-like naming convention
- Consistent spacing and colors
- Responsive design patterns
- Hover and focus states

### Color Palette
- Primary: #667eea (Purple)
- Primary Dark: #764ba2 (Dark Purple)
- Background: #f8f9fa (Light Gray)
- Text Primary: #212529 (Dark Gray)
- Text Secondary: #6c757d (Medium Gray)
- Border: #dee2e6 (Light Gray)
- Error: #dc3545 (Red)

## TypeScript Types

### Main Interfaces
- `KnowledgeItem` - Individual knowledge record
- `PaginationMetadata` - Pagination information
- `KnowledgeResponse` - API response structure
- `Category` - Category configuration
- `ApiError` - Error structure

## Development Workflow

1. Install dependencies: `npm install`
2. Start dev server: `npm run dev`
3. Access at: `http://localhost:3000`
4. Backend proxy: `/api` → `http://localhost:8000`

## Build and Deploy

1. Build: `npm run build`
2. Output: `dist/` folder
3. Preview: `npm run preview`
4. Deploy: Upload `dist/` to hosting service
