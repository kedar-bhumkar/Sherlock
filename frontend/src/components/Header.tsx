import React from 'react';
import { Search, Settings } from 'lucide-react';
import './Header.css';

interface HeaderProps {
  onSettingsClick?: () => void;
}

const Header: React.FC<HeaderProps> = ({ onSettingsClick }) => {
  return (
    <header className="header">
      <div className="header-brand">
        <Search className="header-icon" size={28} strokeWidth={2.5} />
        <h1 className="header-title">Sherlock</h1>
        <span className="header-subtitle">Image Knowledge Extraction</span>
      </div>

      <div className="header-actions">
        <button
          className="header-button"
          onClick={onSettingsClick}
          aria-label="Settings"
          title="Settings"
        >
          <Settings size={20} />
        </button>
      </div>
    </header>
  );
};

export default Header;
