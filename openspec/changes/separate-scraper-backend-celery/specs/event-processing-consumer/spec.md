## ADDED Requirements

### Requirement: Process crawl job task
The system SHALL define a Celery task `process_crawl_job(job_id)` that processes all extracted events from a completed crawl job. This task runs on the `default` queue.

#### Scenario: Successful crawl job processing
- **WHEN** the `process_crawl_job` task receives a `job_id`
- **THEN** it fetches all `ExtractedEvent` rows linked to that job's `CrawlResult` entries with status `extracted`
- **THEN** it runs event processing (location resolution, tag processing, short_name, emoji) on each event
- **THEN** it runs deduplication and merging against existing events
- **THEN** it updates `CrawlResult` status to `processed` for each completed source
- **THEN** it logs results to `ExtractedEventLog`

#### Scenario: Crawl job with no extracted events
- **WHEN** the `process_crawl_job` task receives a `job_id` with no extracted events
- **THEN** it completes successfully without errors and logs a warning

#### Scenario: Partial failure within a crawl job
- **WHEN** processing fails for one source's events within a job
- **THEN** that source's `CrawlResult` is marked as `failed` with error details
- **THEN** other sources in the same job continue processing normally

### Requirement: Location resolution service
The system SHALL resolve location names from extracted events to existing `Location` records or create new ones. This logic MUST use SQLAlchemy async (not psycopg2).

#### Scenario: Location name matches existing location
- **WHEN** an extracted event's `location_name` matches an existing location (normalized comparison)
- **THEN** the event's `location_id` is set to the matched location's ID

#### Scenario: Location name has no match
- **WHEN** an extracted event's `location_name` does not match any existing location
- **THEN** a new `Location` record is created with the raw name
- **THEN** a `geocode_location` Celery task is queued for the new location (non-blocking)

#### Scenario: Extracted event has no location name
- **WHEN** an extracted event has a null or empty `location_name`
- **THEN** the event is logged as `skipped_no_location` in `ExtractedEventLog`

### Requirement: Tag processing service
The system SHALL apply tag rewrite rules, exclusion rules, and removal rules to extracted event tags. This replaces the tag processing logic from `pipeline/processor.py`.

#### Scenario: Tag rewrite rule matches
- **WHEN** an extracted event has a tag matching a rewrite rule pattern
- **THEN** the tag is replaced with the rewrite rule's replacement value

#### Scenario: Tag exclusion rule matches
- **WHEN** an extracted event has a tag matching an exclusion pattern
- **THEN** that tag is removed from the event's tag list

#### Scenario: Tag removal rule matches
- **WHEN** an extracted event has a tag matching a removal rule
- **THEN** the entire event is skipped and logged as `skipped_tag_removed`

### Requirement: Event deduplication service
The system SHALL deduplicate extracted events against existing events using the 7-strategy matching from `pipeline/merger.py`, converted to SQLAlchemy async.

#### Scenario: Extracted event matches existing event
- **WHEN** an extracted event matches an existing event by location + name similarity + date overlap
- **THEN** the existing event is updated (merge URLs, update description if longer, merge occurrences)
- **THEN** an `EventSource` link is created between the extracted event and the existing event

#### Scenario: Extracted event is new
- **WHEN** an extracted event does not match any existing event
- **THEN** a new `Event` record is created with associated `EventOccurrence`, `EventUrl`, and `EventTag` records
- **THEN** an `EventSource` link is created

#### Scenario: Duplicate extracted events within same crawl
- **WHEN** multiple extracted events from the same crawl match the same existing event
- **THEN** they are merged into a single update (not multiple conflicting updates)

### Requirement: Event archiving service
The system SHALL archive events whose sources no longer report them, with a grace period for events with future occurrences.

#### Scenario: Event no longer reported by any source
- **WHEN** all sources that previously reported an event have newer crawls without it
- **THEN** the event is archived (status set to `archived`)

#### Scenario: Event with future occurrences
- **WHEN** an event would be archived but has occurrences in the future
- **THEN** archiving is deferred for 14 days (grace period)

### Requirement: Audit logging
The system SHALL log all processing outcomes to `ExtractedEventLog` for every extracted event processed.

#### Scenario: Event successfully created or merged
- **WHEN** an extracted event is processed into a final event
- **THEN** an `ExtractedEventLog` entry is created with status `created` or `merged` and the target `event_id`

#### Scenario: Event skipped
- **WHEN** an extracted event is skipped (no location, no occurrences, tag removal)
- **THEN** an `ExtractedEventLog` entry is created with the appropriate skip reason
