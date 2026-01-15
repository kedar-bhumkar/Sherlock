import { useState, useCallback, useEffect } from 'react';
import { ApiError } from '../types';
import {
  getTOTPStatus,
  verifyTOTP,
  validateSession,
  logout as apiLogout,
  setAuthToken,
  getAuthToken,
  clearAuthToken,
} from '../services/api';

interface UseAuthState {
  authenticated: boolean;
  loading: boolean;
  totpEnabled: boolean;
  error: ApiError | null;
}

interface UseAuthReturn extends UseAuthState {
  login: (code: string) => Promise<boolean>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
}

export const useAuth = (): UseAuthReturn => {
  const [state, setState] = useState<UseAuthState>({
    authenticated: false,
    loading: true,
    totpEnabled: true,
    error: null,
  });

  const checkAuth = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      // First check if TOTP is enabled
      const status = await getTOTPStatus();

      if (!status.enabled || !status.configured) {
        // TOTP is disabled, allow access
        setState({
          authenticated: true,
          loading: false,
          totpEnabled: false,
          error: null,
        });
        return;
      }

      // TOTP is enabled, check if we have a valid session
      const token = getAuthToken();
      if (!token) {
        setState({
          authenticated: false,
          loading: false,
          totpEnabled: true,
          error: null,
        });
        return;
      }

      // Validate the session
      const session = await validateSession();
      setState({
        authenticated: session.valid,
        loading: false,
        totpEnabled: true,
        error: null,
      });

      if (!session.valid) {
        clearAuthToken();
      }
    } catch (err) {
      setState({
        authenticated: false,
        loading: false,
        totpEnabled: true,
        error: err as ApiError,
      });
    }
  }, []);

  const login = useCallback(async (code: string): Promise<boolean> => {
    setState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      const response = await verifyTOTP(code);

      if (response.success && response.token) {
        setAuthToken(response.token);
        setState((prev) => ({
          ...prev,
          authenticated: true,
          loading: false,
          error: null,
        }));
        return true;
      }

      // TOTP disabled case
      if (response.success && !response.token) {
        setState((prev) => ({
          ...prev,
          authenticated: true,
          loading: false,
          totpEnabled: false,
          error: null,
        }));
        return true;
      }

      setState((prev) => ({
        ...prev,
        authenticated: false,
        loading: false,
        error: { message: response.message },
      }));
      return false;
    } catch (err) {
      setState((prev) => ({
        ...prev,
        authenticated: false,
        loading: false,
        error: err as ApiError,
      }));
      return false;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } finally {
      setState((prev) => ({
        ...prev,
        authenticated: false,
        error: null,
      }));
    }
  }, []);

  // Check auth status on mount
  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return {
    ...state,
    login,
    logout,
    checkAuth,
  };
};
