# Codebase Structure

**Analysis Date:** 2026-02-24

## Directory Layout

```
momaverse/
├── src/                        # Source files (bundled to dist/ on build)
│   ├── index.html             # Main application entry point
│   ├── about.html             # About page
│   ├── js/                    # JavaScript modules (bundled)
│   │   ├── script.js          # Main application orchestrator
│   │   ├── core/              # Core utilities and constants
│   │   ├── data/              # Data management and filtering
│   │   ├── map/               # Map, markers, and viewport
│   │   ├── tags/              # Tag filtering and UI
│   │   └── ui/                # UI components and modals
│   ├── css/                   # Stylesheets (bundled)
│   │   ├── index.css          # Main CSS entry point
│   │   ├── variables.css      # Design tokens
│   │   ├── layout.css         # Base layout structure
│   │   ├── filter-panel.css   # Left sidebar styles
│   │   ├── tags.css           # Tag button styles
│   │   ├── map.css            # Map container styles
│   │   ├── popups.css         # Popup styles
│   │   ├── bottom-sheet.css   # Mobile bottom sheet styles
│   │   ├── modals.css         # Modal dialogs
│   │   └── fonts.css          # Typography
│   ├── data/                  # Data files (JSON, map styles)
│   │   ├── events.init.json   # Initial events dataset (bundled)
│   │   ├── events.full.json   # Complete events dataset (bundled)
│   │   ├── locations.init.json # Initial locations (bundled)
│   │   ├── locations.full.json # Complete locations (bundled)
│   │   ├── tags.json          # Tag configuration
│   │   ├── related_tags.json  # Related tag relationships
│   │   ├── map-style-dark.json # Dark theme map style
│   │   └── map-style-light.json # Light theme map style
│   ├── images/                # SVG and image assets
│   │   ├── torch.svg          # Logo
│   │   ├── logo.svg           # Modal logo
│   │   └── trumpet.svg        # Emoji replacement icon
│   ├── fonts/                 # Font files (Inter)
│   │   ├── glyphs/           # Font glyph data
│   │   ├── Inter-*.woff2      # Web font files
│   │   └── ...
│   ├── api/                   # Backend PHP API endpoints
│   │   ├── events.php         # Event CRUD operations
│   │   ├── locations.php      # Location CRUD operations
│   │   ├── feedback.php       # Feedback submission
│   │   ├── sync.php           # Data sync operations
│   │   ├── auth.php           # Authentication
│   │   └── ...
│   └── admin/                 # Admin interface
│       └── admin.js           # Database admin panel
│
├── dist/                      # Built output (generated, not committed)
│   ├── index.html
│   ├── app-[hash].js          # Bundled JavaScript (content-hashed)
│   ├── app-[hash].css         # Bundled CSS (content-hashed)
│   ├── data/                  # Data files
│   ├── images/                # Assets
│   ├── fonts/                 # Font files
│   ├── api/                   # API files
│   └── admin/                 # Admin files
│
├── build.js                   # Build script (esbuild bundler)
├── pipeline/                  # Data pipeline (Python/scripts)
├── database/                  # Database schema and scripts
├── scripts/                   # Utility scripts
├── package.json               # Dependencies (esbuild, flatpickr)
├── .env.example               # Environment variable template
├── .gitignore                 # Git ignore rules
└── README.md                  # Project documentation
```

## Directory Purposes

**`src/js/`:**
- Purpose: All application JavaScript modules
- Contains: Core utilities, data management, map integration, tag filtering, UI components
- Key files: `script.js` (orchestrator), `dataManager.js`, `mapManager.js`, `filterManager.js`

**`src/js/core/`:**
- Purpose: Shared utilities and constants
- Contains: Constants (time, distance, UI values), utility functions (HTML escape, date format), URL parsing, browser storage
- Key files:
  - `constants.js` - Centralized constants (eliminates magic numbers)
  - `utils.js` - Reusable functions (debounce, throttle, SafeStorage)
  - `urlParams.js` - URL parameter parsing and state management
  - `historyManager.js` - Browser history API wrapper

**`src/js/data/`:**
- Purpose: Data operations (fetching, processing, indexing, filtering, searching)
- Contains: Network data fetching, event/location indexing, tag-based filtering, semantic search with scoring
- Key files:
  - `dataManager.js` - Load JSON, process events/locations, build indexes (27KB)
  - `filterManager.js` - Filter events by tags, dates, viewport with tag states (16KB)
  - `searchManager.js` - Search locations/events/tags with scoring algorithm (20KB)

**`src/js/map/`:**
- Purpose: Map rendering, marker management, viewport calculations
- Contains: MapLibre integration, WebGL symbol layer markers, popup display, viewport-aware filtering
- Key files:
  - `mapManager.js` - Create/manage map instance, handle sources/layers (27KB)
  - `markerController.js` - Marker lifecycle, popup content, display limits (9KB)
  - `viewportManager.js` - Calculate visible center accounting for overlay (24KB)

**`src/js/tags/`:**
- Purpose: Tag filtering UI and related tag enrichment
- Contains: Tag state machine (unselected/selected/required/forbidden), color assignment, related tags from JSON, filter panel rendering
- Key files:
  - `filterPanelUI.js` - Orchestrates tag panel, delegates to specialized modules (17KB)
  - `tagStateManager.js` - Tag state cycling, button rendering (16KB)
  - `tagColorManager.js` - Assign colors to selected tags from palette (18KB)
  - `relatedTagsManager.js` - Load and apply related tags with weights (4KB)
  - `searchController.js` - Omni search input, debouncing, special terms (5KB)
  - `selectedTagsDisplay.js` - Show selected tags, toggle related tags inclusion (9KB)
  - `sectionRenderer.js` - Render collapsible search result sections (23KB)

**`src/js/ui/`:**
- Purpose: UI components, dialogs, theming, gestures
- Contains: Modal dialogs, theme switching, emoji font loading, gesture handlers, toast notifications, popup builders
- Key files:
  - `uiManager.js` - Date picker init, event listeners (8KB)
  - `popupContentBuilder.js` - Generate popup HTML for locations (21KB)
  - `modalManager.js` - Welcome/settings/feedback modals (9KB)
  - `bottomSheet.js` - Mobile bottom sheet for popups (27KB)
  - `themeManager.js` - Dark/light theme switching (6KB)
  - `emojiManager.js` - Emoji font loading (8KB)
  - `gestureHandler.js` - Swipe gestures (12KB)
  - `feedbackManager.js` - User feedback submission (8KB)
  - `toastNotifier.js` - Toast notifications (2KB)

**`src/css/`:**
- Purpose: All styling, modular by component
- Contains: Design tokens (colors, shadows), layout structure, component styles, responsive breakpoints
- Key files:
  - `index.css` - Main entry point, imports all other CSS in order
  - `variables.css` - CSS custom properties (colors, shadows, spacing)
  - `layout.css` - Base HTML/body styles, grid layout
  - `filter-panel.css` - Left sidebar styles
  - `tags.css` - Tag button states and colors
  - `map.css` - Map container, controls, markers
  - `popups.css` - Popup content styling
  - `modals.css` - Modal dialogs
  - `fonts.css` - @font-face declarations

**`src/data/`:**
- Purpose: Static data files and configuration
- Contains: Event/location JSON datasets, tag configuration, map styles, related tag relationships
- Key files:
  - `events.init.json`, `locations.init.json` - Initial dataset (quick startup)
  - `events.full.json`, `locations.full.json` - Complete datasets (background load)
  - `tags.json` - Tag color configuration and geotags
  - `related_tags.json` - Related tag relationships with weights (2MB)
  - `map-style-dark.json`, `map-style-light.json` - MapLibre style definitions

**`src/api/`:**
- Purpose: Backend REST API endpoints (PHP)
- Contains: Database operations, feedback submission, admin auth
- Key files:
  - `events.php` - GET/POST events (CRUD)
  - `locations.php` - GET/POST locations (CRUD)
  - `feedback.php` - Submit user feedback
  - `sync.php` - Data synchronization
  - `auth.php` - Admin authentication
  - `websites.php` - Website data management
  - `edit_logger.php` - Log edit operations

**`src/admin/`:**
- Purpose: Admin interface for database management
- Contains: Database view and edit interface
- Key files: `admin.js` - Admin panel UI

**`build.js`:**
- Purpose: Build system (esbuild bundler)
- Responsibilities:
  - Extract JS file order from `index.html`
  - Concatenate JS files in order
  - Minify JS/CSS (production) or pass through (dev)
  - Generate content-hashed filenames for cache busting
  - Update HTML with bundle paths
  - Copy asset directories to dist/

## Key File Locations

**Entry Points:**
- `src/index.html` - Web application markup and script tags (loads in correct order)
- `src/js/script.js` - Main application orchestrator (executes on DOMContentLoaded)

**Configuration:**
- `src/js/script.js` - App.config contains all hardcoded URLs, dates, colors, map settings
- `src/data/tags.json` - Tag configuration (colors, geotags)
- `src/data/related_tags.json` - Related tag relationships with weights
- `build.js` - Build configuration (asset directories, minification)
- `.env.example` - Template for environment variables

**Core Logic:**
- `src/js/data/dataManager.js` - Data loading and indexing (27KB)
- `src/js/data/filterManager.js` - Tag-based event filtering (16KB)
- `src/js/data/searchManager.js` - Search and scoring algorithm (20KB)
- `src/js/map/mapManager.js` - Map rendering via MapLibre (27KB)
- `src/js/tags/tagColorManager.js` - Tag color assignment (18KB)

**Testing:**
- `pipeline/tests/` - Python tests for data pipeline

## Naming Conventions

**Files:**
- Camel case: `dataManager.js`, `markerController.js`, `popupContentBuilder.js`
- Index files use simple names: `index.html`, `index.css`
- CSS files use kebab-case: `filter-panel.css`, `bottom-sheet.css`
- Data files use snake_case: `related_tags.json`, `events.init.json`

**Directories:**
- Lower case: `src/`, `js/`, `data/`, `api/`, `css/`
- Plural for collections: `images/`, `fonts/`, `scripts/`
- Functional grouping: `core/`, `data/`, `map/`, `tags/`, `ui/`

**CSS Classes:**
- Kebab-case: `.filter-panel`, `.tag-button`, `.bottom-sheet`
- State prefix: `.state-selected`, `.state-required`, `.state-forbidden`, `.state-related`
- Prefixed for specificity: `.modal-content`, `.popup-title`, `.toast-notification`

**JavaScript Identifiers:**
- Functions and variables: camelCase
- Constants: UPPER_SNAKE_CASE (in `constants.js`)
- Module names: CapitalizedCamelCase (e.g., `DataManager`, `MapManager`)
- Private functions: Leading underscore `_privateFunction`

## Where to Add New Code

**New Feature (Filtering/Search):**
- Primary code: `src/js/data/filterManager.js` or `src/js/data/searchManager.js`
- Tests: `pipeline/tests/` (for data pipeline) or inline in module
- Configuration: `src/js/script.js` App.config if adding URLs

**New UI Component:**
- Implementation: `src/js/ui/` (if generic) or `src/js/tags/` (if tag-related)
- Styles: Create new file `src/css/[component-name].css` and import in `src/css/index.css`
- Add to HTML: Update `src/index.html` if new DOM structure needed

**New Data Processing:**
- Add to: `src/js/data/dataManager.js` (for loading) or `src/js/data/filterManager.js` (for processing)
- Follow pattern: Private function → public API method

**New Map Feature:**
- Map-related: `src/js/map/mapManager.js`
- Marker logic: `src/js/map/markerController.js`
- Viewport logic: `src/js/map/viewportManager.js`

**Utilities:**
- Shared helpers: `src/js/core/utils.js`
- Constants: `src/js/core/constants.js`
- Import and use: Other modules import from core

## Special Directories

**`src/data/`:**
- Purpose: Static JSON data files loaded at runtime
- Generated: No (manually maintained)
- Committed: Yes
- Bundled: Yes, copied to dist/ on build
- Load pattern: `DataManager.fetchData('data/events.init.json')`

**`src/images/`:**
- Purpose: SVG and image assets
- Generated: No
- Committed: Yes
- Bundled: Yes, copied to dist/ on build

**`src/fonts/`:**
- Purpose: Font files and glyph data
- Generated: Partially (glyph data in `glyphs/` subdirs)
- Committed: Yes
- Bundled: Yes, WOFF2 files copied to dist/

**`dist/`:**
- Purpose: Built output ready for deployment
- Generated: Yes (by `build.js`)
- Committed: No (in .gitignore)
- Creation: Run `npm run build` or `npm run dev`

**`pipeline/`:**
- Purpose: Data collection and processing (separate system)
- Language: Python
- Contains: Scraper logic, database schema, tests

**`database/`:**
- Purpose: Database schema and initialization scripts
- Contains: SQL schema definitions, migrations

## Build System

**Entry:** `build.js` (Node.js script)

**Process:**
1. Parse `src/index.html` to extract `<script>` tags in order
2. Read JS files in that order, concatenate (not a bundler, just concatenation)
3. Prepend Flatpickr library code
4. Minify (production) or pass through (dev)
5. Bundle CSS: esbuild resolves `@import`, minifies, prepends Flatpickr CSS
6. Generate content-hashed filenames (prod) or stable names (dev)
7. Update HTML with new bundle paths
8. Copy asset directories: `data/`, `images/`, `fonts/`, `api/`, `admin/`
9. Output: `dist/` directory ready for deployment

**Commands:**
```bash
npm run dev       # Build in watch mode (unminified)
npm run build     # Production build (minified, content-hashed)
```

**Output Structure:**
- `dist/index.html` - Updated with bundle paths
- `dist/app-[hash].js` - Minified JavaScript
- `dist/app-[hash].css` - Minified CSS
- `dist/data/` - Event/location datasets, map styles
- `dist/images/` - SVG and assets
- `dist/fonts/` - Font files
- `dist/api/` - API endpoints
- `dist/admin/` - Admin interface

## Load Order

Scripts load in `src/index.html` in this order:

1. **External Libraries:**
   - MapLibre GL (CDN) - map library
   - Flatpickr (CDN) - date picker

2. **Core Layer:**
   - `js/core/constants.js` - Must be first (used by all)
   - `js/core/utils.js` - Utilities
   - `js/core/historyManager.js` - Browser history
   - `js/core/urlParams.js` - URL parsing

3. **Data Layer:**
   - `js/data/filterManager.js` - Filtering logic
   - `js/data/dataManager.js` - Data loading
   - `js/data/searchManager.js` - Search

4. **Tags Layer:**
   - `js/tags/tagColorManager.js` - Color assignment
   - `js/tags/relatedTagsManager.js` - Related tags (deferred Phase 2)
   - `js/tags/tagStateManager.js` - State machine
   - `js/tags/sectionRenderer.js` - Render results
   - `js/tags/searchController.js` - Search input
   - `js/tags/filterPanelUI.js` - Orchestrator
   - `js/tags/selectedTagsDisplay.js` - Selected tags display

5. **UI Layer:**
   - `js/ui/modalManager.js` - Modals
   - `js/ui/toastNotifier.js` - Toast notifications
   - `js/ui/gestureHandler.js` - Gestures
   - `js/ui/bottomSheet.js` - Bottom sheet
   - `js/ui/popupContentBuilder.js` - Popup HTML builder
   - `js/ui/uiManager.js` - UI coordination
   - `js/ui/emojiManager.js` - Emoji loading
   - `js/ui/themeManager.js` - Theme switching
   - `js/ui/feedbackManager.js` - Feedback

6. **Map Layer:**
   - `js/map/mapManager.js` - Map instance
   - `js/map/viewportManager.js` - Viewport calculations
   - `js/map/markerController.js` - Marker lifecycle

7. **Main Application:**
   - `js/script.js` - App orchestrator (executes DOMContentLoaded)

**CSS Load Order (in `src/css/index.css`):**
1. `variables.css` - Design tokens (all others depend on these)
2. `fonts.css` - Typography
3. `layout.css` - Base structure
4. Component files: `filter-panel.css`, `tags.css`, `map.css`, `popups.css`, `bottom-sheet.css`, `modals.css`

