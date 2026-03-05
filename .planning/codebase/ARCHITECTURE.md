# Architecture

**Analysis Date:** 2026-02-24

## Pattern Overview

**Overall:** Modular MVC-style architecture with event-driven data flow

**Key Characteristics:**
- Separation of concerns via independent module system (not class-based OOP)
- Centralized state management in `App.state` (monolithic object)
- Event-driven communication through callbacks and provider objects
- Two-phase data loading (initial + full dataset) for performance
- GPU-accelerated WebGL marker rendering via MapLibre native layers

## Layers

**Presentation (UI Layer):**
- Purpose: DOM manipulation, rendering, user interactions
- Location: `src/js/ui/`, `src/css/`, `src/index.html`
- Contains: Modal managers, theme management, bottom sheets, popup builders, emoji rendering
- Depends on: Core utilities, data layer output
- Used by: Main application orchestrator (`App`)

**Interaction (Tags/Filtering Layer):**
- Purpose: Tag state management, filter panel UI, related tags enrichment
- Location: `src/js/tags/`
- Contains: Tag state cycling, color assignment, related tag relationships, filter panel rendering
- Depends on: Data layer, core utilities
- Used by: App and data layer (bidirectional via callbacks)

**Data Layer:**
- Purpose: Data fetching, processing, indexing, filtering, and searching
- Location: `src/js/data/`
- Contains: Data fetching with error handling, event/location indexing, tag-based filtering, semantic search with scoring
- Depends on: Core utilities, constants
- Used by: Map layer, tags layer, main application

**Map/Viewport Layer:**
- Purpose: Map rendering, marker lifecycle, viewport calculations
- Location: `src/js/map/`
- Contains: MapLibre integration, WebGL symbol layer markers, popup management, viewport visibility calculations
- Depends on: Data layer, core utilities
- Used by: Main application

**Core Layer:**
- Purpose: Shared utilities, constants, URL parameter handling
- Location: `src/js/core/`
- Contains: Constants (time, distance, UI), utility functions, URL parsing, browser storage
- Depends on: Nothing (lowest level)
- Used by: All other layers

## Data Flow

**Initial Load (Phase 1):**
1. User loads page → `DOMContentLoaded` fires
2. App parses URL parameters via `URLParams.parse()`
3. App loads initial dataset (smaller events/locations JSON files)
4. `DataManager.processInitialData()` builds event index, location index, tag frequencies
5. Tag color assignment and related tags system initialized
6. Map renders with initial marker set
7. Date picker initialized with URL params or defaults
8. UI shown to user (loading screen hidden)
9. Background: full dataset loading begins asynchronously

**Full Dataset Load (Phase 2):**
1. App fetches full events and locations JSON in parallel
2. `DataManager.processFullData()` merges with initial data, rebuilds indexes
3. Map emoji images loaded
4. Tag filtering re-evaluated with complete dataset
5. Search index rebuilt
6. Filters re-applied, display updates

**Tag Selection Flow:**
1. User clicks tag button
2. `TagStateManager.cycleTagState()` transitions state (unselected → selected → required → forbidden)
3. If selected/required: `TagColorManager.assignColorToTag()` assigns color
4. If deselected: `TagColorManager.unassignColorFromTag()` removes color
5. Callback triggers: `App.filterAndDisplayEvents()`
6. `RelatedTagsManager.enrichSelectedTags()` expands selection with related tags
7. `FilterManager.filterEventsByTags()` filters events by rules
8. Map markers updated, tag UI re-rendered

**Search & Filtering Flow:**
```
User types in search or changes filters
    ↓
App.performSearch() or App.updateFilteredEventList()
    ↓
Get selected tags with colors from TagColorManager
    ↓
Enrich with related tags (RelatedTagsManager)
    ↓
Extract all tags for filtering
    ↓
FilterManager.filterEventsByTags() → filtered events
    ↓
SearchManager.search() → scored/ranked results
    ↓
FilterPanelUI renders sections with results
    ↓
MarkerController updates map markers
```

**Viewport Filtering Flow:**
1. User pans/zooms map
2. `ViewportManager.calculateVisibleCenter()` accounts for left filter panel overlay
3. `MarkerController` on map moveend:
   - Calculates visible bounds
   - Filters currently matching events to visible set
   - Updates map marker visibility
   - Searches relevant items if needed

**State Management:**
- Centralized in `App.state` object (monolithic)
- Properties include: map instance, all events, filters, selected tags, dates, visible locations
- Modified via:
  - Direct property assignment (e.g., `state.currentlyMatchingEvents = [...]`)
  - Module callbacks that receive state reference
  - Provider objects passed to modules (loose coupling)

## Key Abstractions

**Module Pattern (IIFE):**
- Purpose: Encapsulation and namespace isolation
- Examples: `DataManager`, `MapManager`, `FilterManager`, `TagStateManager`
- Pattern:
  ```javascript
  const ModuleName = (() => {
    const privateState = {};
    function privateFunction() {}
    function publicFunction() {}
    return { publicFunction };
  })();
  ```

**Provider Objects:**
- Purpose: Reduce callback parameter bloat, improve readability
- Examples:
  - `filterProvider` → used by `MarkerController` for accessing tag states
  - `eventProvider` → used by `MarkerController` for managing forced event display
  - `colorProvider` → used by `TagStateManager` for tag color operations
- Pattern: Objects with methods that module calls to access parent state

**Event Index:**
- Purpose: Fast O(1) lookup of events by tag
- Structure: `{ tagName: [eventId1, eventId2, ...], ... }`
- Built in: `DataManager.buildTagIndex()`
- Used in: `FilterManager` for fast filtering

**Tag Enrichment:**
- Purpose: Expand user selections with semantically related tags
- Process:
  1. User selects "Art"
  2. `RelatedTagsManager.enrichSelectedTags()` loads related tags from `data/related_tags.json`
  3. Returns: `[["Art", color, 1.0], ["Contemporary Art", color, 0.8], ...]`
  4. Weight used for: filtering (binary: include/exclude) and scoring (weight × 3 points)

**Score-Based Ranking:**
- Purpose: Order search results by relevance
- Components:
  - Base score: 1
  - Matching boost: +10 (if event matches current filters)
  - Multi-tag match: weight × 3 (per matching tag in enriched set)
  - Visibility boost: +5 (if event currently visible on map)
  - Proximity bonus: 0-5 (distance-based, max 20km)
  - Temporal bonus: 0-5 (for events, days from selected date)
  - Exact tag match: +1000 (when searching tags directly)

## Entry Points

**`src/index.html`:**
- Location: Web application markup
- Triggers: Browser load event
- Responsibilities: Define DOM structure, load scripts in correct order

**`src/js/script.js` (main application):**
- Location: Application orchestrator and state container
- Triggers: `DOMContentLoaded` event
- Responsibilities:
  - Initialize all modules (data, map, UI, tags)
  - Coordinate data loading phases (initial → full)
  - Manage application state (`App.state`)
  - Implement filter/search logic by calling module methods
  - Handle user interactions (date picker, tag selection, search)
  - Manage map pan/zoom interactions

**`src/js/data/dataManager.js`:**
- Location: Data fetching entry point
- Triggers: Called by App during initialization
- Responsibilities: Load JSON files, parse, error handling, build indexes

**`src/js/map/mapManager.js`:**
- Location: MapLibre integration
- Triggers: Called by App after map container is ready
- Responsibilities: Create map instance, manage source/layers, handle popups

## Error Handling

**Strategy:** Try-catch with user-facing toast notifications

**Patterns:**
- `DataManager.fetchData()` wraps fetch with comprehensive error handling:
  - Timeout errors: "Request timed out after X seconds..."
  - Network errors: "Unable to connect to the server..."
  - HTTP errors: Status-specific messages (404, 500, etc.)
  - Parse errors: "Invalid data format received..."
- Phase 2 (full data) errors: Toast notification, continue with initial dataset
- Phase 1 (initial data) errors: Show error in loading container, block UI

**Error Types:**
- Network failures → user-friendly messages
- Invalid JSON → data corruption message
- Missing endpoints → 404 handling
- Timeouts → connection diagnostics

## Cross-Cutting Concerns

**Logging:** Console logs in development (searchable via console for debugging)
- Data loading progress
- Tag enrichment process
- Filter and search scoring
- Module initialization

**Validation:**
- Date picker: min/max bounds, range validation
- URL parameters: tag existence check, date range validation
- Events: required fields check (id, location, tags, dates)
- Map: bounds checking for geolocation

**Authentication:** Not implemented (public application)

**Performance Optimization:**
- WebGL markers: GPU-accelerated rendering via MapLibre
- Two-phase data loading: Show UI quickly with initial data
- Tag index: O(1) event lookup by tag instead of O(n) iteration
- Search debounce: 100ms delay on search input
- Map move throttle: 250ms delay on pan/zoom
- Viewport culling: Only render visible markers

**Responsive Design:**
- Mobile breakpoint: 768px
- Filter panel: Full-width on mobile, sidebar on desktop
- Bottom sheet for popup content on mobile
- Gesture handling: Swipe to reorder filter sections

## Module Communication Patterns

**Direct Calls:**
- App calls module methods directly: `DataManager.fetchData()`, `MapManager.init()`
- Synchronous calls for setup, async for data loading

**Callbacks:**
- Data changes trigger callbacks: date picker → `onDatePickerClose`
- Filter changes trigger: tag selection → `onFilterChange`
- Search input → `performSearch` via debounced input handler

**Shared State:**
- App.state passed by reference to module functions
- Modules read/write state properties directly
- No state isolation between modules

**Provider Pattern:**
- Loosest coupling used for complex interactions
- Example: `MarkerController.init({ filterProvider, eventProvider })`
- Provider object methods called to query parent state

