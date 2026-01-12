import React, { useEffect, useState } from 'react';
import { X, ExternalLink, Sparkles, BookOpen, ChevronDown, ChevronUp, Loader2 } from 'lucide-react';
import { KnowledgeItem, ParaphrasedDataStructure } from '../types';
import { formatDate, getProxiedImageUrl } from '../utils/helpers';
import { getKnowledgeById } from '../services/api';
import { API_BASE_URL } from '../utils/constants';
import './Modal.css';

interface ModalProps {
  isOpen: boolean;
  item: KnowledgeItem | null;
  onClose: () => void;
}

const Modal: React.FC<ModalProps> = ({ isOpen, item, onClose }) => {
  const [expandedConcepts, setExpandedConcepts] = useState<Set<number>>(new Set());
  const [parsedParaphrased, setParsedParaphrased] = useState<ParaphrasedDataStructure | null>(null);
  const [isStringFormat, setIsStringFormat] = useState(false);
  const [freshItem, setFreshItem] = useState<KnowledgeItem | null>(null);
  const [isLoadingFresh, setIsLoadingFresh] = useState(false);

  // Fetch fresh data from API when modal opens
  useEffect(() => {
    if (isOpen && item?.id) {
      let isCancelled = false;
      setIsLoadingFresh(true);

      getKnowledgeById(item.id)
        .then((data) => {
          if (!isCancelled) {
            setFreshItem(data);
            setIsLoadingFresh(false);
          }
        })
        .catch(() => {
          if (!isCancelled) {
            // Fallback to passed item if fetch fails
            setFreshItem(null);
            setIsLoadingFresh(false);
          }
        });

      return () => {
        isCancelled = true;
      };
    } else {
      setFreshItem(null);
      setIsLoadingFresh(false);
    }
  }, [isOpen, item?.id]);

  // Use fresh data if available, otherwise fallback to passed item
  const displayItem = freshItem || item;

  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  useEffect(() => {
    if (displayItem?.paraphrased_data) {
      try {
        const parsed = JSON.parse(displayItem.paraphrased_data) as ParaphrasedDataStructure;
        if (parsed.summary && Array.isArray(parsed.details)) {
          setParsedParaphrased(parsed);
          setIsStringFormat(false);
          // Initialize with all concept indices to expand all by default
          setExpandedConcepts(new Set(parsed.details.map((_, index) => index)));
        } else {
          setIsStringFormat(true);
          setParsedParaphrased(null);
        }
      } catch {
        setIsStringFormat(true);
        setParsedParaphrased(null);
      }
    } else {
      setParsedParaphrased(null);
      setIsStringFormat(false);
    }
  }, [displayItem]);

  if (!isOpen || !item) return null;

  const handleBackdropClick = (event: React.MouseEvent<HTMLDivElement>) => {
    if (event.target === event.currentTarget) {
      onClose();
    }
  };

  const toggleConcept = (index: number) => {
    const newExpanded = new Set(expandedConcepts);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedConcepts(newExpanded);
  };

  return (
    <div className="modal-backdrop" onClick={handleBackdropClick}>
      <div className="modal-container">
        <div className="modal-header">
          <div className="modal-header-content">
            <h2 className="modal-title">{displayItem.title}</h2>
            <div className="modal-metadata">
              <span className="modal-badge">{displayItem.category}</span>
              <span className="modal-badge secondary">{displayItem.subcategory}</span>
              <span className="modal-date">{formatDate(displayItem.created_at)}</span>
              {isLoadingFresh && (
                <Loader2 size={14} className="modal-loading-indicator" />
              )}
            </div>
          </div>

          <button
            className="modal-close-button"
            onClick={onClose}
            aria-label="Close modal"
          >
            <X size={24} />
          </button>
        </div>

        <div className="modal-body">
          {/* Image Section */}
          <div className="modal-image-section">
            {displayItem.image ? (
              <img
                src={getProxiedImageUrl(displayItem.image, API_BASE_URL)}
                alt={displayItem.title}
                className="modal-image"
              />
            ) : (
              <div className="modal-image-placeholder">No image available</div>
            )}
            {displayItem.url && (
              <a
                href={displayItem.url}
                target="_blank"
                rel="noopener noreferrer"
                className="modal-image-link"
              >
                <ExternalLink size={16} />
                View Source
              </a>
            )}
          </div>

          {/* Data Section */}
          <div className="modal-data-section">
            <div className="modal-data-column">
              <h3 className="modal-data-title">Raw Data</h3>
              <div className="modal-data-content">
                {displayItem.raw_data || 'No raw data available'}
              </div>
            </div>

            <div className="modal-data-column">
              <h3 className="modal-data-title">Paraphrased Data</h3>
              {isStringFormat || !parsedParaphrased ? (
                <div className="modal-data-content">
                  {displayItem.paraphrased_data || 'No paraphrased data available'}
                </div>
              ) : (
                <div className="paraphrased-structured">
                  <div className="paraphrased-summary">
                    <div className="summary-header">
                      <Sparkles size={20} className="summary-icon" />
                      <h4>Summary</h4>
                    </div>
                    <p className="summary-text">{parsedParaphrased.summary}</p>
                  </div>

                  {parsedParaphrased.details && parsedParaphrased.details.length > 0 && (
                    <div className="paraphrased-concepts">
                      <div className="concepts-header">
                        <BookOpen size={18} />
                        <h4>Key Concepts</h4>
                      </div>
                      <div className="concepts-list">
                        {parsedParaphrased.details.map((detail, index) => (
                          <div key={index} className="concept-item">
                            <button
                              className="concept-header"
                              onClick={() => toggleConcept(index)}
                              aria-expanded={expandedConcepts.has(index)}
                            >
                              <div className="concept-title">
                                <span className="concept-bullet"></span>
                                <span className="concept-name">{detail.concept}</span>
                              </div>
                              {expandedConcepts.has(index) ? (
                                <ChevronUp size={18} className="concept-toggle" />
                              ) : (
                                <ChevronDown size={18} className="concept-toggle" />
                              )}
                            </button>
                            {expandedConcepts.has(index) && (
                              <div className="concept-details">
                                <p>{detail.expanded_information || detail.expanded || detail.expanded_info || 'No expanded information available'}</p>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Status and Error Section */}
          {(displayItem.status === 'failed' || displayItem.status === 'processing') && (
            <div className="modal-status-section">
              <div className={`modal-status-badge ${displayItem.status}`}>
                Status: {displayItem.status}
              </div>
              {displayItem.last_error && (
                <div className="modal-error">
                  <strong>Error:</strong> {displayItem.last_error}
                </div>
              )}
              {displayItem.retry_count > 0 && (
                <div className="modal-retry">
                  Retry attempts: {displayItem.retry_count}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Modal;
