import { useState, useCallback, useRef, useEffect } from 'react';

interface UseModalReturn<T> {
  isOpen: boolean;
  data: T | null;
  openModal: (data: T) => void;
  closeModal: () => void;
}

/**
 * Custom hook for managing modal state
 */
export const useModal = <T = any>(): UseModalReturn<T> => {
  const [isOpen, setIsOpen] = useState(false);
  const [data, setData] = useState<T | null>(null);
  const clearTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (clearTimeoutRef.current) {
        clearTimeout(clearTimeoutRef.current);
      }
    };
  }, []);

  const openModal = useCallback((modalData: T) => {
    // Clear any pending timeout from previous close
    if (clearTimeoutRef.current) {
      clearTimeout(clearTimeoutRef.current);
      clearTimeoutRef.current = null;
    }
    setData(modalData);
    setIsOpen(true);
  }, []);

  const closeModal = useCallback(() => {
    setIsOpen(false);
    // Clear data immediately to prevent stale data flash on next open
    setData(null);
  }, []);

  return {
    isOpen,
    data,
    openModal,
    closeModal,
  };
};
