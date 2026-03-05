# Phase 4: JSON API Crawling - Research

**Researched:** 2026-03-05
**Domain:** HTTP-based JSON/JSONP crawling, token optimization, pipeline routing
**Confidence:** HIGH

## Summary

Phase 4 adds a lightweight JSON API crawling path to the existing browser-based pipeline. The first (and currently only) target is Alternativa Teatral, which exposes a JSONP endpoint returning ~920 theater events. The implementation requires three changes: a new `crawl_json_api()` function in `crawler.py`, two new columns on the `websites` table (with corresponding `db.py` changes), and crawl routing logic in `main.py` that bypasses the browser for `json_api` mode websites.

The codebase already uses `httpx` (v0.28.1) for HTTP requests in `extractor.py`, so no new dependencies are needed. The core technical challenges are: JSONP wrapper stripping, date-based event filtering to reduce token cost, field selection to minimize payload size, and flattening structured JSON into markdown that the existing Gemini extraction step can consume.

**Primary recommendation:** Keep the implementation minimal -- a single function in `crawler.py` that does HTTP GET, strips JSONP, filters by date, selects fields, and outputs markdown. No new files, no abstractions. The existing pipeline architecture (crawl -> extract -> process -> merge) remains unchanged; only the crawl step differs.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.28.1 | HTTP GET for JSON/JSONP endpoints | Already in project, used by extractor.py; async-capable |
| json (stdlib) | - | Parse JSON after JSONP stripping | Standard library, no dependency needed |
| re (stdlib) | - | Strip JSONP callback wrapper | Simple regex for `callback(...)` pattern |
| datetime (stdlib) | - | Date window filtering | Already used throughout pipeline |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| mysql-connector-python | (existing) | DB operations | Already in project for all DB ops |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx | aiohttp (already installed) | httpx simpler API, already used in extractor.py for similar HTTP fetches |
| Manual JSONP strip | demjson3 library | Overkill -- JSONP stripping is a one-line regex, no library needed |

**Installation:**
```bash
# No new packages needed -- httpx 0.28.1 already installed
```

## Architecture Patterns

### Recommended Changes (3 files, no new files)

```
pipeline/
├── crawler.py       # ADD: crawl_json_api() function (~60 lines)
├── db.py            # MODIFY: add crawl_mode + json_api_config to SELECT/dict
├── main.py          # MODIFY: route json_api websites to HTTP path, skip browser
```

### Pattern 1: Crawl Mode Routing in main.py

**What:** Split websites into browser-mode and json_api-mode groups before crawling. JSON API websites skip the AsyncWebCrawler entirely.
**When to use:** When `website['crawl_mode'] == 'json_api'`
**Example:**
```python
# In run_pipeline(), after getting websites:
json_api_websites = [w for w in websites if w.get('crawl_mode') == 'json_api']
browser_websites = [w for w in websites if w.get('crawl_mode', 'browser') == 'browser']

# Crawl JSON API websites first (fast, no browser needed)
for website in json_api_websites:
    conn = db.create_connection()
    cur = conn.cursor(buffered=True)
    result_id = await crawler.crawl_json_api(website, cur, conn, crawl_run_id)
    if result_id:
        crawl_results.append((result_id, website))
    cur.close()
    conn.close()

# Then crawl browser websites as before (existing code unchanged)
```

### Pattern 2: JSONP Stripping

**What:** Remove JSONP callback wrapper to get pure JSON.
**When to use:** When `json_api_config.jsonp_callback` is set.
**Example:**
```python
import re

def strip_jsonp(text, callback_name=None):
    """Strip JSONP callback wrapper. Returns pure JSON string."""
    if callback_name:
        # Known callback: strip exactly that
        prefix = callback_name + '('
        if text.startswith(prefix) and text.rstrip().endswith(')'):
            return text[len(prefix):-1].rstrip().rstrip(')')
    # Generic: strip any function call wrapper
    match = re.match(r'^[a-zA-Z_]\w*\s*\((.*)\)\s*;?\s*$', text, re.DOTALL)
    if match:
        return match.group(1)
    return text  # Already plain JSON
```

### Pattern 3: Date Window Filtering

**What:** Filter events by `proxima_fecha` to only include events within a configurable window (e.g., next 30 days).
**When to use:** Always for JSON API crawls to reduce token cost.
**Example:**
```python
from datetime import datetime, timedelta

def filter_by_date_window(events_dict, days_ahead=30):
    """Filter events dict to only those with upcoming dates within window."""
    cutoff = datetime.now() + timedelta(days=days_ahead)
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    filtered = {}
    for event_id, event in events_dict.items():
        for lugar_id, lugar in event.get('lugares', {}).items():
            for func_id, funcion in lugar.get('funciones', {}).items():
                proxima = funcion.get('proxima_fecha', '')
                if proxima:
                    try:
                        dt = datetime.strptime(proxima, '%Y-%m-%d %H:%M')
                        if today <= dt <= cutoff:
                            filtered[event_id] = event
                            break
                    except ValueError:
                        continue
            if event_id in filtered:
                break
    return filtered
```

### Pattern 4: JSON-to-Markdown Flattening

**What:** Convert filtered JSON events to markdown that Gemini can extract from, matching the format browser-crawled content produces.
**When to use:** After filtering and field selection, before storing as `crawled_content`.
**Example:**
```python
def flatten_events_to_markdown(events_dict, fields_include=None):
    """Convert JSON events to markdown for Gemini extraction."""
    lines = []
    for event_id, event in events_dict.items():
        lines.append(f"## {event.get('titulo', 'Sin titulo')}")

        # Tags from clasificaciones
        tags = [c['descripcion'] for c in event.get('clasificaciones', {}).values()]
        if tags:
            lines.append(f"**Tags:** {', '.join(tags)}")

        # Venues and showtimes
        for lugar_id, lugar in event.get('lugares', {}).items():
            lines.append(f"**Venue:** {lugar.get('nombre', '')}")
            lines.append(f"**Address:** {lugar.get('direccion', '')}, {lugar.get('zona', '')}")

            # Showtimes
            for func_id, funcion in lugar.get('funciones', {}).items():
                day = funcion.get('dia', '')
                hora = funcion.get('hora', '')
                proxima = funcion.get('proxima_fecha', '')
                lines.append(f"- {day} {hora} (next: {proxima})")

        # URL
        url_slug = event.get('url', '')
        if url_slug:
            lines.append(f"**URL:** https://www.alternativateatral.com/{url_slug}")

        # Ticket URL
        url_entradas = event.get('url_entradas', '')
        if url_entradas:
            lines.append(f"**Tickets:** {url_entradas}")

        lines.append("")  # blank line between events

    return "\n".join(lines)
```

### Pattern 5: json_api_config Schema

**What:** Per-source JSON configuration stored in the `websites.json_api_config` column.
**Structure:**
```json
{
    "jsonp_callback": "jsoncallback",
    "data_path": "espectaculos",
    "fields_include": ["titulo", "clasificaciones", "lugares", "url", "url_entradas"],
    "date_field_path": "lugares.*.funciones.*.proxima_fecha",
    "date_window_days": 30,
    "base_url": "https://www.alternativateatral.com/get-json.php?t=novedades&r=cartelera",
    "encoding": "utf-8"
}
```

### Anti-Patterns to Avoid
- **Creating a new file for JSON API crawling:** Keep it in `crawler.py` as a single function. The existing file already handles crawling; this is just a new crawl method.
- **Building a generic JSON-to-event converter:** The JSON-to-markdown step replaces the browser, not the AI. Gemini still does the actual event extraction. Don't try to map JSON fields directly to the event schema.
- **Parallelizing JSON API crawls:** With only one JSON API source (Alternativa Teatral), parallelization adds complexity for zero benefit. A simple sequential loop is fine.
- **Over-abstracting json_api_config:** The config schema should be simple and flat. Don't build a DSL for JSON path navigation -- `data_path` as a simple dot-notation key (e.g., "espectaculos") is sufficient.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP requests | Custom urllib/socket code | httpx (already installed) | Handles encoding, redirects, timeouts, async |
| JSONP parsing | Full JavaScript parser | Simple regex strip | JSONP is always `callback(json)` -- regex is sufficient |
| Date parsing | Custom date parser | datetime.strptime | Standard format `YYYY-MM-DD HH:MM` from the API |
| JSON path navigation | JSONPath library | Simple dict key access | `data["espectaculos"]` is one level deep, no need for a library |

**Key insight:** This is a simple HTTP GET + JSON parse + filter + format pipeline. Every component is a standard library operation. The temptation to over-engineer (JSON path DSL, pluggable transformers, abstract crawl strategies) adds complexity without value for what is essentially one API endpoint.

## Common Pitfalls

### Pitfall 1: JSONP Response with BOM or Encoding Issues
**What goes wrong:** JSONP response may have UTF-8 BOM or use Latin-1 encoding for Spanish characters (accents, n-tilde).
**Why it happens:** PHP endpoints sometimes emit different encodings.
**How to avoid:** Use `response.text` (httpx handles encoding detection) rather than `response.content.decode()`. If specific encoding is needed, store it in `json_api_config.encoding`.
**Warning signs:** Garbled Spanish characters (mojibake) in venue names or titles.

### Pitfall 2: Assuming proxima_fecha Always Exists
**What goes wrong:** Some events may have empty `funciones` or missing `proxima_fecha`, causing KeyError or silent data loss.
**Why it happens:** Events that are "coming soon" or have irregular scheduling may lack concrete dates.
**How to avoid:** Always use `.get()` with defaults. Include events with no date in output (Gemini can still extract them).
**Warning signs:** Filtered event count is much lower than expected.

### Pitfall 3: Storing JSON API URL in website_urls Table
**What goes wrong:** The JSON API endpoint URL is different from the website's crawlable page URL. Storing it in `website_urls` would cause the browser crawler to try to render a JSON endpoint.
**How to avoid:** Store the JSON API URL in `json_api_config.base_url` (or as a field in the JSON config), NOT in the `website_urls` table. The `website_urls` table should keep the HTML page URL for fallback browser crawling.
**Warning signs:** Browser crawler returning raw JSON/JSONP text as "crawled content."

### Pitfall 4: Markdown Too Large for Gemini Token Limits
**What goes wrong:** Even after filtering, 200-300 events at ~200 chars each = ~50KB of markdown, which may still be large for Gemini extraction.
**Why it happens:** The existing extractor has batching logic (`max_batches`) but the crawled content is stored as one blob.
**How to avoid:** The existing extractor already handles large content via batching. Ensure `max_batches` is set appropriately for Alternativa Teatral. The 3-layer token reduction (field selection, date filtering, markdown flattening) should bring it well within limits.
**Warning signs:** Gemini extraction timing out or returning truncated results.

### Pitfall 5: Not Updating schema.sql with New Columns
**What goes wrong:** The roadmap says columns are "already migrated locally" but `schema.sql` doesn't have them. Future setups will be missing the columns.
**Why it happens:** Manual ALTER TABLE without updating the schema file.
**How to avoid:** Add `crawl_mode` and `json_api_config` columns to the `websites` CREATE TABLE in `schema.sql`.
**Warning signs:** Pipeline fails on fresh database setup.

## Code Examples

### Complete crawl_json_api() Function Structure
```python
# Source: codebase analysis + Alternativa Teatral API inspection
async def crawl_json_api(website, cursor, connection, crawl_run_id):
    """Crawl a website via JSON API instead of browser.

    Uses json_api_config from the website record for:
    - JSONP callback stripping
    - Data path navigation
    - Field selection
    - Date window filtering
    """
    name = website['name']
    config = website.get('json_api_config', {})

    if not config:
        print(f"  Skipping {name}: no json_api_config")
        return None

    safe_filename = create_safe_filename(name, '.md')
    crawl_result_id = db.create_crawl_result(
        cursor, connection, crawl_run_id, website['id'], safe_filename
    )

    try:
        # 1. HTTP GET
        api_url = config.get('base_url') or website['urls'][0]['url']
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(api_url)
            response.raise_for_status()

        text = response.text

        # 2. Strip JSONP wrapper
        callback = config.get('jsonp_callback')
        if callback:
            text = strip_jsonp(text, callback)

        # 3. Parse JSON
        data = json.loads(text)

        # 4. Navigate data_path
        data_path = config.get('data_path')
        if data_path:
            for key in data_path.split('.'):
                data = data[key]

        # 5. Filter by date window
        days = config.get('date_window_days', 30)
        data = filter_by_date_window(data, days)

        # 6. Select fields + flatten to markdown
        fields = config.get('fields_include')
        markdown = flatten_events_to_markdown(data, fields)

        # 7. Store as crawled_content (same as browser path)
        if not markdown.strip():
            db.update_crawl_result_failed(cursor, connection, crawl_result_id, "No events after filtering")
            db.update_website_last_crawled(cursor, connection, website['id'])
            return None

        db.update_crawl_result_crawled(cursor, connection, crawl_result_id, markdown)
        db.update_website_last_crawled(cursor, connection, website['id'])
        print(f"  - {name}: {len(data)} events, {len(markdown)} chars markdown")
        return crawl_result_id

    except Exception as e:
        db.update_crawl_result_failed(cursor, connection, crawl_result_id, str(e))
        db.update_website_last_crawled(cursor, connection, website['id'])
        return None
```

### db.py Changes
```python
# Add to SELECT in get_websites_due_for_crawling():
#   w.crawl_mode, w.json_api_config
# Add to dict construction:
#   'crawl_mode': row[N],  # 'browser' or 'json_api'
#   'json_api_config': json.loads(row[N+1]) if row[N+1] else {},
```

### Schema Migration
```sql
ALTER TABLE websites
    ADD COLUMN crawl_mode ENUM('browser', 'json_api') DEFAULT 'browser'
        COMMENT 'How to crawl: browser (Crawl4AI) or json_api (HTTP GET)'
        AFTER process_images,
    ADD COLUMN json_api_config JSON DEFAULT NULL
        COMMENT 'Config for json_api mode: jsonp_callback, data_path, fields_include, date_window_days'
        AFTER crawl_mode;
```

### Alternativa Teatral Website Update
```sql
UPDATE websites
SET crawl_mode = 'json_api',
    json_api_config = JSON_OBJECT(
        'jsonp_callback', 'jsoncallback',
        'data_path', 'espectaculos',
        'fields_include', JSON_ARRAY('titulo', 'clasificaciones', 'lugares', 'url', 'url_entradas'),
        'date_window_days', 30,
        'base_url', 'https://www.alternativateatral.com/get-json.php?t=novedades&r=cartelera'
    )
WHERE name = 'Alternativa Teatral';
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Browser crawl + JS execution for all sites | HTTP GET for structured APIs | This phase | Faster, cheaper, more reliable for API-based sources |
| Full 920-event payload to Gemini | 3-layer filtering (fields, dates, flatten) | This phase | ~70-80% token reduction |

**Deprecated/outdated:**
- None. This is additive -- browser crawling remains the default for all other sites.

## Alternativa Teatral API Specifics

Verified via direct WebFetch (HIGH confidence):

- **Endpoint:** `https://www.alternativateatral.com/get-json.php?t=novedades&r=cartelera`
- **JSONP callback:** `jsoncallback`
- **Top-level structure:** `{ espectaculos: { "869": {...}, "4346": {...}, ... } }`
- **Event ID:** String key in `espectaculos` object (e.g., "869")
- **Date format:** `proxima_fecha` uses `YYYY-MM-DD HH:MM` format
- **URL pattern:** Slug format like `obra869-venimos-de-muy-lejos`, full URL = `https://www.alternativateatral.com/{slug}`
- **Venue structure:** Nested `lugares` > venue ID > `funciones` > function ID > date/time
- **Tags:** `clasificaciones` is an object with numeric IDs mapping to `{ padre, descripcion }`
- **Total events:** ~920 (as of March 2026)
- **Response size:** ~732KB

## Open Questions

1. **What is the actual `data_path` key in the JSONP response?**
   - What we know: The response contains `espectaculos` as a top-level key with event data
   - What's unclear: Whether there are other top-level keys we might want (e.g., metadata, pagination info)
   - Recommendation: Use `espectaculos` as `data_path`. Inspect full response during implementation to confirm.

2. **Should events without `proxima_fecha` be included or excluded?**
   - What we know: Some events may have venues but no scheduled functions yet
   - What's unclear: Whether these are useful or noise
   - Recommendation: Include them -- Gemini can decide if they're relevant. Better to over-include than silently lose events.

3. **Is the `crawl_mode` column already in the local DB?**
   - What we know: Roadmap says "already migrated locally" but schema.sql doesn't have it
   - What's unclear: Whether this was an ALTER TABLE that wasn't reflected in schema.sql
   - Recommendation: Plan should include both ALTER TABLE migration AND schema.sql update. If column exists, ALTER will be a no-op.

## Sources

### Primary (HIGH confidence)
- Alternativa Teatral JSONP endpoint (direct WebFetch) -- verified response structure, callback name, field names, date format
- Codebase analysis: `crawler.py`, `db.py`, `main.py`, `extractor.py` -- verified existing patterns, dependencies, architecture
- `database/schema.sql` -- verified current table structure (no crawl_mode/json_api_config columns)
- `pip list` from venv -- verified httpx 0.28.1 already installed

### Secondary (MEDIUM confidence)
- Roadmap context about "already migrated locally" -- from project documentation, not verified against live DB

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already in project, verified via pip list
- Architecture: HIGH - based on direct codebase analysis of existing patterns
- API structure: HIGH - verified via direct WebFetch of the endpoint
- Pitfalls: MEDIUM - based on experience with similar JSONP/encoding scenarios

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable -- API endpoint unlikely to change rapidly)
