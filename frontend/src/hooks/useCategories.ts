import { useState, useEffect, useCallback } from 'react';
import { getTags } from '../services/api';
import { Category, ApiError } from '../types';

interface UseCategoriesState {
  categories: Category[];
  loading: boolean;
  error: ApiError | null;
}

interface UseCategoriesReturn extends UseCategoriesState {
  refetch: () => Promise<void>;
}

/**
 * Custom hook for fetching categories dynamically from the API
 */
export const useCategories = (): UseCategoriesReturn => {
  const [state, setState] = useState<UseCategoriesState>({
    categories: [],
    loading: true,
    error: null,
  });

  const fetchCategories = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      const response = await getTags();

      setState({
        categories: response.categories,
        loading: false,
        error: null,
      });
    } catch (error) {
      setState({
        categories: [],
        loading: false,
        error: error as ApiError,
      });
    }
  }, []);

  useEffect(() => {
    fetchCategories();
  }, [fetchCategories]);

  return {
    ...state,
    refetch: fetchCategories,
  };
};
