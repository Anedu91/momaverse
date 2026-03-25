# Event Processing Pipeline

Crawls event websites, extracts structured data with Gemini AI, and merges deduplicated events into the database.

## Setup

### Prerequisites

- Python 3.12+
- PostgreSQL
- [uv](https://docs.astral.sh/uv/) (package manager)

### Install Dependencies

```bash
cd pipeline
uv sync
```

### Environment Variables

Create a `.env` file in the project root:

```env
FOMO_ENV=local          # "local" or "production"

# Gemini AI
GEMINI_API_KEY="your-api-key"
GEMINI_MODEL="gemini-2.5-flash"   # default
GEMINI_TIMEOUT=120                 # seconds, default

# Production DB (only needed if FOMO_ENV=production)
PROD_DB_HOST="..."
PROD_DB_NAME="..."
PROD_DB_USER="..."
PROD_DB_PASS="..."
```

## Usage

```bash
# Run full pipeline (all sources due for crawling)
uv run main.py

# Run specific source by ID
uv run main.py --ids 4

# Run multiple sources
uv run main.py --ids 4,12,25

# Limit to first N due sources
uv run main.py --limit 5
```

When `--ids` is used, `crawl_frequency` is ignored — those sources are always crawled.

## Pipeline Steps

```
STEP 0: Resume incomplete crawl results from previous runs
STEP 1: Find sources due for crawling
STEP 2: Crawl sources (browser or JSON API)
STEP 3: Extract events with Gemini AI
STEP 4: Process & enrich events (locations, tags, dates)
STEP 5: Merge into final events table & archive outdated
```

### Data Flow

```
sources + source_urls + crawl_configs
     ↓
[Crawl] → crawl_contents.crawled_content
     ↓
[Extract] → crawl_contents.extracted_content
     ↓
[Process] → extracted_events (with occurrences, tags, location_id)
     ↓
[Merge] → events + event_occurrences + event_urls + event_tags + event_sources
```

## Module Structure

```
pipeline/
├── main.py               # Orchestrator — runs all 5 steps
├── crawler.py             # Web crawling (browser + JSON API modes)
├── extractor.py           # Gemini AI event extraction
├── processor.py           # Event enrichment (locations, tags, dates)
├── merger.py              # Deduplication & merging into final events
├── location_resolver.py   # Auto-creates locations from JSON API data
├── db.py                  # Database operations
├── exporter.py            # JSON export
└── tests/
    └── test_processor.py
```

## Database Tables

| Table | Purpose |
|-------|---------|
| `sources` | Event source websites |
| `crawl_configs` | Crawl settings per source (1:1 with sources) |
| `source_urls` | URLs to crawl per source (1:many) |
| `crawl_jobs` | Pipeline execution records |
| `crawl_results` | Status tracking per source per job |
| `crawl_contents` | Raw HTML/markdown + extracted JSON |
| `extracted_events` | Structured events from Gemini (before dedup) |
| `extracted_event_logs` | Audit log (created/merged/skipped/failed) |
| `events` | Final deduplicated events |
| `event_occurrences` | Date/time instances |
| `event_urls` | URLs associated with events |
| `event_tags` | Event ↔ tag associations |
| `event_sources` | Lineage: which extracted_event → which event |
| `locations` | Venues with coordinates |
| `location_alternate_names` | Alternate names for location matching |
| `tags` | Tag definitions |
| `tag_rules` | Tag rewrite/exclude/remove rules |

---

## Creating Sources

A source needs three things: a record in `sources`, a `crawl_configs` entry, and one or more `source_urls`.

### 1. Browser Mode (default)

For HTML/JavaScript websites. Uses [Crawl4AI](https://github.com/unclecode/crawl4ai) to render pages in a browser.

```sql
-- Create the source
INSERT INTO sources (name, source_type)
VALUES ('My Event Site', 'primary');

-- Add crawl config (source_id = the ID from above)
INSERT INTO crawl_configs (source_id, crawl_mode, crawl_frequency)
VALUES (1, 'browser', 7);

-- Add URL(s) to crawl
INSERT INTO source_urls (source_id, url, sort_order)
VALUES (1, 'https://example.com/events', 1);
```

### 2. JSON API Mode

For structured API endpoints that return JSON directly. Skips browser rendering and Gemini extraction — maps fields directly to events.

```sql
INSERT INTO crawl_configs (source_id, crawl_mode, crawl_frequency, json_api_config)
VALUES (1, 'json_api', 3, '{
  "base_url": "https://api.example.com/events",
  "data_path": "results.events",
  "date_window_days": 30,
  "jsonp_callback": null,
  "fields_include": null
}');
```

**json_api_config fields:**

| Field | Description |
|-------|-------------|
| `base_url` | API endpoint URL |
| `data_path` | Dot-separated path to events in response (e.g., `"data.events"`) |
| `date_window_days` | Only include events within N days from today (default: 30) |
| `jsonp_callback` | JSONP wrapper function name to strip (optional) |
| `fields_include` | Array of field names to keep (optional, keeps all if null) |

---

## Crawl Config Options

All fields in `crawl_configs` with their purpose and defaults:

### Scheduling

| Field | Default | Description |
|-------|---------|-------------|
| `crawl_frequency` | 7 | Days between crawls |
| `force_crawl` | false | Force crawl on next run (resets to false after) |
| `crawl_after` | null | Don't crawl until this date (for seasonal sources) |

### Browser Rendering

| Field | Default | Description |
|-------|---------|-------------|
| `text_mode` | true | Disable images for faster text-only crawls |
| `light_mode` | true | Minimal browser features for speed |
| `use_stealth` | false | Undetected browser mode for bot detection bypass |
| `javascript_enabled` | true | Enable JavaScript execution |

Sources with different `text_mode`/`light_mode`/`use_stealth` values get separate browser instances.

### Page Interaction

| Field | Default | Description |
|-------|---------|-------------|
| `scan_full_page` | true | Scroll the entire page before capturing (loads lazy content) |
| `scroll_delay` | 0.2 | Seconds to pause between scroll steps |
| `delay_before_return_html` | 5 | Seconds to wait for JS to finish after page load |
| `remove_overlay_elements` | false | Remove popups/cookie banners that obscure content |
| `crawl_timeout` | 120 | Total timeout in seconds for the entire crawl |

### Click-to-Load Pagination

For sites with "Load More" buttons:

| Field | Default | Description |
|-------|---------|-------------|
| `selector` | null | CSS selector for the pagination/load-more button |
| `num_clicks` | 2 | Number of times to click the button |

Example: A site with a "Show More Events" button:

```sql
UPDATE crawl_configs SET
  selector = '.load-more-btn',
  num_clicks = 5
WHERE source_id = 1;
```

The crawler generates JavaScript that clicks the button N times with 1-second delays between clicks.

### Custom JavaScript

For complex page interactions beyond simple button clicks:

| Field | Default | Description |
|-------|---------|-------------|
| `js_code` | null | Custom JavaScript to execute before content capture |

This overrides `selector`/`num_clicks` if set. Can also be set per-URL in `source_urls.js_code`.

```sql
-- Source-level JS (applies to all URLs)
UPDATE crawl_configs SET
  js_code = 'document.querySelector(".tab-future").click(); await new Promise(r => setTimeout(r, 2000));'
WHERE source_id = 1;

-- Per-URL JS (overrides source-level for this URL only)
UPDATE source_urls SET
  js_code = 'document.querySelector(".month-next").click();'
WHERE source_id = 1 AND url = 'https://example.com/calendar';
```

### Deep Crawling with Keywords

For sites where events are spread across multiple pages linked from a listing:

| Field | Default | Description |
|-------|---------|-------------|
| `keywords` | null | Comma-separated URL patterns to follow (e.g., `"event, show, concert"`) |
| `max_pages` | 30 | Maximum pages to crawl when following links |

**How it works:**
1. Crawls the main URL
2. Finds all links on the page
3. Follows links whose URL contains any keyword (wildcard match: `*event*`)
4. Scrapes each matched page
5. Combines all content for extraction

**When to use:** When the listing page only shows titles/dates, but full event details are on individual pages.

**When NOT to use:** When all event info is already visible on the listing page (like Indie Hoy's `/eventos/`).

Example:

```sql
UPDATE crawl_configs SET
  keywords = 'event, show, concert',
  max_pages = 20
WHERE source_id = 1;
```

### Content Filtering

| Field | Default | Description |
|-------|---------|-------------|
| `content_filter_threshold` | null | Pruning filter aggressiveness, 0.0–1.0. Null = disabled |

When set, applies a `PruningContentFilter` that removes boilerplate content (nav, footer, ads). Higher values = more aggressive filtering. Start with `0.5` and adjust.

### Extraction Settings

| Field | Default | Description |
|-------|---------|-------------|
| `process_images` | false | Use Gemini vision model to extract events from flyer images |
| `max_batches` | 3 | Max enrichment batches for large pages (limits API cost) |
| `notes` | null | Extra instructions passed to Gemini in the extraction prompt |

### Tags

| Field | Default | Description |
|-------|---------|-------------|
| `default_tags` | null | Array of tags automatically added to all events from this source |

---

## Source URLs

Each source can have multiple URLs. They're crawled sequentially and their content is combined.

```sql
INSERT INTO source_urls (source_id, url, sort_order)
VALUES
  (1, 'https://example.com/events', 1),
  (1, 'https://example.com/events/page/2', 2);
```

### URL Templates

URLs support date placeholders resolved at crawl time:

| Template | Resolves to | Example |
|----------|-------------|---------|
| `{{month}}` | Current month (lowercase) | `march` |
| `{{year}}` | Current year | `2026` |
| `{{next_month}}` | Next month name | `april` |
| `{{next_month_year}}` | Year of next month | `2026` |

```sql
INSERT INTO source_urls (source_id, url, sort_order)
VALUES (1, 'https://example.com/events/{{month}}-{{year}}', 1);
-- Resolves to: https://example.com/events/march-2026
```

### Per-URL JavaScript

Each URL can have its own JavaScript that overrides the source-level `js_code`:

```sql
INSERT INTO source_urls (source_id, url, js_code, sort_order)
VALUES (1, 'https://example.com/calendar', 'document.querySelector(".next-month").click();', 1);
```

---

## Common Source Configurations

### Simple static page

All events are listed on one page, no JavaScript needed:

```sql
INSERT INTO crawl_configs (source_id, crawl_mode, crawl_frequency)
VALUES (1, 'browser', 7);
```

### JavaScript-heavy site with lazy loading

Events load as you scroll:

```sql
INSERT INTO crawl_configs (source_id, crawl_mode, scan_full_page, delay_before_return_html)
VALUES (1, 'browser', true, 8);
```

### Site with "Load More" button

```sql
INSERT INTO crawl_configs (source_id, crawl_mode, selector, num_clicks)
VALUES (1, 'browser', 'button.load-more', 5);
```

### Site with bot detection

```sql
INSERT INTO crawl_configs (source_id, crawl_mode, use_stealth, text_mode, light_mode)
VALUES (1, 'browser', true, false, false);
```

### Event listing with detail pages

Listing page links to individual event pages:

```sql
INSERT INTO crawl_configs (source_id, crawl_mode, keywords, max_pages)
VALUES (1, 'browser', 'evento, show, agenda', 20);
```

### Image flyers (no text content)

Events are posted as flyer images:

```sql
INSERT INTO crawl_configs (source_id, crawl_mode, process_images)
VALUES (1, 'browser', true);
```

### Monthly calendar with URL templates

```sql
INSERT INTO source_urls (source_id, url, sort_order) VALUES
  (1, 'https://example.com/calendar/{{month}}-{{year}}', 1),
  (1, 'https://example.com/calendar/{{next_month}}-{{next_month_year}}', 2);
```

---

## Tag Rules

Control how tags are processed across all sources:

```sql
-- Rewrite: normalize tag names
INSERT INTO tag_rules (rule_type, pattern, replacement)
VALUES ('rewrite', 'standup', 'Comedy');

-- Exclude: silently remove a tag
INSERT INTO tag_rules (rule_type, pattern)
VALUES ('exclude', 'Lorem');

-- Remove: skip the entire event if it has this tag
INSERT INTO tag_rules (rule_type, pattern)
VALUES ('remove', 'Cancelled');
```

## Troubleshooting

### Source returns 0 pages / 0 chars

- **Check `scan_full_page`**: If null, set to `true` — the page may need scrolling to load content.
- **Check `keywords`**: If set, the crawler follows links instead of scraping the main page. Remove keywords if all events are already on the listing page.
- **Check `delay_before_return_html`**: Increase if the page needs more time to render JavaScript.

### Bot detection / verification page

Set `use_stealth = true`. Also set `text_mode = false` and `light_mode = false` — minimal browser features can trigger detection.

### Content too small (under 500 chars)

The pipeline skips extraction if crawled content is under 500 bytes (prevents Gemini hallucinations). Check if the site requires JavaScript, scrolling, or button clicks to reveal content.

### Events not matching existing locations

The processor tries multiple matching strategies (exact name, substring, alternate names, address, short name). If a venue isn't matching:

```sql
INSERT INTO location_alternate_names (location_id, alternate_name)
VALUES (42, 'The Venue Formerly Known As...');
```

### Duplicate events being created

Check if the location matches. Events are deduplicated by location + date + similar name. If the same venue has two location records, events won't merge. Consolidate locations and add alternate names.
