-- This script creates the necessary tables for the Greeni chatbot application.
CREATE TABLE chatbot_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    total_tokens INTEGER NOT NULL,
    prompt_tokens INTEGER NOT NULL, 
    completion_tokens INTEGER NOT NULL,
    score INTEGER,
    messages JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    interaction_time INTEGER
);

-- Add comment to the table
COMMENT ON TABLE chatbot_logs IS 'Stores chat interactions and metadata with the Greeni chatbot';
