import { API_BASE_URL } from '../utils/constants';
import { buildQueryParams } from '../utils/helpers';
import { KnowledgeResponse, ApiError, Category, TagsConfig } from '../types';

/**
 * Base fetch wrapper with error handling
 */
const fetchWithErrorHandling = async <T>(
  url: string,
  options?: RequestInit
): Promise<T> => {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({
        message: response.statusText,
      }));
      const error: ApiError = {
        message: errorData.message || 'An error occurred',
        status: response.status,
      };
      throw error;
    }

    return await response.json();
  } catch (error) {
    if ((error as ApiError).status) {
      throw error;
    }
    throw {
      message: 'Network error. Please check your connection.',
      status: 0,
    } as ApiError;
  }
};

export interface GetKnowledgeParams {
  category?: string;
  subcategory?: string;
  topic?: string;
  page?: number;
  page_size?: number;
}

/**
 * Fetch knowledge items with optional filters and pagination
 */
export const getKnowledge = async (
  params: GetKnowledgeParams = {}
): Promise<KnowledgeResponse> => {
  const queryString = buildQueryParams({
    category: params.category,
    subcategory: params.subcategory,
    topic: params.topic,
    page: params.page,
    page_size: params.page_size,
  });

  return fetchWithErrorHandling<KnowledgeResponse>(
    `${API_BASE_URL}/api/knowledge${queryString}`
  );
};

/**
 * Fetch a single knowledge item by ID
 */
export const getKnowledgeById = async (id: string): Promise<any> => {
  return fetchWithErrorHandling(`${API_BASE_URL}/api/knowledge/${id}`);
};

/**
 * Retry a failed knowledge item
 */
export const retryKnowledgeItem = async (id: string): Promise<any> => {
  return fetchWithErrorHandling(`${API_BASE_URL}/api/knowledge/${id}/retry`, {
    method: 'POST',
  });
};

/**
 * Retry all failed knowledge items
 */
export const retryAllFailed = async (
  category?: string,
  limit: number = 100
): Promise<any> => {
  const queryString = buildQueryParams({ category, limit });

  return fetchWithErrorHandling(
    `${API_BASE_URL}/api/knowledge/retry-failed${queryString}`,
    {
      method: 'POST',
    }
  );
};

export interface IngestParams {
  folder_type?: 'local' | 'google_drive';
  folder_location?: string;
  image_url?: string;
  llm_type?: 'local' | 'web';
  llm?: string;
}

/**
 * Ingest new images
 */
export const ingestImages = async (params: IngestParams): Promise<any> => {
  return fetchWithErrorHandling(`${API_BASE_URL}/api/ingest`, {
    method: 'POST',
    body: JSON.stringify(params),
  });
};

/**
 * Fetch tags configuration (categories and subcategories)
 */
export const getTags = async (): Promise<TagsConfig> => {
  return fetchWithErrorHandling<TagsConfig>(`${API_BASE_URL}/api/config/tags`);
};
