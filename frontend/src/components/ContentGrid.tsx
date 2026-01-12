import React from 'react';
import { Image as ImageIcon, AlertCircle, Loader2 } from 'lucide-react';
import { KnowledgeItem, PaginationMetadata } from '../types';
import { truncateText, getProxiedImageUrl } from '../utils/helpers';
import { API_BASE_URL } from '../utils/constants';
import Pagination from './Pagination';
import './ContentGrid.css';

interface ContentGridProps {
  items: KnowledgeItem[];
  loading: boolean;
  error: string | null;
  metadata: PaginationMetadata | null;
  onItemClick: (item: KnowledgeItem) => void;
  onPageChange: (page: number) => void;
}

const ContentGrid: React.FC<ContentGridProps> = ({
  items,
  loading,
  error,
  metadata,
  onItemClick,
  onPageChange,
}) => {
  if (loading) {
    return (
      <div className="content-state">
        <Loader2 className="content-state-icon rotating" size={48} />
        <p className="content-state-text">Loading knowledge items...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="content-state">
        <AlertCircle className="content-state-icon error" size={48} />
        <p className="content-state-text error">Error loading items</p>
        <p className="content-state-message">{error}</p>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="content-state">
        <ImageIcon className="content-state-icon" size={48} />
        <p className="content-state-text">No knowledge items found</p>
        <p className="content-state-message">
          Try selecting a different category or add new images to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="content-grid-container">
      <div className="content-grid">
        {items.map((item) => (
          <div
            key={item.id}
            className="content-card"
            onClick={() => onItemClick(item)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onItemClick(item);
              }
            }}
          >
            <div className="content-card-image-container">
              {item.image ? (
                <img
                  src={getProxiedImageUrl(item.image, API_BASE_URL)}
                  alt={item.title}
                  className="content-card-image"
                  loading="lazy"
                />
              ) : (
                <div className="content-card-placeholder">
                  <ImageIcon size={32} />
                </div>
              )}
              <div className="content-card-overlay">
                <span className="content-card-badge">{item.category}</span>
              </div>
            </div>

            <div className="content-card-body">
              <h3 className="content-card-title" title={item.title}>
                {truncateText(item.title, 60)}
              </h3>
              <p className="content-card-subtitle">
                {item.subcategory}
              </p>
            </div>
          </div>
        ))}
      </div>

      {metadata && metadata.total_pages > 1 && (
        <Pagination
          currentPage={metadata.page}
          totalPages={metadata.total_pages}
          onPageChange={onPageChange}
        />
      )}
    </div>
  );
};

export default ContentGrid;
