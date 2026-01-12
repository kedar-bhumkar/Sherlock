/**
 * Format date to a readable string
 */
export const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date);
};

/**
 * Truncate text to specified length with ellipsis
 */
export const truncateText = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength).trim() + '...';
};

/**
 * Capitalize first letter of a string
 */
export const capitalizeFirst = (text: string): string => {
  if (!text) return '';
  return text.charAt(0).toUpperCase() + text.slice(1);
};

/**
 * Build query parameters from object
 */
export const buildQueryParams = (params: Record<string, string | number | undefined>): string => {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.append(key, String(value));
    }
  });

  const query = searchParams.toString();
  return query ? `?${query}` : '';
};

/**
 * Check if a URL is valid
 */
export const isValidUrl = (url: string): boolean => {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
};

/**
 * Check if a URL is a Google Drive URL
 */
export const isGoogleDriveUrl = (url: string): boolean => {
  if (!url) return false;
  return url.includes('drive.google.com') || url.includes('docs.google.com');
};

/**
 * Extract Google Drive file ID from various URL patterns
 */
export const extractGoogleDriveFileId = (url: string): string | null => {
  if (!url) return null;

  const patterns = [
    /\/file\/d\/([a-zA-Z0-9_-]+)/,           // https://drive.google.com/file/d/{FILE_ID}/view
    /\/document\/d\/([a-zA-Z0-9_-]+)/,       // https://docs.google.com/document/d/{FILE_ID}/edit
    /\/spreadsheets\/d\/([a-zA-Z0-9_-]+)/,   // https://docs.google.com/spreadsheets/d/{FILE_ID}/edit
    /\/presentation\/d\/([a-zA-Z0-9_-]+)/,   // https://docs.google.com/presentation/d/{FILE_ID}/edit
    /[?&]id=([a-zA-Z0-9_-]+)/,               // https://drive.google.com/open?id={FILE_ID}
    /\/uc\?id=([a-zA-Z0-9_-]+)/,             // https://drive.google.com/uc?id={FILE_ID}
  ];

  for (const pattern of patterns) {
    const match = url.match(pattern);
    if (match && match[1]) {
      return match[1];
    }
  }

  return null;
};

/**
 * Convert Google Drive URL to proxy endpoint URL
 * Returns the original URL if it's not a Google Drive URL
 */
export const getProxiedImageUrl = (url: string, apiBaseUrl: string): string => {
  if (!url) return url;

  if (isGoogleDriveUrl(url)) {
    const fileId = extractGoogleDriveFileId(url);
    if (fileId) {
      return `${apiBaseUrl}/api/images/gdrive/${fileId}`;
    }
  }

  return url;
};
