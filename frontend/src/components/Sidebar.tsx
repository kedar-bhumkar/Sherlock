import React, { useState, useEffect } from 'react';
import { ChevronDown, ChevronRight, Folder, FolderOpen, Loader2, AlertCircle } from 'lucide-react';
import { ALL_CATEGORIES, ALL_SUBCATEGORIES, ALL_TOPICS } from '../utils/constants';
import { useCategories } from '../hooks';
import { capitalizeFirst } from '../utils/helpers';
import './Sidebar.css';

interface SidebarProps {
  selectedCategory: string;
  selectedSubcategory: string;
  selectedTopic: string;
  onCategorySelect: (category: string, subcategory: string, topic: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({
  selectedCategory,
  selectedSubcategory,
  selectedTopic,
  onCategorySelect,
}) => {
  const { categories, loading, error, refetch } = useCategories();
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set([ALL_CATEGORIES])
  );
  const [expandedSubcategories, setExpandedSubcategories] = useState<Set<string>>(
    new Set()
  );

  // Expand all categories when they are loaded
  useEffect(() => {
    if (categories.length > 0) {
      setExpandedCategories(new Set([ALL_CATEGORIES, ...categories.map((c) => c.name)]));
    }
  }, [categories]);

  const toggleCategory = (categoryName: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(categoryName)) {
      newExpanded.delete(categoryName);
    } else {
      newExpanded.add(categoryName);
    }
    setExpandedCategories(newExpanded);
  };

  const toggleSubcategory = (categoryName: string, subcategoryName: string) => {
    const key = `${categoryName}:${subcategoryName}`;
    const newExpanded = new Set(expandedSubcategories);
    if (newExpanded.has(key)) {
      newExpanded.delete(key);
    } else {
      newExpanded.add(key);
    }
    setExpandedSubcategories(newExpanded);
  };

  const isSelected = (category: string, subcategory: string, topic: string) => {
    return selectedCategory === category && selectedSubcategory === subcategory && selectedTopic === topic;
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h2 className="sidebar-title">Categories</h2>
      </div>

      <nav className="sidebar-nav">
        {/* Loading State */}
        {loading && (
          <div className="sidebar-loading">
            <Loader2 size={20} className="animate-spin" />
            <span>Loading categories...</span>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="sidebar-error">
            <AlertCircle size={18} />
            <span>Failed to load categories</span>
            <button className="sidebar-retry-button" onClick={refetch}>
              Retry
            </button>
          </div>
        )}

        {/* All Categories Option */}
        {!loading && !error && (
          <div className="sidebar-category">
            <button
              className={`sidebar-category-button ${
                isSelected(ALL_CATEGORIES, ALL_SUBCATEGORIES, ALL_TOPICS) ? 'active' : ''
              }`}
              onClick={() => onCategorySelect(ALL_CATEGORIES, ALL_SUBCATEGORIES, ALL_TOPICS)}
            >
              <div className="sidebar-category-label">
                <Folder size={18} />
                <span>All Categories</span>
              </div>
            </button>
          </div>
        )}

        {/* Individual Categories */}
        {!loading && !error && categories.map((category) => {
          const isExpanded = expandedCategories.has(category.name);
          const isCategorySelected = selectedCategory === category.name;

          return (
            <div key={category.name} className="sidebar-category">
              <div className="sidebar-category-header">
                <button
                  className="sidebar-expand-button"
                  onClick={() => toggleCategory(category.name)}
                  aria-label={`${isExpanded ? 'Collapse' : 'Expand'} ${category.name}`}
                >
                  {isExpanded ? (
                    <ChevronDown size={16} />
                  ) : (
                    <ChevronRight size={16} />
                  )}
                </button>

                <button
                  className={`sidebar-category-button ${
                    isCategorySelected && selectedSubcategory === ALL_SUBCATEGORIES && selectedTopic === ALL_TOPICS
                      ? 'active'
                      : ''
                  }`}
                  onClick={() => onCategorySelect(category.name, ALL_SUBCATEGORIES, ALL_TOPICS)}
                >
                  <div className="sidebar-category-label">
                    {isExpanded ? (
                      <FolderOpen size={18} />
                    ) : (
                      <Folder size={18} />
                    )}
                    <span>{category.name}</span>
                  </div>
                </button>
              </div>

              {/* Subcategories */}
              {isExpanded && (
                <div className="sidebar-subcategories">
                  {category.subcategories.map((subcategory) => {
                    const subcatKey = `${category.name}:${subcategory.name}`;
                    const isSubcatExpanded = expandedSubcategories.has(subcatKey);
                    const hasTopics = subcategory.topics && subcategory.topics.length > 0;

                    return (
                      <div key={subcategory.name}>
                        <div className="sidebar-subcategory-header">
                          {hasTopics && (
                            <button
                              className="sidebar-subcategory-expand"
                              onClick={() => toggleSubcategory(category.name, subcategory.name)}
                              aria-label={`${isSubcatExpanded ? 'Collapse' : 'Expand'} ${subcategory.name}`}
                            >
                              {isSubcatExpanded ? (
                                <ChevronDown size={14} />
                              ) : (
                                <ChevronRight size={14} />
                              )}
                            </button>
                          )}
                          <button
                            className={`sidebar-subcategory-button ${
                              isSelected(category.name, subcategory.name, ALL_TOPICS) ? 'active' : ''
                            }`}
                            onClick={() => onCategorySelect(category.name, subcategory.name, ALL_TOPICS)}
                            style={!hasTopics ? { marginLeft: '1.25rem' } : undefined}
                          >
                            {capitalizeFirst(subcategory.name)}
                          </button>
                        </div>

                        {/* Topics */}
                        {hasTopics && isSubcatExpanded && (
                          <div className="sidebar-topics">
                            {subcategory.topics.map((topic) => (
                              <button
                                key={topic}
                                className={`sidebar-topic-button ${
                                  isSelected(category.name, subcategory.name, topic) ? 'active' : ''
                                }`}
                                onClick={() => onCategorySelect(category.name, subcategory.name, topic)}
                              >
                                {capitalizeFirst(topic)}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </nav>
    </aside>
  );
};

export default Sidebar;
