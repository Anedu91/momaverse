---
status: testing
phase: 02-buenos-aires-locations
source: 02-01-SUMMARY.md
started: 2026-03-05T05:00:00Z
updated: 2026-03-05T05:00:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 1
name: geocode.php references Buenos Aires
expected: |
  Run `php scripts/geocode.php --help` — help text should reference Buenos Aires (not NYC).
  Grep: `grep -c 'NYC' scripts/geocode.php` should return 0.
  Grep: `grep 'BA_BOUNDS' scripts/geocode.php` should show the BA bounding box constant.
awaiting: user response

## Tests

### 1. geocode.php references Buenos Aires
expected: Running `php scripts/geocode.php --help` shows Buenos Aires in help text. No NYC references remain. BA_BOUNDS constant is defined with coordinates -34.75,-58.60|-34.50,-58.28.
result: [pending]

### 2. Seed SQL files execute without errors
expected: Running each seed file against the database succeeds. Execute in order: `mysql -u root fomo < database/seeds/museos_ba.sql`, then centros_culturales_ba.sql, galerias_y_espacios_ba.sql, teatros_ba.sql. All INSERT statements complete without errors.
result: [pending]

### 3. Venue count and categories
expected: After running all seeds (including existing complejo_teatral_ba.sql), `SELECT COUNT(*) FROM locations` returns approximately 46 rows. Venues span museums, cultural centers, galleries, and theaters.
result: [pending]

### 4. Coordinates within Buenos Aires bounds
expected: Running `SELECT name, lat, lng FROM locations WHERE lat < -34.75 OR lat > -34.50 OR lng < -58.60 OR lng > -58.28` returns zero rows — all venues are within CITY_BOUNDS.
result: [pending]

### 5. Alternate names linked correctly
expected: Running `SELECT l.name, la.alternate_name FROM location_alternate_names la JOIN locations l ON l.id = la.location_id` shows alternate names for key venues (e.g., MALBA has full name, CCK has full name, etc.).
result: [pending]

### 6. Venue markers appear at correct positions on map
expected: After running the pipeline exporter (`cd pipeline && python exporter.py`) and loading the app, venue markers appear on the Buenos Aires map. Clicking a marker (e.g., MALBA, Teatro Colon) shows it at the correct real-world position — not in the river, wrong barrio, or off by blocks.
result: [pending]

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0

## Gaps

[none yet]
