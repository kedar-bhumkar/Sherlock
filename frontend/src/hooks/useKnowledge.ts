import { useState, useEffect, useCallback, useRef } from 'react';
import { getKnowledge, GetKnowledgeParams } from '../services/api';
import { KnowledgeItem, PaginationMetadata, ApiError } from '../types';
import { DEFAULT_PAGE_SIZE } from '../utils/constants';

interface UseKnowledgeState {
  data: KnowledgeItem[];
  metadata: PaginationMetadata | null;
  loading: boolean;
  error: ApiError | null;
}

interface UseKnowledgeReturn extends UseKnowledgeState {
  refetch: () => Promise<void>;
}

/**
 * Custom hook for fetching knowledge items with filters and pagination
 */
export const useKnowledge = (
  category?: string,
  subcategory?: string,
  topic?: string,
  page: number = 1,
  pageSize: number = DEFAULT_PAGE_SIZE
): UseKnowledgeReturn => {
  const [state, setState] = useState<UseKnowledgeState>({
    data: [],
    metadata: null,
    loading: true,
    error: null,
  });

  // Track request sequence to prevent race conditions
  const requestIdRef = useRef(0);

  const fetchData = useCallback(async () => {
    // Increment request ID to track this specific request
    const currentRequestId = ++requestIdRef.current;

    setState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      const params: GetKnowledgeParams = {
        page,
        page_size: pageSize,
      };

      // Only add category/subcategory/topic if they're not "All"
      if (category && category !== 'All') {
        params.category = category;
      }
      if (subcategory && subcategory !== 'All') {
        params.subcategory = subcategory;
      }
      if (topic && topic !== 'All') {
        params.topic = topic;
      }

      const response = await getKnowledge(params);

      // Only update state if this is still the latest request
      if (currentRequestId === requestIdRef.current) {
        setState({
          data: response.data,
          metadata: response.metadata,
          loading: false,
          error: null,
        });
      }
    } catch (error) {
      // Only update state if this is still the latest request
      if (currentRequestId === requestIdRef.current) {
        setState({
          data: [],
          metadata: null,
          loading: false,
          error: error as ApiError,
        });
      }
    }
  }, [category, subcategory, topic, page, pageSize]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    ...state,
    refetch: fetchData,
  };
};
