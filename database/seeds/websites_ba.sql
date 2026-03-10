-- Seed: Buenos Aires Event Source Websites
-- 4 Argentine event sources for pipeline crawling
-- Sources: Alternativa Teatral, Plateanet, Teatro El Picadero, Microteatro

-- ============================================================================
-- 1. ALTERNATIVA TEATRAL (primary)
-- Biggest theater aggregator in Buenos Aires
-- NOTE: Heavy JS / infinite scroll. Basic HTML crawl may extract partial data.
--       Has a JSON API endpoint but response too large for token limits.
--       Complex API/JSON crawling deferred to future phase.
-- ============================================================================

INSERT INTO websites (name, description, base_url, crawl_frequency, notes, source_type, disabled)
VALUES (
    'Alternativa Teatral',
    'Mayor agregador de teatro y artes escenicas en Buenos Aires. Cartelera completa de obras.',
    'https://www.alternativateatral.com',
    3,
    'Events are in Spanish. Dates may use DD/MM/YYYY format. Heavy JavaScript with infinite scroll. Basic HTML crawl may only extract partial event listings. JSON API endpoint exists but response is too large for token limits -- complex API crawling deferred to future phase.',
    'primary',
    FALSE
);

INSERT INTO website_urls (website_id, url, sort_order) VALUES
((SELECT id FROM websites WHERE name = 'Alternativa Teatral' LIMIT 1), 'https://www.alternativateatral.com/cartelera.asp', 1);

INSERT INTO website_tags (website_id, tag) VALUES
((SELECT id FROM websites WHERE name = 'Alternativa Teatral' LIMIT 1), 'Theater');

-- ============================================================================
-- 2. PLATEANET (primary)
-- Ticketing/event platform
-- NOTE: May experience geo-blocking from non-Argentine IPs.
-- ============================================================================

INSERT INTO websites (name, description, base_url, crawl_frequency, notes, source_type, disabled)
VALUES (
    'Plateanet',
    'Plataforma de venta de entradas y listado de eventos en Buenos Aires.',
    'https://www.plateanet.com',
    3,
    'Events are in Spanish. Dates may use DD/MM/YYYY format. May not work from non-Argentine IPs (potential geo-blocking from Indonesian server). If crawl fails, consider using a proxy or VPN.',
    'primary',
    FALSE
);

INSERT INTO website_urls (website_id, url, sort_order) VALUES
((SELECT id FROM websites WHERE name = 'Plateanet' LIMIT 1), 'https://www.plateanet.com/', 1);

INSERT INTO website_tags (website_id, tag) VALUES
((SELECT id FROM websites WHERE name = 'Plateanet' LIMIT 1), 'Show');

-- ============================================================================
-- 3. TEATRO EL PICADERO (primary)
-- Venue page with current shows
-- Links to location: "Teatro El Picadero" in teatros_ba.sql
-- ============================================================================

INSERT INTO websites (name, description, base_url, crawl_frequency, notes, source_type, disabled)
VALUES (
    'Teatro El Picadero',
    'Teatro emblematico del circuito independiente porteno. Pagina de obras en cartel.',
    'https://www.teatropicadero.com.ar',
    3,
    'Events are in Spanish. Dates may use DD/MM/YYYY format. Venue page listing current shows.',
    'primary',
    FALSE
);

INSERT INTO website_urls (website_id, url, sort_order) VALUES
((SELECT id FROM websites WHERE name = 'Teatro El Picadero' LIMIT 1), 'https://www.teatropicadero.com.ar/obras', 1);

-- Link to location (only if it exists)
INSERT INTO website_locations (website_id, location_id)
SELECT
    (SELECT id FROM websites WHERE name = 'Teatro El Picadero' LIMIT 1),
    id
FROM locations WHERE name = 'Teatro El Picadero' LIMIT 1;

INSERT INTO website_tags (website_id, tag) VALUES
((SELECT id FROM websites WHERE name = 'Teatro El Picadero' LIMIT 1), 'Theater');

-- ============================================================================
-- 4. MICROTEATRO (primary)
-- Venue with short-form theater
-- ============================================================================

INSERT INTO websites (name, description, base_url, crawl_frequency, notes, source_type, disabled)
VALUES (
    'Microteatro Buenos Aires',
    'Espacio de microteatro con obras cortas e intimas. Formato unico de teatro breve.',
    'https://www.microteatro.com.ar',
    3,
    'Events are in Spanish. Dates may use DD/MM/YYYY format. Short-form theater venue.',
    'primary',
    FALSE
);

INSERT INTO website_urls (website_id, url, sort_order) VALUES
((SELECT id FROM websites WHERE name = 'Microteatro Buenos Aires' LIMIT 1), 'https://www.microteatro.com.ar/', 1);

INSERT INTO website_tags (website_id, tag) VALUES
((SELECT id FROM websites WHERE name = 'Microteatro Buenos Aires' LIMIT 1), 'Theater');

-- ============================================================================
-- Configure Alternativa Teatral for JSON API crawling
-- Uses JSONP endpoint instead of browser crawl (infinite scroll fails)
-- ============================================================================

UPDATE websites
SET crawl_mode = 'json_api',
    json_api_config = '{"jsonp_callback": "jsoncallback", "data_path": "espectaculos", "fields_include": ["titulo", "clasificaciones", "lugares", "url", "url_entradas"], "date_window_days": 30, "base_url": "https://www.alternativateatral.com/get-json.php?t=novedades&r=cartelera"}'::jsonb
WHERE name = 'Alternativa Teatral';
