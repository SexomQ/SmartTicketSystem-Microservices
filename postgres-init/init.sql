-- PostgreSQL initialization script for Smart Ticket System Microservices
-- This script runs automatically when the postgres container is first created

-- Create database if it doesn't exist (this is handled by POSTGRES_DB env var)
-- But we can ensure the schema is correct

-- Set timezone
SET timezone = 'UTC';

-- Enable required extensions if needed
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE smartticket TO postgres;

-- Note: Individual service databases will be initialized by each service
-- This is just the base setup
