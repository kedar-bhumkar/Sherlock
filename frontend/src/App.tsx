import React, { useState } from 'react';
import { Header, Sidebar, ContentGrid, Modal } from './components';
import { useKnowledge, useModal } from './hooks';
import { KnowledgeItem } from './types';
import { ALL_CATEGORIES, ALL_SUBCATEGORIES, ALL_TOPICS, DEFAULT_PAGE_SIZE } from './utils/constants';
import './App.css';

const App: React.FC = () => {
  const [selectedCategory, setSelectedCategory] = useState(ALL_CATEGORIES);
  const [selectedSubcategory, setSelectedSubcategory] = useState(ALL_SUBCATEGORIES);
  const [selectedTopic, setSelectedTopic] = useState(ALL_TOPICS);
  const [currentPage, setCurrentPage] = useState(1);

  const { data, metadata, loading, error } = useKnowledge(
    selectedCategory,
    selectedSubcategory,
    selectedTopic,
    currentPage,
    DEFAULT_PAGE_SIZE
  );

  const { isOpen, data: selectedItem, openModal, closeModal } = useModal<KnowledgeItem>();

  const handleCategorySelect = (category: string, subcategory: string, topic: string) => {
    setSelectedCategory(category);
    setSelectedSubcategory(subcategory);
    setSelectedTopic(topic);
    setCurrentPage(1); // Reset to first page when changing filters
    closeModal(); // Close modal when navigating to prevent stale data display
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    // Scroll to top of content area
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleItemClick = (item: KnowledgeItem) => {
    openModal(item);
  };

  const handleSettingsClick = () => {
    // TODO: Implement settings modal
    console.log('Settings clicked');
  };

  return (
    <div className="app">
      <Header onSettingsClick={handleSettingsClick} />

      <div className="app-layout">
        <Sidebar
          selectedCategory={selectedCategory}
          selectedSubcategory={selectedSubcategory}
          selectedTopic={selectedTopic}
          onCategorySelect={handleCategorySelect}
        />

        <main className="app-main">
          <ContentGrid
            items={data}
            loading={loading}
            error={error?.message || null}
            metadata={metadata}
            onItemClick={handleItemClick}
            onPageChange={handlePageChange}
          />
        </main>
      </div>

      <Modal
        isOpen={isOpen}
        item={selectedItem}
        onClose={closeModal}
      />
    </div>
  );
};

export default App;
