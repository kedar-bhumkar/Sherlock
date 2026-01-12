-- Sherlock Database Schema
-- Run this in your Supabase SQL Editor

-- Enable pgvector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- KNOWLEDGE TABLE
-- Stores extracted content from images
-- ============================================
CREATE TABLE IF NOT EXISTS knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Classification
    category VARCHAR(100) NOT NULL DEFAULT '',
    subcategory VARCHAR(100) NOT NULL DEFAULT '',
    title VARCHAR(500) NOT NULL DEFAULT '',

    -- Content
    raw_data TEXT NOT NULL DEFAULT '',
    paraphrased_data TEXT NOT NULL DEFAULT '',

    -- Source
    image TEXT NOT NULL,  -- URL or local path
    url TEXT DEFAULT '',  -- Original source URL if applicable

    -- Processing status
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    last_error TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,

    -- Vector embedding (1536 dimensions for text-embedding-3-small)
    -- Note: HNSW index in Supabase limited to 2000 dimensions
    embedding vector(1536),

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge(category);
CREATE INDEX IF NOT EXISTS idx_knowledge_subcategory ON knowledge(subcategory);
CREATE INDEX IF NOT EXISTS idx_knowledge_status ON knowledge(status);
CREATE INDEX IF NOT EXISTS idx_knowledge_created_at ON knowledge(created_at DESC);

-- Index for vector similarity search (using HNSW for better performance)
CREATE INDEX IF NOT EXISTS idx_knowledge_embedding ON knowledge
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_knowledge_updated_at
    BEFORE UPDATE ON knowledge
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================
-- CONFIG TABLE
-- Stores application configuration (tags, llms)
-- ============================================
CREATE TABLE IF NOT EXISTS config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(100) UNIQUE NOT NULL,
    value JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER update_config_updated_at
    BEFORE UPDATE ON config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================
-- SEED DATA - Default Configuration
-- ============================================

-- Insert default tags configuration
INSERT INTO config (key, value) VALUES (
    'tags',
    '{
        "categories": [
            {
                "name": "Design",
                "subcategories": ["documentation", "architecture", "other"]
            },
            {
                "name": "Code",
                "subcategories": ["frontend", "backend", "other"]
            },
            {
                "name": "Domain",
                "subcategories": ["clinical", "non clinical", "other"]
            },
            {
                "name": "Misc",
                "subcategories": ["roadmap", "strategy", "performance", "other"]
            }
        ]
    }'::jsonb
) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

-- Insert default LLM configuration
INSERT INTO config (key, value) VALUES (
    'llms',
    '{
        "web": [
            {
                "id": "gemini-3-flash-preview",
                "name": "GPT-4o",
                "provider": "openai",
                "model": "gemini-3-flash-preview",
                "default": true
            },
            {
                "id": "claude-sonnet-4",
                "name": "Claude Sonnet 4",
                "provider": "anthropic",
                "model": "claude-sonnet-4-20250514"
            },
            {
                "id": "gemini-2.0-flash",
                "name": "Gemini 2.0 Flash",
                "provider": "google",
                "model": "gemini-2.0-flash"
            }
        ],
        "local": [
            {
                "id": "llava",
                "name": "LLaVA",
                "provider": "ollama",
                "model": "llava"
            }
        ]
    }'::jsonb
) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;


-- ============================================
-- ROW LEVEL SECURITY (Optional)
-- Enable if you want to restrict access
-- ============================================

-- Enable RLS on tables
ALTER TABLE knowledge ENABLE ROW LEVEL SECURITY;
ALTER TABLE config ENABLE ROW LEVEL SECURITY;

-- Allow all operations for authenticated users (adjust as needed)
CREATE POLICY "Allow all for authenticated users" ON knowledge
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow all for authenticated users" ON config
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Allow read access for anonymous users (for public API)
CREATE POLICY "Allow read for anon" ON knowledge
    FOR SELECT
    TO anon
    USING (true);

CREATE POLICY "Allow read for anon" ON config
    FOR SELECT
    TO anon
    USING (true);

-- Allow service role full access
CREATE POLICY "Allow all for service role" ON knowledge
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow all for service role" ON config
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);


-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Function to search knowledge by vector similarity
CREATE OR REPLACE FUNCTION search_knowledge(
    query_embedding vector(1536),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 10,
    filter_category TEXT DEFAULT NULL,
    filter_subcategory TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    category VARCHAR(100),
    subcategory VARCHAR(100),
    title VARCHAR(500),
    raw_data TEXT,
    paraphrased_data TEXT,
    image TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        k.id,
        k.category,
        k.subcategory,
        k.title,
        k.raw_data,
        k.paraphrased_data,
        k.image,
        1 - (k.embedding <=> query_embedding) AS similarity
    FROM knowledge k
    WHERE
        k.status = 'completed'
        AND k.embedding IS NOT NULL
        AND (filter_category IS NULL OR k.category = filter_category)
        AND (filter_subcategory IS NULL OR k.subcategory = filter_subcategory)
        AND 1 - (k.embedding <=> query_embedding) > match_threshold
    ORDER BY k.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;


-- ============================================
-- VERIFICATION QUERIES
-- Run these to verify the schema
-- ============================================

-- Check tables exist
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';

-- Check config data
-- SELECT * FROM config;

-- Check knowledge table structure
-- SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'knowledge';
