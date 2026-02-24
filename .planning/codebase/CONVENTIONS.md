# Coding Conventions

**Analysis Date:** 2026-02-24

## Naming Patterns

**Files:**
- **Modules:** camelCase with descriptive names (e.g., `dataManager.js`, `filterManager.js`, `tagStateManager.js`)
- **Main entry:** `script.js` for application initialization
- **Utilities:** `utils.js`, `constants.js` for shared code
- **UI components:** descriptive names following responsibility (e.g., `popupContentBuilder.js`, `toastNotifier.js`, `modalManager.js`)

**Functions:**
- **camelCase:** All functions use camelCase (e.g., `fetchData`, `processLocationData`, `initDatePicker`, `getNextState`)
- **Descriptive verbs:** Names start with action verbs (`get`, `set`, `create`, `process`, `init`, `destroy`, `handle`)
- **Private functions:** Prefixed with underscore (e.g., `_ensureLayers`, `_addSourceAndLayers`, `_restoreAfterStyleChange`)
- **Callbacks:** Often suffixed with `Callback` or `Handler` (e.g., `onThemeChange`, `onDatePickerClose`, `gestureHandler`)

**Variables:**
- **camelCase:** All variables use camelCase (e.g., `locationKey`, `selectedDates`, `datePickerInstance`, `tagStates`)
- **Boolean prefixes:** State variables often use `is`, `has`, `should` prefix (e.g., `isInitialLoad`, `hasStartTime`, `shouldExpand`)
- **Collection names:** Plural for arrays/sets (e.g., `selectedTags`, `allEvents`, `occurrences`, `matchedTags`)
- **Maps/Objects:** Descriptive suffixes (e.g., `locationsByLatLng`, `eventsByLatLng`, `eventsById`, `tagFrequencies`)

**Constants:**
- **SCREAMING_SNAKE_CASE or nested objects:** Constants defined within IIFE modules use nested object structure for organization
- **Organization:** Constants grouped by category with section comments
  ```javascript
  const Constants = (() => {
      const TIME = {
          ONE_DAY_MS: 24 * 60 * 60 * 1000,
          SEARCH_DEBOUNCE_MS: 100
      };
      const DISTANCE = { ... };
      const UI = { ... };
      return { TIME, DISTANCE, UI };
  })();
  ```

**Types/Enums:**
- **SCREAMING_SNAKE_CASE:** For enum values (e.g., `TAG_STATE.SELECTED`, `TAG_STATE.REQUIRED`, `TAG_STATE.FORBIDDEN`)
- **Nested in objects:** Related values grouped together (e.g., `TAG_STATE = { UNSELECTED, SELECTED, REQUIRED, FORBIDDEN }`)

## Code Style

**Formatting:**
- **No formatter enforced:** Project has no `.prettierrc`, `.eslintrc`, or Prettier/ESLint configuration
- **Manual formatting:** Code is hand-formatted following consistent patterns
- **Indentation:** 4 spaces (observed consistently across all files)
- **Line breaks:** Descriptive section separators using `// ========================================` pattern

**Module Structure:**
- **IIFE pattern:** All modules use Immediately Invoked Function Expressions to create private scope
  ```javascript
  const ModuleName = (() => {
      // ========================================
      // PRIVATE STATE
      // ========================================
      const state = { ... };

      // ========================================
      // PRIVATE FUNCTIONS
      // ========================================
      function privateFunc() { ... }

      // ========================================
      // EXPORTS
      // ========================================
      return {
          publicMethod1,
          publicMethod2
      };
  })();
  ```

**Naming conventions within modules:**
- **Section headers:** Uppercase with equals separator (`// ========================================`)
- **Subsections:** descriptive comments (e.g., `// Date picker initialization`)
- **Private state:** Named `state` object (e.g., in `DataManager`, `FilterManager`)

## Import Organization

**Script Loading Order:**
- **Manual ordering:** Determined by `<script>` tag order in `index.html`
- **File list parsed from HTML:** Build system (`build.js`) reads `index.html` to determine load order
- **Typical order:** Core utilities first, then data managers, then UI components, then main `script.js`
- **External libraries:** Flatpickr included first in build process

**Dependencies:**
- **No module system:** Plain JavaScript with global namespace (all modules attached to `window`)
- **Module dependencies:** Pass through function parameters or access via global reference
- **Provider pattern:** Used to reduce callback bloat and improve organization
  ```javascript
  MarkerController.init({
    filterProvider: {
      getTagStates: () => ...,
      getSelectedDates: () => ...
    },
    eventProvider: {
      getForceDisplayEventId: () => ...,
      setForceDisplayEventId: (id) => ...
    }
  });
  ```

## Error Handling

**Strategy:** Comprehensive try-catch with user-friendly error messages

**Patterns:**
- **Network errors:** Wrapped in try-catch with specific error type detection
  ```javascript
  try {
      response = await fetch(url, { signal: controller.signal });
  } catch (fetchError) {
      if (fetchError.name === 'AbortError') {
          throw new Error(`Request timed out after ${timeout/1000} seconds...`);
      } else if (fetchError.message.includes('Failed to fetch')) {
          throw new Error('Unable to connect to the server...');
      }
  }
  ```

- **HTTP status handling:** Check `response.ok`, then handle specific status codes (404, 500, etc.)
  ```javascript
  if (!response.ok) {
      if (response.status === 404) {
          throw new Error(`Data file not found (404)...`);
      } else if (response.status === 500) {
          throw new Error(`Server error (500)...`);
      }
  }
  ```

- **Parsing errors:** Catch and rethrow with context
  ```javascript
  try {
      data = await response.json();
  } catch (parseError) {
      throw new Error(`Invalid data format received from server...`);
  }
  ```

- **Silent failures with warnings:** Some areas use `console.warn` rather than throwing
  ```javascript
  catch (e) {
      console.warn(`Could not parse occurrences for event "${rawEvent.name}":`, ...);
  }
  ```

- **DOM operations:** Try-catch used in state cleanup
  ```javascript
  try {
      state.datePickerInstance.destroy();
  } catch (error) {
      console.warn('Failed to destroy Flatpickr instance:', error);
  }
  ```

## Logging

**Framework:** Native `console` object (no custom logging library)

**Levels used:**
- **console.error():** Network failures, critical errors
- **console.warn():** Non-critical failures, data parsing issues, library cleanup failures
- **console.log():** Not observed in production code (no verbose logging)

**Patterns:**
- **Error context:** Include context about what failed
  ```javascript
  console.error(`Failed to fetch data from ${url}:`, error);
  console.warn(`Could not parse occurrences for event "${rawEvent.name}":`, occurrencesJson, e);
  ```

- **Developer warnings:** Alert developers to invalid data or edge cases
  ```javascript
  console.warn("Utils.formatDateForDisplay received an invalid timestamp:", timestamp);
  ```

## Comments

**When to Comment:**
- **Module headers:** Every module starts with JSDoc block describing purpose
- **Complex sections:** Groups of related functions preceded by section comment header
- **Data transformations:** Complex logic steps explained inline
- **Edge cases:** Special handling documented (e.g., early morning cutoff for overnight events)

**JSDoc/TSDoc:**
- **Function documentation:** JSDoc blocks on all public functions
  ```javascript
  /**
   * Fetches data from the specified URL with comprehensive error handling
   * @param {string} url - The URL to fetch data from
   * @param {number} timeout - Timeout in milliseconds (default: 10000ms)
   * @returns {Promise<Object>} The parsed JSON data
   * @throws {Error} Network, timeout, or parsing errors with user-friendly messages
   */
  async function fetchData(url, timeout = 10000) { ... }
  ```

- **Parameter types:** Always documented (e.g., `@param {Date}`, `@param {Object}`, `@param {Function}`)
- **Return values:** Documented with type and description (e.g., `@returns {boolean}`)
- **Module-level JSDoc:** Each module has top-level comment block with purpose
  ```javascript
  /**
   * DataManager Module
   *
   * Manages data fetching, processing, and indexing for events and locations.
   * Handles initial and full dataset loading, event filtering, and tag management.
   *
   * @module DataManager
   */
  ```

- **State documentation:** Complex state objects documented inline
  ```javascript
  /**
   * Application state object
   * @type {Object}
   * @property {maplibregl.Map|null} map - MapLibre map instance
   * @property {boolean} debugMode - Debug mode toggle state
   */
  state: { ... }
  ```

- **Enum/Constant documentation:** Constants documented with purpose
  ```javascript
  /**
   * Available states for tag filters
   * @enum {string}
   */
  const TAG_STATE = {
      UNSELECTED: 'unselected',
      SELECTED: 'selected'
  };
  ```

## Function Design

**Size:** Functions are kept focused and relatively small (typically 10-50 lines)

**Parameters:**
- **Explicit dependencies:** Functions receive objects/state needed as parameters (e.g., `state`, `config`, `elements`)
- **Callbacks grouped:** Related callbacks passed as object literal
  ```javascript
  callbacks = {
      onDatePickerClose: (dates) => { ... },
      onFilterChange: (tagStates) => { ... }
  }
  ```

- **Provider objects:** Used for batch parameter passing
  ```javascript
  filterProvider = {
      getTagStates: () => { ... },
      getSelectedDates: () => { ... }
  }
  ```

**Return Values:**
- **Explicit returns:** Functions return single values or objects
- **Void functions:** Used for state mutation and setup
- **Callbacks as returns:** Some utility functions return closures (e.g., debounce, throttle)
  ```javascript
  function debounce(func, wait) {
      return function debounced(...args) { ... };
  }
  ```

## Module Design

**Exports:**
- **Named exports:** Each module exports specific public methods/functions as object literal
- **All private by default:** Functions not in return statement are private (scope closure)
- **Consistent export pattern:** Every module returns an object with named public functions

**Barrel Files:**
- **Not used:** No index.js re-export pattern
- **Direct imports:** Code accesses modules directly by name (e.g., `DataManager.fetchData()`)

**Module interdependencies:**
- **Minimal coupling:** Modules pass dependencies as parameters rather than accessing globals
- **Late binding:** References to other modules resolved at init time, not at load time
- **Provider pattern:** Preferred for complex dependencies

---

*Convention analysis: 2026-02-24*
