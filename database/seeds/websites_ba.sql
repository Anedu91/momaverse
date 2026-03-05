-- Seed: Buenos Aires Event Source Websites
-- 4 Argentine event sources for pipeline crawling
-- Sources: Alternativa Teatral, Plateanet, Teatro El Picadero, Microteatro

USE fomo;

-- ============================================================================
-- 1. ALTERNATIVA TEATRAL (aggregator)
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
    'aggregator',
    FALSE
);

SET @alternativa_id = (SELECT id FROM websites WHERE name = 'Alternativa Teatral' LIMIT 1);

INSERT INTO website_urls (website_id, url, sort_order) VALUES
(@alternativa_id, 'https://www.alternativateatral.com/cartelera.asp', 1);

INSERT INTO website_tags (website_id, tag) VALUES
(@alternativa_id, 'Theater');

-- ============================================================================
-- 2. PLATEANET (aggregator)
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
    'aggregator',
    FALSE
);

SET @plateanet_id = (SELECT id FROM websites WHERE name = 'Plateanet' LIMIT 1);

INSERT INTO website_urls (website_id, url, sort_order) VALUES
(@plateanet_id, 'https://www.plateanet.com/', 1);

INSERT INTO website_tags (website_id, tag) VALUES
(@plateanet_id, 'Show');

-- ============================================================================
-- 3. TEATRO EL PICADERO (primary)
-- Venue page with current shows
-- Links to Phase 2 location: "Teatro El Picadero" in teatros_ba.sql
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

SET @picadero_web_id = (SELECT id FROM websites WHERE name = 'Teatro El Picadero' LIMIT 1);

INSERT INTO website_urls (website_id, url, sort_order) VALUES
(@picadero_web_id, 'https://www.teatropicadero.com.ar/obras', 1);

-- Link to Phase 2 location
SET @picadero_loc_id = (SELECT id FROM locations WHERE name = 'Teatro El Picadero' LIMIT 1);
INSERT INTO website_locations (website_id, location_id)
SELECT @picadero_web_id, @picadero_loc_id
FROM DUAL WHERE @picadero_loc_id IS NOT NULL;

INSERT INTO website_tags (website_id, tag) VALUES
(@picadero_web_id, 'Theater');

-- ============================================================================
-- 4. MICROTEATRO (primary)
-- Venue with short-form theater
-- No matching Phase 2 location found in seeds
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

SET @microteatro_id = (SELECT id FROM websites WHERE name = 'Microteatro Buenos Aires' LIMIT 1);

INSERT INTO website_urls (website_id, url, sort_order) VALUES
(@microteatro_id, 'https://www.microteatro.com.ar/', 1);

INSERT INTO website_tags (website_id, tag) VALUES
(@microteatro_id, 'Theater');
