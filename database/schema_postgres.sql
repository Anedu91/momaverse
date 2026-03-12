-- Momaverse Database Schema (PostgreSQL)
-- Event venues, websites, and events data

-- Create database (run this connected to 'postgres' database):
-- CREATE DATABASE momaverse;
-- \c momaverse

-- ============================================================================
-- ENUM TYPES
-- ============================================================================

CREATE TYPE source_type AS ENUM ('primary', 'aggregator');
CREATE TYPE crawl_mode AS ENUM ('browser', 'json_api');
CREATE TYPE crawl_run_status AS ENUM ('running', 'completed', 'failed');
CREATE TYPE crawl_result_status AS ENUM ('pending', 'crawled', 'extracted', 'processed', 'failed');
CREATE TYPE tag_rule_type AS ENUM ('rewrite', 'exclude', 'remove');
CREATE TYPE edit_action AS ENUM ('INSERT', 'UPDATE', 'DELETE');
CREATE TYPE edit_source AS ENUM ('local', 'website', 'crawl');
CREATE TYPE sync_source AS ENUM ('local', 'website');
CREATE TYPE conflict_status AS ENUM ('pending', 'resolved_local', 'resolved_website', 'resolved_merged');

-- ============================================================================
-- LOCATIONS
-- ============================================================================

-- Stores venue/location information
CREATE TABLE IF NOT EXISTS locations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    short_name VARCHAR(100) DEFAULT NULL,             -- Display name for map labels and buttons
    very_short_name VARCHAR(50) DEFAULT NULL,          -- Abbreviated name when space is limited
    address VARCHAR(500),
    description TEXT DEFAULT NULL,
    lat DECIMAL(10, 6),
    lng DECIMAL(10, 6),
    emoji VARCHAR(10),
    alt_emoji VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_locations_name ON locations (name);
CREATE INDEX idx_locations_short_name ON locations (short_name);
CREATE INDEX idx_locations_coords ON locations (lat, lng);

-- ============================================================================
-- WEBSITES
-- ============================================================================

-- Stores event source websites for crawling
CREATE TABLE IF NOT EXISTS websites (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT DEFAULT NULL,
    base_url VARCHAR(500) DEFAULT NULL,                -- Main website URL (informational, not crawled)
    crawl_frequency INTEGER DEFAULT NULL,              -- Days between crawls
    selector VARCHAR(500) DEFAULT NULL,                -- CSS selector for click-to-load
    num_clicks INTEGER DEFAULT NULL,                   -- Number of clicks for pagination
    js_code TEXT DEFAULT NULL,                         -- JavaScript code to execute before crawling
    keywords VARCHAR(255) DEFAULT NULL,                -- URL filter keywords
    max_pages INTEGER DEFAULT 30,                      -- Max pages for deep crawl
    max_batches INTEGER DEFAULT NULL,                  -- Max extraction batches for large crawls
    notes TEXT DEFAULT NULL,
    disabled BOOLEAN DEFAULT FALSE,                    -- If true, skip this website during crawling
    source_type source_type DEFAULT 'primary',         -- primary=direct source, aggregator=lists events from other venues
    crawl_after DATE DEFAULT NULL,                     -- Do not crawl until this date (for seasonal events)
    force_crawl BOOLEAN DEFAULT FALSE,                 -- If true, crawl this website on next run regardless of frequency
    last_crawled_at TIMESTAMP NULL,                    -- When this website was last crawled
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    delay_before_return_html INTEGER DEFAULT NULL,     -- Seconds to wait for JS to render (default: 5)
    content_filter_threshold DECIMAL(3,2) DEFAULT NULL, -- Pruning filter threshold 0-1 (NULL disables filter)
    scan_full_page BOOLEAN DEFAULT NULL,               -- Scroll full page before capture (default: true)
    remove_overlay_elements BOOLEAN DEFAULT NULL,      -- Remove popup/overlay elements (default: true)
    javascript_enabled BOOLEAN DEFAULT NULL,           -- Enable JavaScript execution (default: true)
    text_mode BOOLEAN DEFAULT NULL,                    -- Disable images for text-only crawl (default: false)
    light_mode BOOLEAN DEFAULT NULL,                   -- Use minimal browser features (default: true)
    use_stealth BOOLEAN DEFAULT NULL,                  -- Use stealth mode to avoid detection
    scroll_delay DECIMAL(3,2) DEFAULT NULL,            -- Seconds to pause between scroll steps (default: 0.2)
    crawl_timeout INTEGER DEFAULT NULL,                -- Timeout in seconds for entire crawl operation (default: 120)
    crawl_frequency_locked BOOLEAN DEFAULT FALSE,      -- If true, auto-frequency adjustment is disabled
    process_images BOOLEAN DEFAULT NULL,               -- Use vision model for image-based extraction
    crawl_mode crawl_mode DEFAULT 'browser',           -- How to crawl: browser (Crawl4AI) or json_api (HTTP GET)
    json_api_config JSONB DEFAULT NULL                 -- Config for json_api mode: jsonp_callback, data_path, fields_include, date_window_days
);

CREATE INDEX idx_websites_name ON websites (name);
CREATE INDEX idx_websites_last_crawled ON websites (last_crawled_at);
CREATE INDEX idx_websites_disabled ON websites (disabled);

-- Website URLs (one website can have multiple URLs to crawl)
CREATE TABLE IF NOT EXISTS website_urls (
    id SERIAL PRIMARY KEY,
    website_id INTEGER NOT NULL,
    url VARCHAR(2000) NOT NULL,
    js_code TEXT DEFAULT NULL,                         -- JavaScript code to execute for this specific URL
    sort_order INTEGER DEFAULT 0,

    FOREIGN KEY (website_id) REFERENCES websites(id) ON DELETE CASCADE
);

CREATE INDEX idx_website_urls_website ON website_urls (website_id);

-- Website-Location relationship (many-to-many)
CREATE TABLE IF NOT EXISTS website_locations (
    id SERIAL PRIMARY KEY,
    website_id INTEGER NOT NULL,
    location_id INTEGER NOT NULL,

    UNIQUE (website_id, location_id),
    FOREIGN KEY (website_id) REFERENCES websites(id) ON DELETE CASCADE,
    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE
);

CREATE INDEX idx_website_locations_website ON website_locations (website_id);
CREATE INDEX idx_website_locations_location ON website_locations (location_id);

-- Location alternate names (after websites table for FK reference)
CREATE TABLE IF NOT EXISTS location_alternate_names (
    id SERIAL PRIMARY KEY,
    location_id INTEGER NOT NULL,
    alternate_name VARCHAR(255) NOT NULL,
    website_id INTEGER DEFAULT NULL,                   -- Scope to specific website (NULL = global)

    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE,
    FOREIGN KEY (website_id) REFERENCES websites(id) ON DELETE CASCADE
);

CREATE INDEX idx_location_alt_names_location ON location_alternate_names (location_id);
CREATE INDEX idx_location_alt_names_name ON location_alternate_names (alternate_name);
CREATE INDEX idx_location_alt_names_website ON location_alternate_names (website_id);

-- Website extra tags (tags to apply to all events from this website)
CREATE TABLE IF NOT EXISTS website_tags (
    id SERIAL PRIMARY KEY,
    website_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,

    UNIQUE (website_id, tag_id),
    FOREIGN KEY (website_id) REFERENCES websites(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

CREATE INDEX idx_website_tags_website ON website_tags (website_id);

-- ============================================================================
-- INSTAGRAM
-- ============================================================================

-- Instagram accounts - stores Instagram handles for locations and websites
CREATE TABLE IF NOT EXISTS instagram_accounts (
    id SERIAL PRIMARY KEY,
    handle VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) DEFAULT NULL,
    description VARCHAR(500) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Location-Instagram relationship (many-to-many)
CREATE TABLE IF NOT EXISTS location_instagram (
    location_id INTEGER NOT NULL,
    instagram_id INTEGER NOT NULL,

    PRIMARY KEY (location_id, instagram_id),
    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE,
    FOREIGN KEY (instagram_id) REFERENCES instagram_accounts(id) ON DELETE CASCADE
);

-- Website-Instagram relationship (many-to-many)
CREATE TABLE IF NOT EXISTS website_instagram (
    website_id INTEGER NOT NULL,
    instagram_id INTEGER NOT NULL,

    PRIMARY KEY (website_id, instagram_id),
    FOREIGN KEY (website_id) REFERENCES websites(id) ON DELETE CASCADE,
    FOREIGN KEY (instagram_id) REFERENCES instagram_accounts(id) ON DELETE CASCADE
);

-- ============================================================================
-- EVENTS
-- ============================================================================

-- Stores individual events
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    short_name VARCHAR(255) DEFAULT NULL,
    description TEXT,
    emoji VARCHAR(10),
    location_id INTEGER DEFAULT NULL,
    location_name VARCHAR(255) DEFAULT NULL,           -- Original location name from source
    sublocation VARCHAR(255) DEFAULT NULL,             -- Room, floor, etc.
    website_id INTEGER DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    archived BOOLEAN DEFAULT FALSE,                    -- If true, event is archived (no future occurrences)
    suppressed BOOLEAN DEFAULT FALSE,                  -- If true, event is hidden from display
    reviewed BOOLEAN DEFAULT FALSE,                    -- If true, event has been reviewed for suppression

    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE SET NULL,
    FOREIGN KEY (website_id) REFERENCES websites(id) ON DELETE SET NULL
);

CREATE INDEX idx_events_name ON events (name);
CREATE INDEX idx_events_location ON events (location_id);
CREATE INDEX idx_events_website ON events (website_id);
CREATE INDEX idx_events_archived ON events (archived);
CREATE INDEX idx_events_reviewed ON events (reviewed);

-- Event occurrences (one event can have multiple dates/times)
CREATE TABLE IF NOT EXISTS event_occurrences (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL,
    start_date DATE NOT NULL,
    start_time VARCHAR(20) DEFAULT NULL,               -- Time string (e.g., "7pm", "11am")
    end_date DATE DEFAULT NULL,
    end_time VARCHAR(20) DEFAULT NULL,
    sort_order INTEGER DEFAULT 0,

    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);

CREATE INDEX idx_event_occurrences_event ON event_occurrences (event_id);
CREATE INDEX idx_event_occurrences_start_date ON event_occurrences (start_date);
CREATE INDEX idx_event_occurrences_date_range ON event_occurrences (start_date, end_date);

-- Event URLs (one event can have multiple source URLs)
CREATE TABLE IF NOT EXISTS event_urls (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL,
    url VARCHAR(2000) NOT NULL,
    sort_order INTEGER DEFAULT 0,

    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);

CREATE INDEX idx_event_urls_event ON event_urls (event_id);

-- ============================================================================
-- TAGS (Generic - used by locations and events)
-- ============================================================================

-- Stores unique tag values
CREATE TABLE IF NOT EXISTS tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

CREATE INDEX idx_tags_name ON tags (name);

-- Location tags (many-to-many)
CREATE TABLE IF NOT EXISTS location_tags (
    id SERIAL PRIMARY KEY,
    location_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,

    UNIQUE (location_id, tag_id),
    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

CREATE INDEX idx_location_tags_location ON location_tags (location_id);
CREATE INDEX idx_location_tags_tag ON location_tags (tag_id);

-- Event tags (many-to-many)
CREATE TABLE IF NOT EXISTS event_tags (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,

    UNIQUE (event_id, tag_id),
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

CREATE INDEX idx_event_tags_event ON event_tags (event_id);
CREATE INDEX idx_event_tags_tag ON event_tags (tag_id);

-- ============================================================================
-- CRAWL DATA (Pipeline tracking)
-- ============================================================================

-- Crawl runs - represents a daily crawl batch
CREATE TABLE IF NOT EXISTS crawl_runs (
    id SERIAL PRIMARY KEY,
    run_date DATE NOT NULL UNIQUE,                     -- The date of the crawl run (YYYYMMDD folder)
    status crawl_run_status DEFAULT 'running',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    notes TEXT DEFAULT NULL
);

CREATE INDEX idx_crawl_runs_status ON crawl_runs (status);
CREATE INDEX idx_crawl_runs_run_date ON crawl_runs (run_date);

-- Crawl results - per-website crawl output within a run
CREATE TABLE IF NOT EXISTS crawl_results (
    id SERIAL PRIMARY KEY,
    crawl_run_id INTEGER NOT NULL,
    website_id INTEGER DEFAULT NULL,                   -- Matched website, if identified
    filename VARCHAR(255) NOT NULL,                    -- Original filename (e.g., cocusocial.json)
    event_count INTEGER DEFAULT 0,                     -- Number of events extracted
    status crawl_result_status DEFAULT 'pending',
    crawled_content TEXT DEFAULT NULL,                  -- Raw markdown from crawler
    extracted_content TEXT DEFAULT NULL,                -- Markdown table from Gemini extraction
    crawled_at TIMESTAMP NULL,
    extracted_at TIMESTAMP NULL,
    processed_at TIMESTAMP NULL,
    error_message TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (crawl_run_id, filename),
    FOREIGN KEY (crawl_run_id) REFERENCES crawl_runs(id) ON DELETE CASCADE,
    FOREIGN KEY (website_id) REFERENCES websites(id) ON DELETE SET NULL
);

CREATE INDEX idx_crawl_results_crawl_run ON crawl_results (crawl_run_id);
CREATE INDEX idx_crawl_results_website ON crawl_results (website_id);
CREATE INDEX idx_crawl_results_status ON crawl_results (status);

-- Crawl events - individual events extracted from a crawl result (raw data)
CREATE TABLE IF NOT EXISTS crawl_events (
    id SERIAL PRIMARY KEY,
    crawl_result_id INTEGER NOT NULL,
    name VARCHAR(500) NOT NULL,
    short_name VARCHAR(255) DEFAULT NULL,
    description TEXT,
    emoji VARCHAR(10),
    location_name VARCHAR(255) DEFAULT NULL,           -- Raw location name from crawl
    sublocation VARCHAR(255) DEFAULT NULL,
    location_id INTEGER DEFAULT NULL,                  -- Matched location from database
    url VARCHAR(2000) DEFAULT NULL,                    -- Primary event URL
    raw_data JSONB DEFAULT NULL,                       -- Full JSON object from crawl
    content_hash CHAR(64) DEFAULT NULL,                -- SHA-256 hash for deduplication
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (crawl_result_id) REFERENCES crawl_results(id) ON DELETE CASCADE
);

CREATE INDEX idx_crawl_events_crawl_result ON crawl_events (crawl_result_id);
CREATE INDEX idx_crawl_events_name ON crawl_events (name);
CREATE INDEX idx_crawl_events_content_hash ON crawl_events (content_hash);
CREATE INDEX idx_crawl_events_location_name ON crawl_events (location_name);
CREATE INDEX idx_crawl_events_location_id ON crawl_events (location_id);

-- Crawl event occurrences - dates/times for crawl events
CREATE TABLE IF NOT EXISTS crawl_event_occurrences (
    id SERIAL PRIMARY KEY,
    crawl_event_id INTEGER NOT NULL,
    start_date DATE NOT NULL,
    start_time VARCHAR(20) DEFAULT NULL,
    end_date DATE DEFAULT NULL,
    end_time VARCHAR(20) DEFAULT NULL,
    sort_order INTEGER DEFAULT 0,

    FOREIGN KEY (crawl_event_id) REFERENCES crawl_events(id) ON DELETE CASCADE
);

CREATE INDEX idx_crawl_event_occurrences_event ON crawl_event_occurrences (crawl_event_id);
CREATE INDEX idx_crawl_event_occurrences_start_date ON crawl_event_occurrences (start_date);

-- Crawl event tags - tags for crawl events
CREATE TABLE IF NOT EXISTS crawl_event_tags (
    id SERIAL PRIMARY KEY,
    crawl_event_id INTEGER NOT NULL,
    tag VARCHAR(100) NOT NULL,                         -- Raw tag string from crawl

    FOREIGN KEY (crawl_event_id) REFERENCES crawl_events(id) ON DELETE CASCADE
);

CREATE INDEX idx_crawl_event_tags_event ON crawl_event_tags (crawl_event_id);
CREATE INDEX idx_crawl_event_tags_tag ON crawl_event_tags (tag);

-- Event sources - links final events to the crawl events that contributed to them
CREATE TABLE IF NOT EXISTS event_sources (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL,
    crawl_event_id INTEGER NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE,                  -- Is this the primary/first source for this event
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (event_id, crawl_event_id),
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (crawl_event_id) REFERENCES crawl_events(id) ON DELETE CASCADE
);

CREATE INDEX idx_event_sources_event ON event_sources (event_id);
CREATE INDEX idx_event_sources_crawl_event ON event_sources (crawl_event_id);

-- ============================================================================
-- TAG RULES
-- ============================================================================

-- Rules for processing tags extracted from events
CREATE TABLE IF NOT EXISTS tag_rules (
    id SERIAL PRIMARY KEY,
    rule_type tag_rule_type NOT NULL,                   -- rewrite=map to new tag, exclude=filter out, remove=skip entire event
    pattern VARCHAR(100) NOT NULL,                     -- Tag pattern to match (lowercase)
    replacement VARCHAR(100) DEFAULT NULL,             -- Replacement tag (only for rewrite rules)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (rule_type, pattern)
);

CREATE INDEX idx_tag_rules_rule_type ON tag_rules (rule_type);
CREATE INDEX idx_tag_rules_pattern ON tag_rules (pattern);

-- ============================================================================
-- USER FEEDBACK
-- ============================================================================

-- Feedback submitted by users via the website
CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    message TEXT NOT NULL,
    user_agent VARCHAR(500) DEFAULT NULL,
    page_url VARCHAR(500) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_feedback_created_at ON feedback (created_at);

-- ============================================================================
-- USER ACCOUNTS (Optional authentication)
-- ============================================================================

-- Users table - optional accounts for tracking edits
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(100) DEFAULT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP NULL
);

CREATE INDEX idx_users_email ON users (email);

-- ============================================================================
-- EDIT HISTORY & SYNC
-- ============================================================================

-- Immutable edit log - tracks all changes to core tables
CREATE TABLE IF NOT EXISTS edits (
    id SERIAL PRIMARY KEY,
    edit_uuid CHAR(36) NOT NULL UNIQUE,                -- UUID for global uniqueness across databases
    table_name VARCHAR(50) NOT NULL,                   -- Table that was edited
    record_id INTEGER NOT NULL,                        -- ID of the edited record
    field_name VARCHAR(100) DEFAULT NULL,              -- NULL for INSERT/DELETE, field name for UPDATE
    action edit_action NOT NULL,
    old_value TEXT DEFAULT NULL,                        -- Previous value (NULL for INSERT)
    new_value TEXT DEFAULT NULL,                        -- New value (NULL for DELETE)
    source edit_source NOT NULL,                       -- Where edit originated
    user_id INTEGER DEFAULT NULL,                      -- User who made the edit (NULL if anonymous)
    editor_ip VARCHAR(45) DEFAULT NULL,                -- IP address for anonymous edits
    editor_user_agent VARCHAR(500) DEFAULT NULL,       -- Browser user agent
    editor_info VARCHAR(500) DEFAULT NULL,             -- Additional context (e.g., crawl_run:123)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    applied_at TIMESTAMP NULL,                         -- When edit was applied (NULL if pending)

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX idx_edits_table_record ON edits (table_name, record_id);
CREATE INDEX idx_edits_source ON edits (source);
CREATE INDEX idx_edits_created ON edits (created_at);
CREATE INDEX idx_edits_user ON edits (user_id);

-- Sync state - tracks sync progress between local and production
CREATE TABLE IF NOT EXISTS sync_state (
    id SERIAL PRIMARY KEY,
    source sync_source NOT NULL UNIQUE,                -- Which database this tracks
    last_synced_edit_id INTEGER DEFAULT NULL,           -- Last edit ID synced FROM this source
    last_sync_at TIMESTAMP NULL
);

-- Conflicts - pending conflicts for manual review
CREATE TABLE IF NOT EXISTS conflicts (
    id SERIAL PRIMARY KEY,
    local_edit_id INTEGER NOT NULL,
    website_edit_id INTEGER NOT NULL,
    table_name VARCHAR(50) NOT NULL,
    record_id INTEGER NOT NULL,
    field_name VARCHAR(100) DEFAULT NULL,
    local_value TEXT DEFAULT NULL,
    website_value TEXT DEFAULT NULL,
    status conflict_status DEFAULT 'pending',
    resolved_value TEXT DEFAULT NULL,
    resolved_by INTEGER DEFAULT NULL,                  -- User who resolved the conflict
    resolved_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (local_edit_id) REFERENCES edits(id) ON DELETE CASCADE,
    FOREIGN KEY (website_edit_id) REFERENCES edits(id) ON DELETE CASCADE,
    FOREIGN KEY (resolved_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX idx_conflicts_status ON conflicts (status);
CREATE INDEX idx_conflicts_table_record ON conflicts (table_name, record_id);
CREATE INDEX idx_conflicts_created ON conflicts (created_at);

-- ============================================================================
-- GRANTEES
-- ============================================================================

-- Grantees table - grant recipients for potential website additions
CREATE TABLE IF NOT EXISTS grantees (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,                 -- Organization name from grant list
    area VARCHAR(100) DEFAULT NULL,                    -- Region (e.g., New York City, Long Island)
    website_id INTEGER DEFAULT NULL,                   -- Linked website if added to our database
    exclusion_reason VARCHAR(500) DEFAULT NULL,         -- Why website was not added (if applicable)
    notes TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (website_id) REFERENCES websites(id) ON DELETE SET NULL
);

CREATE INDEX idx_grantees_area ON grantees (area);
CREATE INDEX idx_grantees_website ON grantees (website_id);
