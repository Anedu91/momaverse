# Testing Patterns

**Analysis Date:** 2026-02-24

## Test Framework

**Status:** No testing framework configured

**Observations:**
- No `jest.config.js`, `vitest.config.ts`, or similar test configuration files
- No test dependencies in `package.json` (only esbuild and flatpickr)
- No test files found (`*.test.js`, `*.spec.js`, `*.test.ts`, `*.spec.ts`)
- No automated testing infrastructure

**Current approach:** Manual testing only

## Manual Testing Strategy

**Observed patterns:**
- **console output:** Application logs errors and warnings to browser console for debugging
- **Visual verification:** UI changes verified through browser inspection
- **Error messages:** User-friendly error messages displayed via `ToastNotifier` module for user feedback
- **Debug mode:** Built-in debug mode (referenced in `script.js` as `App.state.debugMode`) for developer verification

## Build and Runtime Testing

**Build verification:**
- **Concatenation validation:** Build script (`build.js`) parses HTML to verify all JS files are included in load order
- **Error on missing files:** Build throws error if no JS files found in index.html
  ```javascript
  if (jsFiles.length === 0) {
      throw new Error('No JS files found in index.html');
  }
  ```

**Runtime verification:**
- **Data validation:** DataManager includes comprehensive data fetching and parsing error handling
- **Network resilience:** Timeout handling, specific error type detection, user-friendly messages
- **Data integrity checks:** Location key validation, occurrence parsing with fallback handling

## Error Handling as Testing

**Pattern:** Error handling code serves as runtime validation

**Examples from codebase:**

**1. Network Error Testing (in DataManager.fetchData):**
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

// HTTP status validation
if (!response.ok) {
    if (response.status === 404) {
        throw new Error(`Data file not found (404)...`);
    } else if (response.status === 500) {
        throw new Error(`Server error (500)...`);
    }
}

// Parse validation
try {
    data = await response.json();
} catch (parseError) {
    throw new Error(`Invalid data format received...`);
}
```

**2. Data Processing Validation (in DataManager.parseOccurrences):**
```javascript
try {
    const start = Utils.parseDateInNewYork(startDateStr, startTimeStr);
    const end = Utils.parseDateInNewYork(effectiveEndDateStr, effectiveEndTimeStr);
    return { start, end, originalStartTime: startTimeStr, originalEndTime: endTimeStr };
} catch (e) {
    console.warn(`Could not parse occurrences for event "${rawEvent.name}":`,
                 occurrencesJson, e);
    // Return fallback
    return [];
}
```

**3. Date Validation (in Utils.formatDateForDisplay):**
```javascript
const date = new Date(Number(timestamp));
if (isNaN(date.getTime())) {
    console.warn("Utils.formatDateForDisplay received an invalid timestamp:", timestamp);
    return "Invalid Date";
}
```

**4. Type Checking (in Utils.escapeHtml):**
```javascript
function escapeHtml(unsafe) {
    if (typeof unsafe !== 'string') return '';
    return unsafe.replace(/&/g, "&amp;").replace(/</g, "&lt;")...
}
```

**5. DOM Cleanup Testing (in UIManager.destroyDatePicker):**
```javascript
try {
    state.datePickerInstance.destroy();
} catch (error) {
    console.warn('Failed to destroy Flatpickr instance:', error);
}
state.datePickerInstance = null;
```

## Debugging Features

**Debug Mode:**
- **Reference:** `App.state.debugMode` in `script.js`
- **Purpose:** Enables debug visualization
- **Container:** `App.state.debugContainer` for debug output

**Console Logging:**
- **Error logging:** Errors logged with context
- **Warning logging:** Non-critical issues logged for developer awareness
- **Pattern:** Module name included in log messages for traceability

## Code Coverage

**Current status:** Not measured or enforced

**Gap:** No integration testing to validate:
- Module initialization order
- Provider pattern implementations
- Cross-module state synchronization
- Event listener attachment and cleanup
- Map/DOM rendering coordination

## Testing Recommendations for Future Implementation

**Unit Testing:**
- **Target modules:** Utility functions (`Utils.debounce`, `Utils.formatDate*`, `Utils.calculateDistance`)
- **Data processing:** DataManager functions for event/location processing
- **State management:** TagStateManager state transitions
- **Calculations:** FilterManager date range logic, proximity calculations

**Integration Testing:**
- **Module initialization:** Verify modules initialize with correct provider patterns
- **State synchronization:** Verify state changes propagate through dependent modules
- **Data pipeline:** Full event data load → filter → display flow

**E2E Testing:**
- **User workflows:** Date selection → filtered results
- **Tag filtering:** Tag selection → result updates
- **Map interaction:** Viewport changes → marker visibility updates
- **Theme switching:** Dark/light toggle with map layer updates

**Suggested framework:** Jest (matches project simplicity and ES6 syntax)

**Suggested approach:**
1. Start with unit tests for pure functions (Utils, Constants)
2. Add integration tests for module initialization and provider patterns
3. Add E2E tests for critical user workflows using Playwright/Cypress

---

*Testing analysis: 2026-02-24*
