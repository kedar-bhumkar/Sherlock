# Sherlock Frontend - Quick Start Guide

## Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8000`

## Installation and Setup

### 1. Install Dependencies

```bash
npm install
```

This will install all required dependencies:
- React 18.3.1
- Lucide React (icons)
- Vite (build tool)
- TypeScript

### 2. Configure Environment (Optional)

Copy the example environment file:

```bash
cp .env.example .env
```

Default configuration:
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_NAME=Sherlock
VITE_APP_DESCRIPTION=Image Knowledge Extraction System
```

### 3. Start Development Server

```bash
npm run dev
```

The application will be available at:
- Frontend: `http://localhost:3000`
- API Proxy: `http://localhost:3000/api` → `http://localhost:8000/api`

### 4. Build for Production

```bash
npm run build
```

Output will be in the `dist/` folder.

### 5. Preview Production Build

```bash
npm run preview
```

## Using the Application

### Navigation

1. **Sidebar Navigation**
   - Click "All Categories" to view all items
   - Expand/collapse categories using chevron icons
   - Click category name to view all items in that category
   - Click subcategory to filter by specific subcategory

2. **Content Grid**
   - Browse image thumbnails
   - View title and category badges
   - Use pagination controls at the bottom
   - Click any card to view full details

3. **Detail Modal**
   - View full-size image
   - Compare raw data vs paraphrased data
   - See metadata (category, subcategory, timestamp)
   - Close with X button or ESC key

### Keyboard Shortcuts

- `Tab` - Navigate between elements
- `Enter` / `Space` - Activate buttons and cards
- `ESC` - Close modal
- Arrow keys work in pagination

## Project Structure Overview

```
src/
├── components/      # UI components (Header, Sidebar, ContentGrid, Modal)
├── hooks/          # Custom React hooks (useKnowledge, useModal)
├── services/       # API client (api.ts)
├── types/          # TypeScript definitions
├── utils/          # Helper functions and constants
├── App.tsx         # Main application
├── main.tsx        # Entry point
└── index.css       # Global styles
```

## Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
| `npm run lint` | Run ESLint |

## API Requirements

The frontend expects the backend to provide:

### GET /api/knowledge
```json
{
  "data": [
    {
      "id": "uuid",
      "category": "Design",
      "subcategory": "architecture",
      "title": "System Architecture Diagram",
      "raw_data": "...",
      "paraphrased_data": "...",
      "image": "https://...",
      "url": "https://...",
      "status": "completed",
      "created_at": "2025-01-06T10:00:00Z",
      "updated_at": "2025-01-06T10:00:00Z",
      "retry_count": 0
    }
  ],
  "metadata": {
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  }
}
```

## Troubleshooting

### Development Server Won't Start

1. Check if port 3000 is available
2. Delete `node_modules` and reinstall: `rm -rf node_modules && npm install`
3. Clear Vite cache: `rm -rf node_modules/.vite`

### API Calls Failing

1. Verify backend is running on `http://localhost:8000`
2. Check browser console for CORS errors
3. Verify API endpoint in `.env` file
4. Check network tab in browser DevTools

### Build Errors

1. Check TypeScript errors: `npm run lint`
2. Ensure all dependencies are installed
3. Update dependencies if needed: `npm update`

### Styling Issues

1. Clear browser cache
2. Check if CSS files are imported correctly
3. Verify CSS custom properties in `index.css`

## Development Tips

### Hot Module Replacement (HMR)
Vite provides instant HMR - changes appear immediately without full page reload.

### Component Development
Each component has its own CSS file for easy maintenance and debugging.

### Type Safety
Use TypeScript interfaces from `src/types/index.ts` for type safety.

### API Integration
All API calls go through `src/services/api.ts` for consistency.

### Custom Hooks
Use provided hooks (`useKnowledge`, `useModal`) for state management.

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## Next Steps

1. Start the backend API server
2. Run `npm run dev`
3. Navigate to `http://localhost:3000`
4. Browse categories and knowledge items
5. Click items to view details

## Need Help?

- Check `README.md` for detailed documentation
- Review `PROJECT_STRUCTURE.md` for architecture details
- Inspect browser console for error messages
- Check backend API logs for server-side issues

## Feature Roadmap

- Settings modal for configuration
- Image upload interface
- Advanced search and filtering
- Real-time updates
- RAG query interface
- Export functionality
