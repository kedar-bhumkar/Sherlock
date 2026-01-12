-- MCP Vector Search Functions
-- Run this in your Supabase SQL Editor after 001_initial_schema.sql

-- ============================================
-- VECTOR SEARCH FUNCTIONS FOR MCP
-- ============================================

-- Function to match knowledge by vector similarity with filters
CREATE OR REPLACE FUNCTION match_knowledge(
    query_embedding vector(1536),
    match_threshold FLOAT DEFAULT 0.5,
    match_count INT DEFAULT 10,
    filter_category TEXT DEFAULT NULL,
    filter_subcategory TEXT DEFAULT NULL,
    filter_topic TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    category VARCHAR(100),
    subcategory VARCHAR(100),
    topic VARCHAR(100),
    title VARCHAR(500),
    raw_data TEXT,
    paraphrased_data TEXT,
    image TEXT,
    url TEXT,
    status VARCHAR(20),
    last_error TEXT,
    retry_count INTEGER,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
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
        k.topic,
        k.title,
        k.raw_data,
        k.paraphrased_data,
        k.image,
        k.url,
        k.status,
        k.last_error,
        k.retry_count,
        k.created_at,
        k.updated_at,
        (1 - (k.embedding <=> query_embedding))::FLOAT AS similarity
    FROM knowledge k
    WHERE
        k.status = 'completed'
        AND k.embedding IS NOT NULL
        AND (filter_category IS NULL OR k.category = filter_category)
        AND (filter_subcategory IS NULL OR k.subcategory = filter_subcategory)
        AND (filter_topic IS NULL OR k.topic = filter_topic)
        AND (1 - (k.embedding <=> query_embedding)) > match_threshold
    ORDER BY k.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Simple version without filters (fallback)
CREATE OR REPLACE FUNCTION match_knowledge_simple(
    query_embedding vector(1536),
    match_count INT DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    category VARCHAR(100),
    subcategory VARCHAR(100),
    topic VARCHAR(100),
    title VARCHAR(500),
    raw_data TEXT,
    paraphrased_data TEXT,
    image TEXT,
    url TEXT,
    status VARCHAR(20),
    last_error TEXT,
    retry_count INTEGER,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
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
        k.topic,
        k.title,
        k.raw_data,
        k.paraphrased_data,
        k.image,
        k.url,
        k.status,
        k.last_error,
        k.retry_count,
        k.created_at,
        k.updated_at,
        (1 - (k.embedding <=> query_embedding))::FLOAT AS similarity
    FROM knowledge k
    WHERE
        k.status = 'completed'
        AND k.embedding IS NOT NULL
    ORDER BY k.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION match_knowledge TO anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION match_knowledge_simple TO anon, authenticated, service_role;
