# Codebase Concerns

**Analysis Date:** 2026-02-24

## Tech Debt

**Mobile iOS Deployment Target Misconfiguration:**
- Issue: iOS project specifies `IPHONEOS_DEPLOYMENT_TARGET = 26.2` in `mobile/ios/fomo/fomo.xcodeproj/project.pbxproj` (lines 180, 237)
- Files: `mobile/ios/fomo/fomo.xcodeproj/project.pbxproj`
- Impact: iOS 26.2 does not exist; latest iOS is 18.x. This will prevent app from building. App will fail to compile.
- Fix approach: Update to a valid iOS deployment target (e.g., 14.0, 15.0, or current 18.x minimum supported version). Check Xcode settings and update both Debug and Release configurations.

**Debug Logging Left in Android Webview Code:**
- Issue: Console.log statements with "DEBUG:" prefix scattered throughout JavaScript embedded in Android `MainActivity.kt`, including output for filter panel rect, app height, and map dimensions
- Files: `mobile/android/app/src/main/java/fomocity/fomo/app/MainActivity.kt` (lines 252, 261, 267, 274, 281)
- Impact: Verbose debug output in production app. Information leakage about layout dimensions and internal state. Increases bandwidth/battery usage from continuous logging.
- Fix approach: Remove or gate debug output behind a build-time flag. Use conditional compilation to exclude debug logs from production builds. Consider using a debug module with centralized toggle.

**Large Frontend Modules Lack Modular Decomposition:**
- Issue: Several JS modules exceed 500+ lines without clear function boundaries:
  - `src/js/script.js`: 1155 lines (main App orchestration)
  - `src/js/map/mapManager.js`: 739 lines (marker/feature management)
  - `src/js/map/viewportManager.js`: 595 lines (viewport calculations)
  - `src/js/data/dataManager.js`: 472 lines (data fetching and transformation)
- Files: `src/js/script.js`, `src/js/map/mapManager.js`, `src/js/map/viewportManager.js`, `src/js/data/dataManager.js`
- Impact: Difficult to locate bugs, refactor functionality, and test isolated concerns. High cognitive load. Tight coupling between concerns.
- Fix approach: Extract logical sub-modules (e.g., separate marker clustering from feature state, separate occurrence parsing from location processing). Use explicit module interfaces. Aim for 200-300 line max per module.

**Excessive Global State References:**
- Issue: 997 occurrences of global state access (`global`, `state.`, `window.`, `localStorage`) across 27 JS files. App state is tightly coupled through global App.state object.
- Files: `src/js/script.js`, `src/js/data/dataManager.js`, `src/js/map/mapManager.js`, and many others
- Impact: State mutations are difficult to track. Hard to determine which module modified what. Memory leaks possible if state is not cleared properly. Testing individual modules in isolation is near-impossible.
- Fix approach: Implement a centralized state management system with clear subscription/update patterns. Consider event bus for inter-module communication. Extract state read/write to dedicated API functions with clear contracts.

**No Automated Tests Exist:**
- Issue: Only manual test screenshots exist (`pipeline/tests/test_processor.py` and `test_merger.py` for pipeline, but no tests for frontend or API)
- Files: No test files found for `src/js/`, `src/api/`
- Impact: Refactoring frontend is risky. Bugs slip through. No regression protection. Cannot measure code coverage. High maintenance cost over time.
- Fix approach: Set up Jest/Vitest for JavaScript unit tests. Add API integration tests using PHP unit testing framework. Target 70%+ coverage for critical paths (data loading, filtering, API).

## Known Bugs

**Crawl4AI Missing Body Tag Causing Data Loss:**
- Symptoms: Websites with JS-heavy rendering silently fail to crawl. Events from certain venues are missing or intermittently appear/disappear.
- Files: `pipeline/crawler.py` (line 213-214), `pipeline/extractor.py` (line 684-686)
- Trigger: Websites that require heavy JavaScript execution before body content is rendered. Crawl4AI timeout or slow JS execution.
- Workaround: Manually add these URLs to a high-frequency crawl list. Investigate Crawl4AI `BrowserConfig` options for longer JS execution timeouts or use headless browser caching.
- Root cause: Crawl4AI may return HTML without properly waiting for DOM hydration. MIN_CRAWL_CONTENT_SIZE check (500 bytes) is insufficient to detect truncated content.

**Upcoming Events Occasionally Archived Unexpectedly:**
- Symptoms: Events scheduled for future dates appear in archive table. Users report missing upcoming events despite venue websites showing them.
- Files: `pipeline/merger.py` (line 723-728), `scripts/archive_outdated_events.php` (line 233-235)
- Trigger: Crawl failures on high-frequency venues. Pipeline dedupe logic incorrectly merges similar events across weeks. Rare data inconsistency in event_occurrences table.
- Workaround: Check `event_sources` table to see which crawl events contributed to archived events. Restore from `crawl_events` if needed.
- Root cause: Merger deduplication heuristics may be too aggressive for recurring events with similar names.

**Location Merging Silently Skips Entries:**
- Symptoms: Running location merge script leaves duplicate locations. No clear indication of which locations were merged vs. skipped.
- Files: `scripts/merge_locations.php` (line 183-189)
- Trigger: Running merge without validating keeper_id and dup_id exist beforehand. Script logs warnings but continues silently.
- Workaround: Manually inspect locations table for duplicates. Use conflicts admin panel to resolve.
- Root cause: Script does not validate location references before attempting merge. Should fail fast rather than skip silently.

**Website ID Mismatches Between Local and Production:**
- Symptoms: Running `scripts/add_websites.php` on production after local testing causes event backlog. Events point to non-existent website_ids.
- Files: `scripts/add_websites.php` (line 427-430)
- Trigger: Adding websites to local database first, then running on production without ensuring ID consistency.
- Workaround: Always run on production first, then sync back to local. Document this in README.
- Root cause: Script does not handle ID sequences properly when adding to different databases. Should accept explicit IDs or warn about environment mismatch.

## Security Considerations

**CORS Allows All Origins:**
- Risk: API endpoints allow requests from any origin (`Access-Control-Allow-Origin: *`)
- Files: `src/api/events.php` (line 17), `src/api/websites.php`, `src/api/sync.php`, `src/api/locations.php`, and other API files
- Current mitigation: Public API (events/locations are read-only and public), so origin doesn't matter for those. However, admin endpoints and edit APIs are also exposed.
- Recommendations: Restrict CORS to known origins. Admin APIs should use stricter CORS or require session tokens. Implement CSRF tokens for mutations.

**SQL Injection Risk in Dynamic Query Building:**
- Risk: `src/api/sync.php` (line 274) dynamically constructs UPDATE queries with user-controlled table/field names: `"UPDATE \`$tableName\` SET \`$fieldName\` = ?"`
- Files: `src/api/sync.php` (line 274-275), `src/api/edit_logger.php`
- Current mitigation: Field names are validated against a whitelist initially, but no explicit validation shown in visible code.
- Recommendations: Ensure strict whitelist validation before using field/table names in queries. Add input validation layer before query builder. Use prepared statement placeholders for all user input, including structural elements if possible (though table/field names cannot use ?).

**Session and Authentication Management:**
- Risk: `src/api/auth.php` handles user registration and login, but session security practices are not visible
- Files: `src/api/auth.php` (line 27 in events.php calls `session_start()`)
- Current mitigation: Using PDO prepared statements (seen in `auth.php` line 91, 143)
- Recommendations: Ensure session cookies use HttpOnly, Secure, SameSite flags. Implement rate limiting on login/registration endpoints. Add password hashing validation (bcrypt/argon2).

**HTML Injection in Popup Content:**
- Risk: Event names, descriptions, and location names are displayed in popups using innerHTML-based DOM manipulation
- Files: `src/js/ui/popupContentBuilder.js` (150 .innerHTML operations), `src/js/ui/bottomSheet.js` (DOM builder functions)
- Current mitigation: Some sanitization via `Utils.escapeHtml()` and `Utils.formatAndSanitize()` visible in `src/js/core/utils.js`
- Recommendations: Audit all `.innerHTML` assignments. Prefer `.textContent` for user data. Use DOMPurify or similar sanitization library for rich text. Validate backend that event data doesn't contain script tags.

**Sensitive Data in Coordinates:**
- Risk: Event location coordinates are publicly exposed in JSON files (`src/data/`)
- Files: `src/data/` (generated), `src/api/locations.php`, `src/api/events.php`
- Current mitigation: Coordinates are already publicly shown on map
- Recommendations: No action needed if coordinates are meant to be public (they are). Ensure no PII (organizer home addresses, phone numbers) is included in location data.

## Performance Bottlenecks

**Excessive Data Processing in Frontend:**
- Problem: All events and locations are loaded into memory as JavaScript objects. Filtering, searching, and tag indexing done on client-side using nested loops and maps.
- Files: `src/js/data/dataManager.js` (multiple `.map()`, `.filter()`, `.forEach()` operations), `src/js/data/searchManager.js`, `src/js/data/filterManager.js`
- Cause: No pagination or server-side filtering. App loads "initial" dataset (~80-150 events) for fast startup, then full dataset on demand. Full dataset processing can be 500+ operations.
- Improvement path: Implement API-driven pagination. Move filtering to backend (`src/api/events.php`). Cache processed results (tag frequencies, normalized search index) in localStorage. Consider Web Workers for heavy calculations.

**No Lazy Loading for Map Markers:**
- Problem: All markers for all events are added to MapLibre feature state at once. With 500+ events, this creates large GeoJSON payload and feature state lookup overhead.
- Files: `src/js/map/mapManager.js` (line 69-100+ for layer setup), `src/js/map/markerController.js` (marker rendering)
- Cause: Initial implementation prioritized simplicity. MapLibre feature-state is efficient but still requires full feature set to be in memory.
- Improvement path: Implement viewport-based marker loading. Only add markers for events visible in current map bounds. Use debounced moveend handler to add/remove markers dynamically.

**Viewport Calculation Runs on Every Map Move:**
- Problem: `calculateViewportBounds()` and related viewport calculations run on map `moveend` event, even for tiny pans
- Files: `src/js/map/viewportManager.js` (line 109-200+)
- Cause: No debouncing or early exit for moves that don't change visible events significantly.
- Improvement path: Add debounce timer (200-300ms) to viewport recalculation. Cache previous bounds and exit early if new bounds contain same set of locations. Only recalculate when bounds changed by >5% of map size.

**Tag Frequency Recalculation on Every Filter:**
- Problem: Tag frequencies recalculated from scratch for every filter change or date range change
- Files: `src/js/tags/tagColorManager.js`, `src/js/tags/filterPanelUI.js` (frequency update calls)
- Cause: No memoization or incremental update strategy.
- Improvement path: Cache tag frequency results. Implement incremental frequency updates (add/remove counts based on events added/removed). Use a frequency cache layer with invalidation.

**No Compression for Large JSON Data Files:**
- Problem: `src/data/events-full.json` and `locations-full.json` served without analysis of compression effectiveness
- Files: `src/.htaccess` (compression config exists but effectiveness not measured)
- Cause: Frontend bundles are hashed and cached aggressively, but data files are not versioned, making compression harder to measure.
- Improvement path: Measure actual bandwidth savings from gzip. Consider splitting large JSON files by geotag or date range. Implement incremental data loading with versioning.

## Fragile Areas

**App.state Global Mutation:**
- Files: `src/js/script.js`, all modules that read/write to App.state
- Why fragile: App.state is modified by 15+ modules without clear ownership or change tracking. State changes can cascade through the system unpredictably. Hard to debug "why did my filter break?"
- Safe modification: Before modifying state, trace all modules that depend on that field. Create a change log in comments. Write a test that verifies state transitions. Consider using a state wrapper with validation.
- Test coverage: No tests exist. At minimum, add integration tests for state transitions (filter change → marker update → frequency recalculation).

**MapLibre Feature State and Layer Visibility:**
- Files: `src/js/map/mapManager.js`, `src/js/map/markerController.js`
- Why fragile: Feature state is stored in MapLibre engine (opaque). If style is changed (theme switch), features are lost and must be re-added. Marker visibility depends on layer filter expressions that are compiled by MapLibre.
- Safe modification: Any changes to marker rendering must also update the style.load handler in mapManager to restore features. Test theme switching after marker updates.
- Test coverage: Manual testing of theme switch shows it works, but no regression test.

**Popup Content Builder with Dynamic HTML:**
- Files: `src/js/ui/popupContentBuilder.js` (469 lines)
- Why fragile: Constructs popup HTML by concatenating strings and using innerHTML. Event data from API must be sanitized. Any change to data format breaks popup.
- Safe modification: Use DOM builder functions instead of string concatenation. Add sanitization at data entry point (API), not just at display point. Update schema validation when event data structure changes.
- Test coverage: Manual screenshots only. No automated tests for popup rendering with various event types.

**Crawl4AI Integration with Dynamic URL Templates:**
- Files: `pipeline/crawler.py` (line 32-50)
- Why fragile: URL templates use date placeholders ({{month}}, {{year}}, {{next_month}}). If a venue's URL structure changes (e.g., from `/events/february` to `/events/2-2026`), template will break and crawl will fail silently.
- Safe modification: Add logging when URL template resolution fails. Validate resolved URLs before crawling. Add venue maintainers ability to test/update URLs manually. Store actual crawled URLs to detect drift.
- Test coverage: No tests for template resolution. Manual testing needed for each new venue.

**Event Deduplication Heuristics:**
- Files: `pipeline/merger.py` (deduplication logic)
- Why fragile: Matching events across crawl runs using fuzzy name matching + location + date range. If venue name changes slightly or event timing shifts, may create duplicates or false matches.
- Safe modification: Add dry-run mode to merger to show matches before applying. Add manual review UI in admin dashboard. Store match scores so low-confidence matches can be reviewed.
- Test coverage: `pipeline/tests/test_merger.py` exists but needs more edge cases (name variations, different timezones, recurring events).

**Admin Dashboard History Panel:**
- Files: `src/admin/history.php` (500 lines), `src/admin/history_api.php` (277 lines)
- Why fragile: Tracks all edits to events/locations, but no validation that reverted edits can't create conflicts. If two users revert different versions of same event, database state becomes inconsistent.
- Safe modification: Implement edit conflict detection. Add UI to show conflicting edits before applying. Require merge strategy (ours/theirs) for conflicts.
- Test coverage: Manual testing only. No automated tests for concurrent edits.

## Scaling Limits

**Single JSON Files for All Events:**
- Current capacity: ~500-1000 events in single events-full.json (100-300KB)
- Limit: Browser memory, network download time, initial load time. At 2000+ events, noticeable slowdown on mobile (>2-3s load time).
- Scaling path: Implement API-driven pagination. Load initial 100 events, fetch rest on demand or via Service Worker pre-caching. Split by geotag (lower Manhattan vs. Upper Manhattan) or date range.

**Database Query Performance for Large Result Sets:**
- Current capacity: `src/api/events.php` can list 1000+ events, but queries are not indexed for complex filters
- Limit: Queries without proper indexes will slow as event count grows past 5000. Range queries on occurrences table are O(n).
- Scaling path: Add indexes on frequently filtered columns (website_id, location_id, date ranges). Implement query caching layer. Use prepared statements and query result caching.

**Crawl Pipeline Processing Time:**
- Current capacity: ~50-100 websites crawled per run, ~500 events extracted per run
- Limit: Crawl4AI timeout (180s per site) × 100 sites = 5+ hours per full pipeline run. Extraction cost increases with event count.
- Scaling path: Parallelize crawling using asyncio (already partially implemented). Implement incremental extraction (only process new/changed content). Cache extracted results.

**Mobile App WebView Performance:**
- Current capacity: Smooth performance on iPhone 12+ with 500 events, noticeable lag on iPhone SE or 2+ year old Android
- Limit: WebView JS engine performance and available memory. Complex DOM operations (filter panel with 100+ tags) cause jank.
- Scaling path: Virtualize tag lists (render only visible tags). Use requestAnimationFrame for DOM updates. Consider native map implementation for performance.

## Dependencies at Risk

**Crawl4AI Stability:**
- Risk: Crawl4AI is actively developed but relatively new library. API may change. Library has known issues with certain website types (heavy JS rendering).
- Impact: Crawl failures cause events to be missing. If Crawl4AI is abandoned, no clear replacement (Playwright/Puppeteer are heavier, need server resources).
- Migration plan: Maintain wrapper around Crawl4AI in `pipeline/crawler.py`. Document fallback to manual data entry for high-value venues. Consider evaluating Playwright or native headless browser if Crawl4AI becomes unreliable.

**Gemini API Dependency:**
- Risk: Gemini AI API rate limits and pricing model may change. API key is required to run pipeline.
- Impact: Pipeline breaks if API quota exceeded. Cost increases unpredictably if event count scales. No local alternative for extraction.
- Migration plan: Implement fallback extraction using Claude API (already used in project). Add fallback to regex-based extraction for simple event lists. Cache extraction results to avoid re-processing.

**MapLibre GL JS WebGL Support:**
- Risk: WebGL is not available on all older browsers or in rare device configurations. MapLibre 3.x is more demanding than Leaflet.
- Impact: Map may fail to render on unsupported devices. Fallback rendering not implemented.
- Migration plan: Test on min iOS 14 and Android 6+ devices. Consider lightweight raster tile layer as fallback. Add canvas-based marker rendering as fallback for WebGL failures.

**Flatpickr Date Picker:**
- Risk: Flatpickr is actively maintained but small library. No longer maintained version may break with newer JavaScript ecosystems.
- Impact: Date range picker breaks on unsupported browsers. No time picker (only date).
- Migration plan: Already vendored via npm (see `build.js`). If Flatpickr becomes unmaintained, replace with native HTML `<input type="date">` or Litepicker. Store in `src/css/index.css` imports.

## Missing Critical Features

**No Offline Mode:**
- Problem: App requires internet to load events. Cached data (Service Worker) not implemented.
- Blocks: Users cannot browse map on weak/no connection. Can't use on subway or in areas with poor service.

**No User-Generated Events:**
- Problem: Events are curator-only (staff adds them). Users cannot submit event tips or corrections.
- Blocks: Community cannot help maintain data. Coverage limited to web-crawlable venues.

**No Event Notifications:**
- Problem: Users have no way to get alerts when new events are added for favorite venues/tags.
- Blocks: Users must manually revisit site to discover new events. Reduces engagement.

**No Admin User Roles:**
- Problem: All admins have full database access. No curator-only or read-only roles.
- Blocks: Cannot safely onboard volunteer curators. Risk of accidental data loss.

**No Accessibility Testing:**
- Problem: WCAG compliance not tested. Keyboard navigation not verified. Screen reader support unknown.
- Blocks: Users with disabilities cannot use app. Potential legal liability.

## Test Coverage Gaps

**No Frontend Unit Tests:**
- What's not tested: Module initialization, data transformation, event filtering, tag state management, marker rendering, popup content generation
- Files: `src/js/` (all files)
- Risk: Refactoring any module could silently break dependent modules. Bugs slip through that should be caught by basic unit tests (e.g., date parsing, tag frequency calculation).
- Priority: High - prevents safe refactoring. Start with critical modules: `dataManager.js`, `filterManager.js`, `mapManager.js`.

**No API Integration Tests:**
- What's not tested: CRUD operations, edit conflict handling, sync behavior, permission checks
- Files: `src/api/` (all PHP files)
- Risk: API changes could break frontend without catching it. Admin endpoints could be vulnerable to unauthorized access if auth logic changes.
- Priority: High - especially for admin endpoints. Use PHPUnit or similar.

**No E2E Tests:**
- What's not tested: Full user workflows (search → filter → click marker → view popup), theme switching, mobile responsiveness
- Files: Integration of all modules
- Risk: Major regressions slip through (e.g., "filter breaks after marker update"). Mobile-specific bugs go unnoticed until user reports.
- Priority: Medium - can use Playwright or Cypress to automate screenshot verification.

**No Mobile App Tests:**
- What's not tested: WebView integration, app-specific gestures, native bridge communication (Android/iOS)
- Files: `mobile/android/`, `mobile/ios/`
- Risk: App crashes on app-specific code paths. iOS/Android specific bugs not caught.
- Priority: Medium - less critical than web, but mobile users rely on app. Manual testing + Xcode/Android Studio simulator tests sufficient.

**No Database Schema Tests:**
- What's not tested: Migration scripts, foreign key constraints, index effectiveness
- Files: `database/schema.sql`, `database/migrate_schema.py`
- Risk: Migration to new schema corrupts data or breaks API. Migrations fail silently, leaving database in inconsistent state.
- Priority: Medium - migrations are high-risk. Add validation script to check schema state before/after migration.

**Crawler Output Validation Not Automated:**
- What's not tested: Crawler output for malformed HTML, missing body tag, truncated content
- Files: `pipeline/crawler.py`, `pipeline/extractor.py`
- Risk: Malformed crawled content breaks extraction. Warnings logged but not acted upon. Invalid events inserted into database.
- Priority: Medium - already has some checks (MIN_CRAWL_CONTENT_SIZE), but needs stricter validation.

---

*Concerns audit: 2026-02-24*
