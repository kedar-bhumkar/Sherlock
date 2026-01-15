export interface ConceptDetail {
  concept: string;
  expanded_information?: string;
  expanded?: string;
  expanded_info?: string;
}

export interface ParaphrasedDataStructure {
  summary: string;
  details: ConceptDetail[];
}

export interface KnowledgeItem {
  id: string;
  category: string;
  subcategory: string;
  topic: string;
  title: string;
  raw_data: string;
  paraphrased_data: string;
  image: string;
  url: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  last_error?: string;
  retry_count: number;
  created_at: string;
  updated_at: string;
}

export interface PaginationMetadata {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface KnowledgeResponse {
  data: KnowledgeItem[];
  metadata: PaginationMetadata;
}

export interface Subcategory {
  name: string;
  topics: string[];
}

export interface Category {
  name: string;
  subcategories: Subcategory[];
}

export interface TagsConfig {
  categories: Category[];
}

export interface LLMConfig {
  id: string;
  name: string;
  provider: string;
  model: string;
  default?: boolean;
}

export interface LLMsConfig {
  web: LLMConfig[];
  local: LLMConfig[];
}

export interface ApiError {
  message: string;
  status?: number;
}

// Auth Types
export interface TOTPVerifyResponse {
  success: boolean;
  token: string | null;
  message: string;
}

export interface TOTPStatusResponse {
  enabled: boolean;
  configured: boolean;
}

export interface SessionValidateResponse {
  valid: boolean;
}
