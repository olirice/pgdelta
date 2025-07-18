#!/bin/bash

# This demonstrates pgdelta's comprehensive PostgreSQL support including triggers:
# schema, table, view, sequence, index, function, trigger, constraint, and policy

pgdelta diff-headless \
    --initial-sql "
        -- Initial production schema
        CREATE SCHEMA blog;

        CREATE TABLE blog.posts (
            id SERIAL PRIMARY KEY,
            title VARCHAR(500) NOT NULL,
            content TEXT,
            view_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        );
    " \
    --master-sql "
        -- Master: current production state (empty - no changes applied)
        SELECT 1;
    " \
    --branch-sql "
        -- Branch: showcasing all pgdelta capabilities including triggers

        -- 1. Schema: Add new namespace
        CREATE SCHEMA analytics;

        -- 2. Sequence: Custom numbering
        CREATE SEQUENCE blog.post_numbers START 1000 INCREMENT 10;

        -- 3. Index: Performance optimization
        CREATE INDEX idx_posts_views ON blog.posts(view_count) WHERE view_count > 0;

        -- 4. Function: Business logic for automatic timestamps
        CREATE FUNCTION blog.update_timestamp()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        AS \$\$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        \$\$;

        -- 5. Trigger: NEW! Automatically update timestamp on changes
        CREATE TRIGGER posts_update_timestamp
        BEFORE UPDATE ON blog.posts
        FOR EACH ROW
        WHEN (OLD.title IS DISTINCT FROM NEW.title OR OLD.content IS DISTINCT FROM NEW.content)
        EXECUTE FUNCTION blog.update_timestamp();

        -- 6. View: Analytics aggregation
        CREATE VIEW analytics.popular_posts AS
        SELECT
            id,
            title,
            view_count,
            created_at
        FROM blog.posts
        WHERE view_count >= 100;

        -- 7. Constraint: Data validation
        ALTER TABLE blog.posts
        ADD CONSTRAINT posts_positive_views
        CHECK (view_count >= 0);

        -- 8. Policy: Row-level security
        ALTER TABLE blog.posts ENABLE ROW LEVEL SECURITY;

        CREATE POLICY public_read_policy ON blog.posts
        FOR SELECT
        TO public
        USING (true);
    " \
    --verbose
