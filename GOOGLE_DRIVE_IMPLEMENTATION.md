# Google Drive Image Authentication Implementation

## Overview
This implementation adds Google Drive authentication to serve images properly to the frontend using existing credentials.json and token.pickle files.

## Backend Implementation

### 1. Google Drive Service (`backend/services/google_drive_service.py`)
**Status:** Already existed - utilized existing authentication system

**Key Features:**
- Authenticates using credentials.json and token.pickle
- Auto-refreshes expired tokens
- Downloads images from Google Drive
- Supports multiple Google Drive URL patterns

**Key Methods:**
- `authenticate(headless=True)` - Authenticates with Google Drive
- `download_file(file_id)` - Downloads file content as bytes
- `get_file_metadata(file_id)` - Gets file metadata including MIME type
- `extract_file_id_from_url(url)` - Extracts file ID from various URL patterns

### 2. Image Proxy API Endpoint (`backend/api/routes/images.py`)
**Created:** New file

**Endpoint:** `GET /api/images/gdrive/{file_id}`

**Features:**
- Proxies Google Drive images through the backend
- Handles authentication automatically
- Returns images with proper content-type headers
- Caches images for 1 hour (configurable)
- Comprehensive error handling

**Response Headers:**
- `Content-Type`: Matches original file MIME type
- `Cache-Control`: public, max-age=3600
- `Content-Disposition`: inline with original filename

**Error Handling:**
- 404: File not found or inaccessible
- 500: Download failures or unexpected errors
- 503: Authentication required (token missing)

### 3. Main Application Updates (`backend/main.py`)
**Modified:** Added images router to FastAPI app

```python
from api.routes import images
app.include_router(images.router, prefix="/api", tags=["Images"])
```

## Frontend Implementation

### 1. Google Drive URL Utilities (`frontend/src/utils/helpers.ts`)
**Modified:** Added three new utility functions

**Functions:**

#### `isGoogleDriveUrl(url: string): boolean`
Checks if a URL is from Google Drive or Google Docs

#### `extractGoogleDriveFileId(url: string): string | null`
Extracts file ID from various Google Drive URL patterns:
- `https://drive.google.com/file/d/{FILE_ID}/view`
- `https://drive.google.com/open?id={FILE_ID}`
- `https://drive.google.com/uc?id={FILE_ID}`
- `https://docs.google.com/document/d/{FILE_ID}/edit`
- `https://docs.google.com/spreadsheets/d/{FILE_ID}/edit`
- `https://docs.google.com/presentation/d/{FILE_ID}/edit`

#### `getProxiedImageUrl(url: string, apiBaseUrl: string): string`
Converts Google Drive URLs to proxy endpoint URLs
- Returns proxy URL for Google Drive images
- Returns original URL for non-Google Drive images

### 2. ContentGrid Component (`frontend/src/components/ContentGrid.tsx`)
**Modified:** Updated to use proxy endpoint for image display

**Changes:**
- Imported `getProxiedImageUrl` and `API_BASE_URL`
- Updated image src to use `getProxiedImageUrl(item.image, API_BASE_URL)`

### 3. Modal Component (`frontend/src/components/Modal.tsx`)
**Modified:** Updated to use proxy endpoint for full-size image display

**Changes:**
- Imported `getProxiedImageUrl` and `API_BASE_URL`
- Updated modal image src to use `getProxiedImageUrl(item.image, API_BASE_URL)`

## File Structure

```
backend/
├── api/
│   └── routes/
│       └── images.py              # NEW - Image proxy endpoint
├── services/
│   └── google_drive_service.py    # EXISTING - Used for authentication
├── settings/
│   └── config.py                  # EXISTING - Contains credentials paths
├── credentials.json               # EXISTING - Google OAuth credentials
├── token.pickle                   # EXISTING - Stored authentication token
└── main.py                        # MODIFIED - Added images router

frontend/
├── src/
│   ├── components/
│   │   ├── ContentGrid.tsx        # MODIFIED - Uses proxy for thumbnails
│   │   └── Modal.tsx              # MODIFIED - Uses proxy for full images
│   └── utils/
│       └── helpers.ts             # MODIFIED - Added GDrive URL utilities
```

## Configuration

### Environment Variables (backend/.env)
```bash
# Google Drive credentials paths (relative to backend/)
google_drive_credentials_path=credentials.json
google_drive_token_path=token.pickle
```

### Environment Variables (frontend/.env)
```bash
# API base URL for proxy endpoint
VITE_API_BASE_URL=http://localhost:8000
```

## How It Works

### Authentication Flow
1. Backend starts and loads credentials.json
2. If token.pickle exists and is valid, uses it
3. If token is expired but has refresh_token, auto-refreshes
4. Token is saved back to token.pickle after refresh

### Image Serving Flow
1. Frontend receives image URL from knowledge API
2. `getProxiedImageUrl()` detects if it's a Google Drive URL
3. If yes, extracts file ID and converts to proxy URL
4. Frontend requests image from `/api/images/gdrive/{file_id}`
5. Backend authenticates with Google Drive
6. Backend downloads image bytes
7. Backend returns image with proper headers and caching

### Example URLs

**Original Google Drive URL:**
```
https://drive.google.com/file/d/1abc123XYZ-456/view
```

**Proxied URL:**
```
http://localhost:8000/api/images/gdrive/1abc123XYZ-456
```

## Benefits

1. **Seamless Integration:** Uses existing credentials without modification
2. **Automatic Authentication:** Token refresh handled automatically
3. **Performance:** 1-hour browser caching reduces repeated downloads
4. **Security:** Google Drive credentials never exposed to frontend
5. **Backward Compatible:** Non-Google Drive URLs work unchanged
6. **Error Handling:** Comprehensive error messages for debugging

## Testing

### Test Backend Endpoint
```bash
curl http://localhost:8000/api/images/gdrive/YOUR_FILE_ID
```

### Test Frontend Display
1. Start backend: `cd backend && uvicorn main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Open browser and view knowledge items with Google Drive images
4. Images should load through proxy endpoint

## Troubleshooting

### 503 Authentication Required
- Ensure credentials.json exists in backend/
- Ensure token.pickle exists and is valid
- Run authentication interactively first if needed

### 404 File Not Found
- Verify file ID is correct
- Ensure Google account has access to the file
- Check file sharing permissions

### Images Not Loading
- Check browser console for errors
- Verify API_BASE_URL in frontend/.env
- Ensure backend is running on correct port
- Check CORS configuration in backend

## Future Enhancements

1. **Advanced Caching:** Add Redis/Memcached for backend caching
2. **Thumbnail Support:** Use Google Drive thumbnail links for faster loading
3. **Batch Download:** Download multiple images in parallel
4. **CDN Integration:** Upload to CDN for faster global delivery
5. **Image Optimization:** Resize/compress images before serving
