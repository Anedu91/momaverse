---
description: Agentic workflow for adding a new scraping source to Momaverse — scrapes the target URL, analyzes page structure, drafts a crawl config, simulates event extraction, and saves the source via the API after user confirmation.
---

You are executing a multi-step agentic workflow to add a new event-scraping source to the Momaverse database. Follow each step in order. Do not skip steps or reorder them.

The argument after `/add-source` is the URL to add.

---

## Step 1 — Read credentials

Read the `.env` file in the project root. Extract these two values:

- `MOMAVERSE_API_URL` — the base API URL (e.g., `https://api.example.com`)
- `MOMAVERSE_API_TOKEN` — the Bearer token for authentication

Do not use fallback values. If either value is missing from `.env`, stop and ask the user to provide them.

---

## Step 2 — Scrape and analyze the target URL

### 2a — Initial scrape

Use `firecrawl_scrape` on the target URL. Retrieve the full page content (HTML + markdown).

### 2b — Map linked pages

Use `firecrawl_map` on the target URL to discover linked pages and sitemap structure.

### 2c — Analyze page structure

Based on the scrape results, determine:

**Rendering type:**
- Is this a **SPA** (Single Page Application)? Signs: minimal HTML, JavaScript-heavy, React/Vue/Angular indicators, content only visible after JS runs.
- Is this **static HTML**? Signs: full event content in raw HTML, no JS framework indicators.

**Pagination patterns:**
- Are there "next page" links, numbered pagination, or infinite scroll?
- Are there URL patterns like `?page=2`, `/page/2`, or `?offset=20`?
- Estimate total pages if pagination is detected.

**Hidden JSON APIs:**
- Are there XHR/fetch API endpoints visible in the page source (e.g., `/api/events`, `/wp-json/`, GraphQL endpoints)?
- If JSON API endpoints are found, note their URL patterns and response structure.

**Content selectors:**
- What CSS selectors target the event listing container? (e.g., `.events-list`, `#calendar`, `article.event`)
- What selectors target individual event items?

**Bot protection:**
- Does the site use Cloudflare, CAPTCHA, rate limiting, or other bot-protection mechanisms?

---

## Step 3 — Draft crawl config

Based on the analysis, build the JSON payloads.

### CrawlConfigCreate fields

Required:
- `crawl_frequency`: integer number of days between crawls (suggest 1 for daily events, 3 for weekly, 7 for monthly calendars)
- `crawl_mode`: one of `"browser"` | `"json_api"`
  - Use `"browser"` for HTML pages (static or SPA)
  - Use `"json_api"` for sites where event data comes from a JSON API endpoint

Optional (include only when needed):
- `selector`: CSS selector string targeting the event listing container (max 500 chars). Use when the page has noise around the events section.
- `js_code`: JavaScript to execute before scraping (for SPAs that require interaction like clicking "load more" or dismissing modals)
- `json_api_config`: dict with API endpoint details — include when `crawl_mode` is `"json_api"`
- `max_pages`: integer, default 30. Lower for sites with few events; raise for large calendars.
- `max_batches`: integer, optional. Cap on scrape batches.
- `delay_before_return_html`: integer milliseconds to wait for JS to render (use for slow SPAs, e.g., 2000–5000)
- `use_stealth`: boolean, set to `true` for bot-protected sites
- `notes`: string, any special instructions for the extractor about this source
- `default_tags`: list of strings, tags to always apply to events from this source
- `keywords`: string (max 255 chars), comma-separated keywords to filter content
- `scan_full_page`: boolean
- `remove_overlay_elements`: boolean, useful when cookie banners or modals obscure content
- `javascript_enabled`: boolean
- `scroll_delay`: float, seconds between scroll steps for infinite scroll pages
- `crawl_timeout`: integer seconds

### SourceCreate fields

- `name`: string (max 255 chars). Derive from the page `<title>` tag or organization name visible on the page. Keep it concise and human-readable.
- `type`: one of `"crawler"` | `"api"` | `"user_submission"` | `"partner_feed"`
  - Use `"crawler"` for web scraping
  - Use `"api"` when consuming a public or partner JSON API
  - Use `"partner_feed"` for official data feeds
  - Use `"user_submission"` for community-submitted sources
- `urls`: array of `SourceUrlCreate` objects, each with:
  - `url`: string (max 2000 chars) — the URL to crawl
  - `js_code`: optional per-URL JavaScript override
  - `sort_order`: integer, default 0
- `crawl_config`: the `CrawlConfigCreate` object above

### Example payload structure

```json
{
  "name": "Example Events Calendar",
  "type": "crawler",
  "urls": [
    {
      "url": "https://example.com/events",
      "sort_order": 0
    }
  ],
  "crawl_config": {
    "crawl_frequency": 3,
    "crawl_mode": "browser",
    "selector": ".events-container",
    "max_pages": 5,
    "delay_before_return_html": 2000
  }
}
```

---

## Step 4 — Simulate event extraction

Using the scraped page content from Step 2a, simulate what the extractor would produce by running the extraction prompt against the content.

Fill in this extraction template and evaluate it yourself:

```
Today's date is {current_date_string}. We are assembling a database of upcoming events in Buenos Aires, Argentina. Currently, we are inspecting {name} ({url}).

Based on the website content below, extract all upcoming events. For each event, provide:
- name: The event name
- location: The venue name
- sublocation: Optional location within the venue (rooftop, 5th floor, etc.)
- occurrences: An array of date/time objects. IMPORTANT: For recurring events (e.g., "every Wednesday" or "Jan 11, 18, 25"), list EACH specific date as a separate occurrence within the next 3 months. Each occurrence has:
  - start_date: Date in YYYY-MM-DD format
  - start_time: Time like "4:00 PM" (optional)
  - end_date: End date if different from start (optional)
  - end_time: End time (optional)
- description: 1-3 sentence description. MUST be written in Spanish.
- url: Specific event URL if available
- hashtags: 4-7 CamelCase tags in Spanish (e.g., ["Comedia", "Música", "Teatro", "Tango"]). Include a mix of high-level and granular tags. Avoid location-specific or Buenos Aires-redundant tags.
- emoji: A single emoji representing the event

Rules:
- Extract ALL events from the page - do not skip or summarize
- Only include events in the Buenos Aires area within the next 3 months
- Dates on Argentine sites often use DD/MM/YYYY format and Spanish month names.
- Ignore unrelated event sections ("Hot Events", "Similar events", etc.)
- For recurring events, expand ALL individual dates into the occurrences array
- If no events are found, return an empty events list

Website content:

{page_content}
```

Produce a **sample events table** showing the first 5–10 events you would extract:

| Name | Location | Date(s) | Description (ES) | Hashtags |
|------|----------|---------|-----------------|----------|
| ... | ... | ... | ... | ... |

If the page content is insufficient to extract events (SPA not yet rendered, gated content, etc.), note this clearly.

---

## Step 5 — User confirmation (STOP)

**STOP here.** Do not proceed until the user confirms.

Present to the user:

1. **Proposed source name and type**
2. **Full SourceCreate JSON payload** (formatted, ready to POST)
3. **Sample extracted events table** from Step 4
4. **Warnings** (check all that apply):
   - SPA detected — JavaScript rendering required
   - Pagination detected — multiple pages will be crawled
   - JSON API detected — consider `crawl_mode: json_api`
   - Bot protection detected — `use_stealth` may be needed
   - No events found in scrape — content may require JS execution
   - Ambiguous source name — please confirm

Ask the user: **"Does this look correct? Reply 'yes' to proceed, 'no' to cancel, or provide edits to the config."**

If the user provides edits, update the payload and re-present the summary before proceeding.

---

## Step 6 — Duplicate check

Before creating the source, check for existing sources with the same URLs.

Make this request:
```
GET {MOMAVERSE_API_URL}/api/v1/sources/?limit=200
Authorization: Bearer {MOMAVERSE_API_TOKEN}
```

Search the response for any `urls` entries matching the target URL(s) from your payload.

- If duplicates are found: warn the user with the existing source name and ID. Ask whether to proceed anyway or cancel.
- If no duplicates: continue to Step 7.

---

## Step 7 — Create the source

Make this request:
```
POST {MOMAVERSE_API_URL}/api/v1/sources/
Authorization: Bearer {MOMAVERSE_API_TOKEN}
Content-Type: application/json

{SourceCreate JSON payload}
```

Handle responses:

- **201 Created**: success — extract and note the new source `id` from the response body
- **409 Conflict**: duplicate URL — report which URLs conflict and stop
- **422 Unprocessable Entity**: validation error — report the full error detail and stop
- **401 / 403**: auth error — report that the token may be invalid or expired and stop
- **Other errors**: report the status code and response body

---

## Step 8 — Confirm

Print a confirmation summary:

```
Source created successfully.
  ID:   {new source id}
  Name: {name}
  Type: {type}
  URLs: {urls list}
  Crawl mode: {crawl_mode}
  Crawl frequency: every {crawl_frequency} day(s)
```

---

## Edge cases

**SPA / JavaScript-rendered content:**
- Set `crawl_mode: "browser"`
- Add `delay_before_return_html` (start with 2000, increase to 5000 for slow sites)
- If content requires user interaction, add `js_code` to simulate it (e.g., clicking a "load more" button)
- Consider `remove_overlay_elements: true` if cookie banners are present

**Paginated content:**
- Set `max_pages` to cover all event pages (check how many pages exist)
- For infinite scroll, add `scroll_delay` (e.g., 1.0) and appropriate `js_code`
- For URL-parameter pagination, list key pages explicitly in `urls`

**JSON API endpoints:**
- Set `crawl_mode: "json_api"`
- Populate `json_api_config` with endpoint URL, method, headers, and any required query params
- Note: the extractor will receive the JSON response directly instead of HTML

**Bot-protected sites (Cloudflare, CAPTCHA):**
- Enable `use_stealth: true`
- Consider `crawl_mode: "browser"` with a longer `delay_before_return_html`
- Warn the user that stealth mode may not always succeed on heavily protected sites
