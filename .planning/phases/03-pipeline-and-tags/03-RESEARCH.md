# Phase 3: Pipeline & Tags - Research

**Researched:** 2026-03-05
**Domain:** Python data pipeline (crawl4ai + Gemini AI extraction), tag taxonomy, frontend tag system
**Confidence:** HIGH

## Summary

Phase 3 adapts the existing NYC event pipeline to crawl Argentine event sources and extract Spanish-language events, then updates the tag taxonomy for the BA art scene. The pipeline architecture is already fully built (crawl -> extract -> process -> merge -> export -> upload) and only needs configuration-level changes: new website entries in the `websites` table, adapted Gemini prompts for Spanish, and updated location matching for BA venues.

The tag system has two independent parts: (1) pipeline-side tag processing (tag_rules table for rewrite/exclude/remove, CamelCase hashtag extraction from Gemini, website_tags for extra tags) and (2) frontend tag display (tags.json for geotags/bgcolors, related_tags.json for tag relationships, tag cloud built dynamically from event data). Both need BA-specific content.

**Primary recommendation:** This is a configuration phase, not a code-change phase. The main work is: inserting website rows with Argentine source URLs, updating hardcoded "NYC" strings in prompts, populating tag_rules for BA categories, and creating new tags.json/related_tags.json content.

## Standard Stack

No new libraries needed. The existing stack handles everything:

### Core (already installed)
| Library | Purpose | Relevance to Phase 3 |
|---------|---------|---------------------|
| crawl4ai | Web crawling with JS rendering | Crawls Argentine event sites -- no changes needed |
| google-genai | Gemini AI extraction | Prompts need Spanish adaptation |
| mysql-connector-python | Database operations | No changes |
| pydantic | Structured output schemas | Schemas work for Spanish content as-is |

### No New Dependencies
The pipeline already handles UTF-8/unicode content (database is utf8mb4, JSON export uses `ensure_ascii=False`). Spanish characters (accents, tildes) will flow through without issues.

## Architecture Patterns

### What Exists (No Changes Needed)
```
pipeline/
  main.py          -- Orchestrator (no changes)
  crawler.py       -- Crawl4AI wrapper (no changes)
  extractor.py     -- Gemini extraction (prompt changes only)
  processor.py     -- Event processing (location matching changes)
  merger.py        -- Deduplication (no changes)
  exporter.py      -- JSON export (already uses BA bounding box)
  db.py            -- Database layer (no changes)
```

### Pattern 1: Website Configuration via Database
**What:** Each event source is a row in the `websites` table with URLs in `website_urls`. No code changes needed to add new sources.
**How it works:**
- `websites` row: name, crawl_frequency, notes (prompt hints), selector, js_code, keywords, etc.
- `website_urls` rows: one per URL to crawl for that website
- `website_tags` rows: extra tags auto-applied to all events from this source
- `website_locations` rows: link website to its venue location
**Phase 3 action:** INSERT rows for Argentine event sources.

### Pattern 2: Gemini Prompt Structure
**What:** The extractor uses two prompt templates that reference "NYC" explicitly.
**Where:**
- `extractor.py:get_prompt()` (line 734): `"upcoming events in New York City"` and `"Only include events in the NYC area"`
- `extractor.py:extract_chunk()` (line 604): `"Extract ALL events from this NYC events page"`
**Phase 3 action:** Replace NYC references with Buenos Aires.

### Pattern 3: Tag Processing Pipeline
**What:** Tags flow through: Gemini extracts CamelCase hashtags -> processor.py `process_tags()` applies rewrite/exclude rules from `tag_rules` table -> merger.py inserts into `tags` and `event_tags` tables -> exporter.py includes in JSON output -> frontend builds tag cloud from event data.
**Phase 3 action:** Populate `tag_rules` table with BA-relevant rewrites and exclusions.

### Pattern 4: Frontend Tag Configuration
**What:** Two static JSON files define tag behavior:
- `tags.json`: Contains `geotags` array (barrio names, used to filter out location-based tags from tag cloud display) and `bgcolors` map (emoji -> hex color for marker rendering)
- `related_tags.json`: Maps tag -> array of `[relatedTag, weight]` tuples for implicit tag selection
**Phase 3 action:** tags.json geotags already updated to BA barrios (Phase 1). related_tags.json is currently `{}` (empty). Need to populate it with BA cultural category relationships.

### Pattern 5: Location Matching in Processor
**What:** `processor.py` matches extracted location names to database locations using multi-tier matching (exact -> alternate names -> short names -> address -> prefix -> fuzzy -> site fallback). Currently has NYC-specific normalization in `_normalize_location_name()` that strips borough names.
**Where:** Lines 428-450 of processor.py -- normalizes by removing "queens", "bronx", "brooklyn", "manhattan", "staten island" suffixes.
**Phase 3 action:** Either remove NYC borough stripping or replace with BA barrio handling. Since Phase 2 already populated 40 BA venues with alternate names, the matching should work -- but the NYC-specific normalization should be cleaned up.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Website configuration | Custom config files | `websites` + `website_urls` database tables | Already built, supports per-site crawl settings |
| Tag normalization | Custom processing | `tag_rules` table (rewrite/exclude/remove) | Already built, data-driven, no code changes |
| Extra per-source tags | Hardcoded tag assignment | `website_tags` table | Already built, links tags to websites |
| Related tags | Code-level tag relationships | `related_tags.json` data file | Frontend already consumes it |
| Spanish language detection | Language detection library | Gemini handles it natively | Gemini understands Spanish -- just tell it in the prompt |

## Common Pitfalls

### Pitfall 1: Hardcoded NYC References in Prompts
**What goes wrong:** Gemini prompt says "New York City" -- it will try to filter for NYC events or generate NYC-relevant tags.
**Why it happens:** Prompts were written for NYC and have city-specific instructions.
**How to avoid:** Search for ALL occurrences of "NYC", "New York", "New York City" in extractor.py and replace with Buenos Aires equivalents.
**Specific locations:**
- `get_prompt()` line 734: "upcoming events in New York City"
- `get_prompt()` line 755: "Only include events in the NYC area"
- `get_prompt()` line 747: "Avoid location-specific or NYC-redundant tags"
- `extract_chunk()` line 604: "this NYC events page"

### Pitfall 2: NYC Borough Stripping in Location Matching
**What goes wrong:** `_normalize_location_name()` strips NYC borough names, which is irrelevant for BA and could interfere with BA location names.
**Why it happens:** Hardcoded list of NYC boroughs used for normalization.
**How to avoid:** Update the suffix list to remove NYC boroughs. Consider whether BA barrio names need similar treatment (probably not -- barrios aren't commonly appended to venue names the way NYC boroughs are).
**Warning signs:** Location matching failures in processor output.

### Pitfall 3: Tag Exclusion Rules Still NYC-Focused
**What goes wrong:** The `tag_rules` table may contain NYC-specific rewrite/exclude rules that interfere with BA tags.
**Why it happens:** Rules were designed for NYC event sources.
**How to avoid:** Review existing tag_rules and remove NYC-specific ones. Add BA-relevant rules (e.g., rewrite "Tango" variations to a canonical form).

### Pitfall 4: Tags in English vs. Spanish
**What goes wrong:** Gemini may extract tags in Spanish ("Musica", "Danza") when the requirement says tags should be in English.
**Why it happens:** Source content is in Spanish; Gemini may follow the source language for tag extraction.
**How to avoid:** Explicitly instruct in the prompt: "Generate tags in English." Also add tag_rules rewrites for common Spanish->English mappings (e.g., "musica" -> "Music").

### Pitfall 5: Related Tags JSON Format
**What goes wrong:** Frontend expects specific format -- `{"TagName": [["RelatedTag", 0.8], ...]}` -- deviating breaks implicit tag selection.
**Why it happens:** Manually editing related_tags.json can introduce errors.
**How to avoid:** Use the exact format the `RelatedTagsManager.loadRelatedTags()` expects: JSON object where keys are tag names and values are arrays of `[tagName, weight]` tuples.

### Pitfall 6: Date Format in Spanish Sources
**What goes wrong:** Argentine sites use DD/MM/YYYY or Spanish month names -- Gemini may misparse dates.
**Why it happens:** Spanish date formats differ from English (e.g., "5 de marzo de 2026").
**How to avoid:** Add a note in the prompt about Argentine date formats: "Dates on Argentine sites use DD/MM/YYYY format and Spanish month names." The Pydantic schema enforces YYYY-MM-DD output which Gemini will convert to.

### Pitfall 7: Process Tags NYC Removal
**What goes wrong:** `process_tags()` in processor.py (lines 220-221) strips "NYC" prefix/suffix from tags. This is harmless for BA but should be reviewed.
**How to avoid:** Either leave it (no-op for BA content) or remove it for cleanliness.

## Code Examples

### Website Insert Pattern (SQL)
```sql
-- Add an Argentine event source
INSERT INTO websites (name, description, base_url, crawl_frequency, notes)
VALUES (
  'Centro Cultural Kirchner',
  'Government cultural center events',
  'https://cck.gob.ar',
  3,
  'Extract events from the agenda/programacion page. Events are in Spanish.'
);

-- Add URL(s) to crawl
INSERT INTO website_urls (website_id, url, sort_order)
VALUES (LAST_INSERT_ID(), 'https://cck.gob.ar/agenda/', 0);

-- Link to location (if venue exists)
INSERT INTO website_locations (website_id, location_id)
VALUES (@website_id, @location_id);

-- Add extra tags for all events from this source
INSERT INTO website_tags (website_id, tag)
VALUES (@website_id, 'Cultural Center');
```

### Prompt Adaptation (Python)
```python
# Current (NYC):
f'''Today's date is {current_date_string}. We are assembling a database of upcoming events in New York City.'''

# Updated (BA):
f'''Today's date is {current_date_string}. We are assembling a database of upcoming events in Buenos Aires, Argentina.'''

# Tag instruction addition:
'''- hashtags: 4-7 CamelCase tags in ENGLISH (e.g., ["Theater", "Dance", "Contemporary", "FreeEntry"]).
  Even though the source content is in Spanish, tags must be in English.'''
```

### Related Tags JSON Format
```json
{
  "Theater": [["Performing Arts", 0.8], ["Drama", 0.7], ["Comedy", 0.6]],
  "Dance": [["Performing Arts", 0.8], ["Tango", 0.7], ["Contemporary Dance", 0.6]],
  "Tango": [["Dance", 0.8], ["Music", 0.6], ["Live Performance", 0.5]],
  "Gallery": [["Art", 0.8], ["Exhibition", 0.7], ["Contemporary Art", 0.6]],
  "Street Art": [["Art", 0.7], ["Mural", 0.6], ["Urban Art", 0.5]],
  "Music": [["Live Performance", 0.7], ["Concert", 0.6]]
}
```

### Tag Rules for BA (SQL)
```sql
-- Rewrite Spanish tags to English
INSERT INTO tag_rules (rule_type, pattern, replacement) VALUES
  ('rewrite', 'musica', 'Music'),
  ('rewrite', 'danza', 'Dance'),
  ('rewrite', 'teatro', 'Theater'),
  ('rewrite', 'arte', 'Art'),
  ('rewrite', 'exposicion', 'Exhibition'),
  ('rewrite', 'concierto', 'Concert'),
  ('rewrite', 'espectaculo', 'Show'),
  ('rewrite', 'gratis', 'Free Entry'),
  ('rewrite', 'entrada libre', 'Free Entry'),
  ('rewrite', 'entradalibre', 'Free Entry');

-- Exclude redundant BA tags
INSERT INTO tag_rules (rule_type, pattern) VALUES
  ('exclude', 'buenosaires'),
  ('exclude', 'argentina'),
  ('exclude', 'caba'),
  ('exclude', 'ba');
```

## State of the Art

| Old Approach (NYC) | Current Need (BA) | Impact |
|---|---|---|
| English prompts, English content | Spanish content, English tags | Prompt adaptation needed |
| NYC borough location stripping | BA has barrios, not boroughs | Normalization cleanup |
| `related_tags.json` was populated for NYC, now empty `{}` | Need BA cultural category relationships | Must populate |
| `tags.json` geotags had NYC neighborhoods | Already updated to BA barrios (Phase 1) | Done |
| Exporter used NYC bounding box for init set | Already updated to BA (Phase 1) | Done |

## Key Findings for Planning

### Plan 03-01: Pipeline Configuration and Spanish Extraction

**Scope of changes:**
1. **Prompt changes in extractor.py** (4 locations with "NYC"/"New York" references) -- replace with BA
2. **Location normalization in processor.py** -- remove NYC borough list, optionally add BA barrio handling
3. **NYC tag stripping in processor.py** -- remove or leave (harmless no-op)
4. **Website database inserts** -- SQL seed files for Argentine event sources
5. **Tag rules** -- SQL seed for Spanish->English rewrites and BA-specific exclusions
6. **Website notes** -- Each website entry should have notes guiding Gemini (e.g., "Events are in Spanish, dates use DD/MM format")

**What does NOT change:**
- crawler.py (already handles any URL)
- merger.py (deduplication is location-agnostic)
- exporter.py (already configured for BA bounding box)
- main.py (orchestration unchanged)
- db.py (all queries are city-agnostic)
- Pydantic schemas (language-agnostic)
- Frontend JS (consumes JSON, doesn't care about city)

### Plan 03-02: BA Tag Taxonomy and Related Tags

**Scope of changes:**
1. **related_tags.json** -- Populate with BA art scene category relationships
2. **tags.json bgcolors** -- Add emoji->color mappings for any new emojis used by BA venues/events (existing map already has extensive coverage)
3. **Verify tag filtering/search** -- No code changes expected; tags flow from events data through the existing frontend system

**BA Art Scene Categories (TAG-01):**
Based on the project description ("galleries, theater, dance, music, street art, pop-ups, underground events"), the core tag taxonomy should include:
- Art, Gallery, Exhibition, Contemporary Art, Street Art, Mural
- Theater, Dance, Tango, Music, Concert, Live Performance
- Film, Cinema, Photography
- Literature, Poetry, Book
- Comedy, Circus
- Festival, Market, Fair
- Free Entry, Outdoor
- Workshop, Talk, Lecture

**Related Tags Connections (TAG-02):**
Key relationships for BA cultural scene:
- Tango <-> Dance, Music, Live Performance (Tango is uniquely BA)
- Theater <-> Performing Arts, Drama, Comedy
- Gallery <-> Art, Exhibition, Contemporary Art
- Street Art <-> Art, Mural, Urban Art
- Music <-> Concert, Live Performance, DJ

## Open Questions

1. **Which Argentine event sources to crawl?**
   - The user "has Buenos Aires event sources identified and ready to configure" (from PROJECT.md)
   - The planner should note that source URLs need to come from the user
   - Recommendation: Create the seed file structure, leave URL values as placeholders, or plan to get them from the user

2. **How many tag_rules exist currently?**
   - We can't query the live database to see existing NYC tag_rules
   - Recommendation: The plan should include reviewing/clearing existing rules before adding BA ones

3. **Should the prompt language be Spanish or English?**
   - Gemini can be prompted in English even for Spanish content
   - Recommendation: Keep prompts in English with explicit instruction about Spanish source content and English tag output

## Sources

### Primary (HIGH confidence)
- Codebase analysis of all pipeline Python files (crawler.py, extractor.py, processor.py, merger.py, exporter.py, db.py, main.py)
- Database schema.sql -- full schema review
- Frontend JS tag system (tagStateManager.js, tagColorManager.js, relatedTagsManager.js, filterPanelUI.js, dataManager.js)
- Static data files (tags.json, related_tags.json)
- Phase 1 and 2 completed work (ROADMAP.md, STATE.md)

### Secondary (MEDIUM confidence)
- BA art scene category list (based on PROJECT.md description + general knowledge of Buenos Aires cultural scene)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- existing codebase, no new libraries
- Architecture: HIGH -- patterns fully visible in code, changes are configuration-level
- Pitfalls: HIGH -- identified by reading actual code, specific line numbers referenced
- Tag taxonomy: MEDIUM -- BA cultural categories based on project description + general knowledge, user may want adjustments

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable -- existing codebase, no external dependencies changing)
