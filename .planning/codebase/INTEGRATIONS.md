# External Integrations

**Analysis Date:** 2026-02-24

## APIs & External Services

**AI/Content Extraction:**
- Google Gemini API (gemini-2.5-flash-preview-05-20)
  - Used for: Structured event extraction from crawled website content
  - SDK: `google-genai` Python package
  - Auth: `GEMINI_API_KEY` environment variable
  - Implementation: `pipeline/extractor.py` - Two-pass extraction with Pydantic schemas for large pages
  - Timeout: 120 seconds (configurable via `GEMINI_TIMEOUT`)

**Web Crawling:**
- crawl4ai - Advanced web scraping framework
  - Used for: Automated website crawling, content extraction, markdown conversion
  - Features: Markdown generation, content filtering, deep crawling with BestFirstCrawlingStrategy
  - Configuration: Browser config, URL pattern filtering, content pruning
  - Implementation: `pipeline/crawler.py`

**Maps & Geolocation:**
- MapLibre GL 4.7.1 - Open-source web mapping
  - SDK: Loaded from unpkg.com CDN
  - Usage: Interactive map rendering with vector tiles, markers, popups
  - Features: Navigation controls, zoom/pan, custom styling with JSON style files
  - Geolocation: Native browser Geolocation API (user-triggered, optional)
  - Attribution: Protomaps + OpenStreetMap

**Map Tiles:**
- Protomaps - Vector tile provider (referenced in attribution)
  - Tile source: Custom map style JSON files (`data/map-style-dark.json`, `data/map-style-light.json`)
  - Theme support: Separate dark and light styles

## Data Storage

**Databases:**
- MySQL 8.0+ (primary database)
  - Connection: PDO in PHP (`src/api/`), mysql-connector-python in Python (`pipeline/`)
  - Host/credentials: Configured in `src/api/config.php` (PHP) and `pipeline/db.py` (Python)
  - Supports both local (XAMPP) and production (Namecheap) environments
  - Schema: 23 tables covering websites, events, locations, tags, crawl results
  - Location: `database/schema.sql`

**File Storage:**
- Local filesystem only
  - JSON data files: `src/data/` (events, locations, tags, related tags)
  - Images: `src/images/` (icons, logos)
  - Fonts: `src/fonts/` (compressed TTF/WOFF2)
  - Admin data: Served from `src/admin/`

**Caching:**
- crawl4ai caching (CacheMode) - Caches crawled website content to avoid redundant requests
- Browser localStorage - Client-side storage for user preferences, settings (via `SafeStorage` utility)
- HTTP caching via .htaccess rules

## Authentication & Identity

**Auth Provider:**
- Custom/None for end users
  - Application is fully public, no user authentication required
  - User preferences stored in browser localStorage (settings, selected tags, date ranges)

**Admin/API Access:**
- Database credentials (hardcoded in config files)
  - `src/api/config.php` - Database credentials for feedback API and admin
  - `pipeline/db.py` - Database credentials for pipeline
  - No API key authentication for admin endpoints

**Feedback Collection:**
- User feedback stored in MySQL
  - No authentication; stores user agent and page URL for context
  - Implementation: `src/api/feedback.php`

## Monitoring & Observability

**Error Tracking:**
- None detected
- Errors logged to console in frontend
- Python pipeline has verbose logging output to stdout/stderr

**Logs:**
- Frontend: Console logs and toast notifications for user-facing errors
- Python pipeline: Stdout/stderr output with step-by-step progress reporting
- PHP API: Error logging via `error_log()` function (to Apache/server error log)
- Database: MySQL error log (depends on server configuration)

**Debug Mode:**
- Easter egg: Search for "debug" in frontend to toggle debug visualization overlay
  - Implementation: `src/js/script.js` (`handleSpecialSearchTerms`)
  - Shows viewport calculations and visible item boundaries

## CI/CD & Deployment

**Hosting:**
- Web hosting with PHP and MySQL support (e.g., Namecheap cPanel)
- Deployment via FTP upload of `dist/` directory
- SSH access available for database synchronization tasks

**CI Pipeline:**
- None detected; manual deployment process
- Local build with `npm run build`, then FTP upload to production

**Deployment Process:**
- Build frontend: `npm run build` → `dist/`
- Upload via FTP: `dist/` contents to web server public_html
- Pipeline runs on server (cron job or manual trigger)
- Database synced via SSH if needed

## Environment Configuration

**Required env vars:**
- `GEMINI_API_KEY` - Google Gemini API key (for event extraction)
- `FTP_HOST` - FTP server hostname
- `FTP_USER` - FTP username
- `FTP_PASSWORD` - FTP password
- `FTP_REMOTE_DIR` - Optional remote directory on FTP server
- `PUBLIC_HTML_FTP_USER` - FTP user for public_html uploads
- `SSH_HOST` - SSH server hostname (for database sync)
- `SSH_USER` - SSH username
- `SSH_PORT` - SSH port
- `PROD_DB_NAME` - Production database name
- `PROD_DB_USER` - Production database user
- `PROD_DB_PASS` - Production database password

**Secrets location:**
- `.env` file (Python dotenv format) - Used by pipeline
- Environment variables - Set via cPanel or server configuration
- `src/api/config.php` - Hardcoded database credentials (not in git)
- `pipeline/db.py` - Hardcoded database credentials (not in git)

## Webhooks & Callbacks

**Incoming:**
- None detected

**Outgoing:**
- None detected; application is pull-based (crawls websites on schedule)

## Data Pipeline Integrations

**Website Crawling Workflow:**
1. `main.py` - Orchestrates pipeline
2. `crawler.py` - Crawls websites using crawl4ai, stores HTML in database
3. `extractor.py` - Uses Gemini AI to extract structured events via Pydantic schemas
4. `processor.py` - Parses extraction results, enriches with location data
5. `merger.py` - Deduplicates and merges crawl_events into final events table
6. `exporter.py` - Generates JSON files for website consumption
7. `uploader.py` - Uploads JSON files to FTP server
8. `frequency_analyzer.py` - Analyzes tag frequencies in visible events

**Data Sync:**
- SSH-based database synchronization for production (via cron or manual trigger)
- FTP upload of JSON exports

## Frontend Data Loading

**Two-Phase Loading:**
- Phase 1: Load initial/lightweight datasets (`events.init.json`, `locations.init.json`, `tags.json`)
- Phase 2 (async): Load full dataset (`events.full.json`, `locations.full.json`) and related tags in background
- Related tags deferred until Phase 2 for performance

**Data URLs:**
- `data/events.init.json` - Initial events for quick startup
- `data/locations.init.json` - Initial locations
- `data/events.full.json` - Complete events dataset
- `data/locations.full.json` - Complete locations dataset
- `data/tags.json` - Tag configuration (geotags, background colors)
- `data/related_tags.json` - Tag hierarchy and relationships
- `data/map-style-dark.json`, `data/map-style-light.json` - MapLibre style definitions

**Data Manager:**
- Implementation: `src/js/data/dataManager.js`
- Handles: Fetching with timeout (10s default), error handling, data processing/indexing
- Features: Abort on timeout, retry logic, detailed error messages

## CDN & External Resources

**JavaScript Libraries:**
- maplibre-gl 4.7.1 (unpkg.com) - Web mapping
- flatpickr (cdn.jsdelivr.net) - Date picker
  - Note: Bundled into app.js during build (not loaded from CDN in production)

**Fonts:**
- Inter font from rsms.me - Typography
  - Loaded via `<link rel="preconnect">` and `<link rel="stylesheet">`

**No Third-Party Analytics:**
- No Google Analytics, Mixpanel, or other tracking detected
- No ads or third-party scripts in production

---

*Integration audit: 2026-02-24*
