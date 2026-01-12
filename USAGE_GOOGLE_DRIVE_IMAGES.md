# Google Drive Image Proxy - Usage Guide

## Quick Start

### Prerequisites
- credentials.json in backend/ folder (already exists)
- token.pickle in backend/ folder (already exists)
- Backend running on http://localhost:8000
- Frontend running on http://localhost:5173 (or configured port)

### Starting the Application

1. **Start Backend:**
```bash
cd backend
uvicorn main:app --reload
```

2. **Start Frontend:**
```bash
cd frontend
npm run dev
```

3. **Access Application:**
```
http://localhost:5173
```

## How It Works

### Automatic URL Detection
The frontend automatically detects Google Drive URLs and routes them through the proxy:

**Supported Google Drive URL Patterns:**
- `https://drive.google.com/file/d/{FILE_ID}/view`
- `https://drive.google.com/open?id={FILE_ID}`
- `https://drive.google.com/uc?id={FILE_ID}`
- `https://docs.google.com/document/d/{FILE_ID}/edit`
- `https://docs.google.com/spreadsheets/d/{FILE_ID}/edit`
- `https://docs.google.com/presentation/d/{FILE_ID}/edit`

### Image Flow Example

**Original URL in Database:**
```
https://drive.google.com/file/d/1abc123XYZ-456/view
```

**Displayed in Frontend As:**
```
http://localhost:8000/api/images/gdrive/1abc123XYZ-456
```

## API Endpoint Reference

### GET /api/images/gdrive/{file_id}

Serves images from Google Drive through authenticated proxy.

**Parameters:**
- `file_id` (path): Google Drive file ID

**Response:**
- Content-Type: Original image MIME type (image/jpeg, image/png, etc.)
- Cache-Control: public, max-age=3600
- Content-Disposition: inline; filename="original_name.jpg"

**Status Codes:**
- 200: Image successfully retrieved
- 404: File not found or inaccessible
- 500: Download error
- 503: Authentication required

**Example Request:**
```bash
curl http://localhost:8000/api/images/gdrive/1abc123XYZ-456
```

## Testing

### 1. Test Backend Service
```bash
cd backend
python test_google_drive_proxy.py
```

**Expected Output:**
```
=== Testing URL Helper Functions ===
[PASS] All URL patterns extracted correctly

=== Testing Google Drive Service ===
1. Configuration Check - OK
2. Authentication Status - OK
3. URL File ID Extraction - OK
```

### 2. Test API Endpoint
```bash
# Replace FILE_ID with actual Google Drive file ID
curl -I http://localhost:8000/api/images/gdrive/FILE_ID
```

**Expected Response:**
```
HTTP/1.1 200 OK
content-type: image/jpeg
cache-control: public, max-age=3600
content-disposition: inline; filename="image.jpg"
```

### 3. Test Frontend Display

1. Open browser DevTools (F12)
2. Go to Network tab
3. Navigate to Sherlock application
4. Click on a knowledge item with Google Drive image
5. Verify image requests go to `/api/images/gdrive/...`
6. Check response status is 200

## Troubleshooting

### Images Not Loading

**Check 1: Backend Running**
```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy","service":"sherlock-api"}
```

**Check 2: Authentication Valid**
```bash
cd backend
python -c "from services.google_drive_service import get_drive_service; print('Auth OK' if get_drive_service().is_authenticated() else 'Auth Failed')"
```

**Check 3: File Accessible**
- Ensure the Google account has access to the file
- Check file sharing permissions in Google Drive
- Verify file ID is correct

### 503 Authentication Required

**Solution:**
```bash
cd backend
python -c "from services.google_drive_service import get_drive_service; get_drive_service().authenticate()"
```

This will:
1. Check existing token.pickle
2. Refresh if expired
3. Open browser for OAuth if needed
4. Save new token to token.pickle

### CORS Errors

**Ensure backend CORS is configured:**
```python
# In backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specific frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Images Load Slowly

**Enable caching in browser:**
- Images are cached for 1 hour by default
- Check browser cache in DevTools > Network > Disable cache is OFF

**Verify cache headers:**
```bash
curl -I http://localhost:8000/api/images/gdrive/FILE_ID | grep -i cache
# Should show: cache-control: public, max-age=3600
```

## Configuration

### Backend Environment Variables

**File:** `backend/.env`

```bash
# Google Drive credentials (relative to backend/)
GOOGLE_DRIVE_CREDENTIALS_PATH=credentials.json
GOOGLE_DRIVE_TOKEN_PATH=token.pickle
```

### Frontend Environment Variables

**File:** `frontend/.env`

```bash
# Backend API URL
VITE_API_BASE_URL=http://localhost:8000
```

**For Production:**
```bash
VITE_API_BASE_URL=https://your-api-domain.com
```

## Development Tips

### Mock Google Drive for Testing

**File:** `backend/.env`
```bash
USE_MOCK=true
```

This uses mock implementations for testing without actual Google Drive access.

### Clear Authentication

```bash
cd backend
rm token.pickle
# Then re-authenticate
python -c "from services.google_drive_service import get_drive_service; get_drive_service().authenticate()"
```

### Debug Image Loading

**Add console logging in frontend:**
```typescript
// In ContentGrid.tsx or Modal.tsx
console.log('Original URL:', item.image);
console.log('Proxied URL:', getProxiedImageUrl(item.image, API_BASE_URL));
```

## Performance Optimization

### Current Caching Strategy
- Browser cache: 1 hour (3600 seconds)
- No backend cache (downloads on each miss)

### Future Improvements

1. **Backend Caching:**
```python
# Add Redis cache in images.py
from redis import Redis
cache = Redis(host='localhost', port=6379)

# Cache downloaded images
cached = cache.get(f"gdrive:{file_id}")
if cached:
    return Response(content=cached, ...)
```

2. **CDN Upload:**
- Upload to S3/CloudFlare after first download
- Update database URL to CDN
- Reduces Google Drive API calls

3. **Thumbnail Generation:**
```python
from PIL import Image
# Resize large images for thumbnails
# Store both thumbnail and full-size
```

## API Usage in Code

### Frontend Components

**ContentGrid.tsx:**
```typescript
import { getProxiedImageUrl } from '../utils/helpers';
import { API_BASE_URL } from '../utils/constants';

<img
  src={getProxiedImageUrl(item.image, API_BASE_URL)}
  alt={item.title}
/>
```

**Modal.tsx:**
```typescript
import { getProxiedImageUrl } from '../utils/helpers';
import { API_BASE_URL } from '../utils/constants';

<img
  src={getProxiedImageUrl(item.image, API_BASE_URL)}
  alt={item.title}
/>
```

### Backend Services

**Using Google Drive Service:**
```python
from services.google_drive_service import get_drive_service

# Get service
drive = get_drive_service()

# Check authentication
if drive.is_authenticated():
    # Download file
    file_bytes = await drive.download_file(file_id)

    # Get metadata
    metadata = await drive.get_file_metadata(file_id)
```

## Security Considerations

1. **Credentials Storage:**
   - credentials.json and token.pickle in .gitignore
   - Never commit to version control
   - Store securely in production (secrets manager)

2. **File Access:**
   - Only files accessible by authenticated Google account
   - No public access to files without sharing

3. **Rate Limiting:**
   - Google Drive API has rate limits
   - Consider implementing request throttling for production

4. **Error Handling:**
   - Never expose credentials in error messages
   - Generic error messages to users
   - Detailed logging server-side only

## Production Deployment

### Backend (Fly.io)

1. **Add secrets:**
```bash
fly secrets set GOOGLE_DRIVE_CREDENTIALS_PATH=/app/credentials.json
fly secrets set GOOGLE_DRIVE_TOKEN_PATH=/app/token.pickle
```

2. **Upload credentials:**
```bash
# Store credentials.json and token.pickle in Fly.io volumes
# Or use secret storage service
```

3. **Environment:**
```bash
# In fly.toml
[env]
  GOOGLE_DRIVE_CREDENTIALS_PATH = "/app/credentials.json"
  GOOGLE_DRIVE_TOKEN_PATH = "/app/token.pickle"
```

### Frontend

**Update production API URL:**
```bash
# In frontend/.env.production
VITE_API_BASE_URL=https://your-api.fly.dev
```

**Build:**
```bash
cd frontend
npm run build
```

## Support

### Common Issues

1. **Token expired:** Run authentication again
2. **File not found:** Check file ID and permissions
3. **Slow loading:** Verify internet connection and API rate limits
4. **CORS errors:** Check backend CORS configuration

### Debug Commands

```bash
# Check token validity
cd backend
python -c "from services.google_drive_service import get_drive_service; s = get_drive_service(); print(f'Valid: {s.is_authenticated()}')"

# Test file download
python -c "import asyncio; from services.google_drive_service import get_drive_service; asyncio.run(get_drive_service().download_file('FILE_ID'))"

# Check API health
curl http://localhost:8000/health
```

## Summary

The Google Drive image proxy implementation provides:

1. Seamless integration with existing credentials
2. Automatic URL detection and conversion
3. Authenticated access to private Google Drive files
4. Browser caching for performance
5. Comprehensive error handling
6. Easy testing and debugging

All Google Drive images will now load properly through the authenticated proxy endpoint without any manual URL conversion needed.
