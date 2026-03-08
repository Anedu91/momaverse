---
status: testing
phase: 04-json-api-crawling
source: [04-01-SUMMARY.md]
started: 2026-03-05T22:30:00Z
updated: 2026-03-05T22:30:00Z
---

## Current Test

number: 1
name: JSON API Route Selection
expected: |
  Run the pipeline with Alternativa Teatral configured as crawl_mode='json_api'.
  It should be crawled via HTTP request (httpx), NOT launched in a browser.
  You should see log output indicating JSON API crawl, not browser crawl.
awaiting: user response

## Tests

### 1. JSON API Route Selection
expected: Alternativa Teatral (crawl_mode='json_api') is crawled via HTTP GET, not browser. Pipeline logs show it taking the JSON API path separately from browser-crawled sites.
result: [pending]

### 2. JSONP Unwrapping
expected: The JSONP callback wrapper from Alternativa Teatral's endpoint is stripped correctly, producing valid JSON. No parse errors in logs.
result: [pending]

### 3. Date Window Filtering
expected: Only events with upcoming dates (within configured window) or no dates are kept. Old/past-only events are filtered out, reducing the ~920 total events significantly.
result: [pending]

### 4. Markdown Output Quality
expected: JSON API crawl produces readable markdown for each event containing: title, tags/classifications, venue name, address, showtimes, event URL, and ticket link where available.
result: [pending]

### 5. Gemini Extraction Integration
expected: Markdown from JSON API crawl feeds into Gemini extraction identically to browser-crawled content. Extracted events have correct titles, venues, dates, and tags.
result: [pending]

### 6. Token Reduction
expected: The markdown sent to Gemini is significantly smaller than the raw 732KB JSONP response. Date filtering + flattening should reduce token usage substantially.
result: [pending]

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0

## Gaps

[none yet]
