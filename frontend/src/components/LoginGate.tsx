import React, { useState, useRef, useEffect } from 'react';
import { Search, Lock, Loader2, AlertCircle } from 'lucide-react';
import { useAuth } from '../hooks';
import './LoginGate.css';

interface LoginGateProps {
  children: React.ReactNode;
}

const LoginGate: React.FC<LoginGateProps> = ({ children }) => {
  const { authenticated, loading, totpEnabled, error, login } = useAuth();
  const [code, setCode] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input on mount
  useEffect(() => {
    if (!loading && !authenticated && inputRef.current) {
      inputRef.current.focus();
    }
  }, [loading, authenticated]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (code.length !== 6 || submitting) return;

    setSubmitting(true);
    setLoginError(null);

    const success = await login(code);
    if (!success) {
      setLoginError('Invalid code. Please try again.');
      setCode('');
      inputRef.current?.focus();
    }

    setSubmitting(false);
  };

  const handleCodeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/\D/g, '').slice(0, 6);
    setCode(value);
    setLoginError(null);
  };

  // Show loading state
  if (loading) {
    return (
      <div className="login-gate">
        <div className="login-container">
          <Loader2 className="login-spinner" size={32} />
          <p className="login-loading-text">Checking authentication...</p>
        </div>
      </div>
    );
  }

  // If authenticated or TOTP is disabled, show the app
  if (authenticated || !totpEnabled) {
    return <>{children}</>;
  }

  // Show login form
  return (
    <div className="login-gate">
      <div className="login-container">
        <div className="login-header">
          <Search className="login-icon" size={40} strokeWidth={2} />
          <h1 className="login-title">Sherlock</h1>
          <p className="login-subtitle">Image Knowledge Extraction</p>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          <div className="login-input-group">
            <Lock className="login-input-icon" size={20} />
            <input
              ref={inputRef}
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              autoComplete="one-time-code"
              placeholder="000000"
              value={code}
              onChange={handleCodeChange}
              className="login-input"
              disabled={submitting}
              maxLength={6}
            />
          </div>

          <p className="login-hint">
            Enter the 6-digit code from your authenticator app
          </p>

          {(loginError || error) && (
            <div className="login-error">
              <AlertCircle size={16} />
              <span>{loginError || error?.message}</span>
            </div>
          )}

          <button
            type="submit"
            className="login-button"
            disabled={code.length !== 6 || submitting}
          >
            {submitting ? (
              <>
                <Loader2 className="login-button-spinner" size={18} />
                Verifying...
              </>
            ) : (
              'Verify'
            )}
          </button>
        </form>
      </div>
    </div>
  );
};

export default LoginGate;
