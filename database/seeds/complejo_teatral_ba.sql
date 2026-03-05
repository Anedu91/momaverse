-- Seed: Complejo Teatral de Buenos Aires (CTBA)
-- Source: https://complejoteatral.gob.ar
-- 6 theaters, 1 website with 6 crawl URLs

USE fomo;

-- ============================================================================
-- LOCATIONS (6 theaters)
-- ============================================================================

INSERT INTO locations (name, short_name, very_short_name, address, description, lat, lng, emoji) VALUES
('Teatro San Martín', 'San Martín', 'TSM', 'Av. Corrientes 1530, CABA', 'Teatro principal del Complejo Teatral de Buenos Aires. Tres salas: Martín Coronado, Cunill Cabanellas y Leopoldo Lugones.', -34.604330, -58.388010, '🎭'),
('Teatro Presidente Alvear', 'T. Alvear', 'Alvear', 'Av. Corrientes 1659, CABA', 'Teatro del Complejo Teatral de Buenos Aires sobre Av. Corrientes.', -34.603960, -58.389420, '🎭'),
('Teatro Regio', 'T. Regio', 'Regio', 'Av. Córdoba 6056, CABA', 'Teatro del Complejo Teatral de Buenos Aires en el barrio de Chacarita.', -34.573950, -58.440520, '🎭'),
('Teatro de la Ribera', 'T. Ribera', 'Ribera', 'Av. Pedro de Mendoza 1821, CABA', 'Teatro del Complejo Teatral de Buenos Aires en La Boca, frente al Riachuelo.', -34.638420, -58.363340, '🎭'),
('Teatro Sarmiento', 'T. Sarmiento', 'Sarmiento', 'Av. Sarmiento 2715, CABA', 'Teatro del Complejo Teatral de Buenos Aires dedicado a la exploración y nuevas formas escénicas.', -34.579550, -58.416700, '🎭'),
('Cine Teatro El Plata', 'El Plata', 'Plata', 'Av. Juan Bautista Alberdi 5765, CABA', 'Cine teatro del Complejo Teatral de Buenos Aires en Mataderos.', -34.637020, -58.472760, '🎬');

-- ============================================================================
-- LOCATION ALTERNATE NAMES (sub-rooms within Teatro San Martín)
-- ============================================================================

-- Get Teatro San Martín ID dynamically
SET @tsm_id = (SELECT id FROM locations WHERE name = 'Teatro San Martín' AND address LIKE '%Corrientes 1530%' LIMIT 1);

INSERT INTO location_alternate_names (location_id, alternate_name) VALUES
(@tsm_id, 'Sala Martín Coronado'),
(@tsm_id, 'Sala Cunill Cabanellas'),
(@tsm_id, 'Sala Leopoldo Lugones'),
(@tsm_id, 'FotoGalería Sara Facio'),
(@tsm_id, 'Anfiteatro del Parque Centenario');

-- ============================================================================
-- WEBSITE
-- ============================================================================

INSERT INTO websites (
    name, description, base_url,
    crawl_frequency, keywords, max_pages,
    source_type, javascript_enabled,
    delay_before_return_html, scan_full_page
) VALUES (
    'Complejo Teatral de Buenos Aires',
    'Complejo de 6 teatros públicos de la Ciudad de Buenos Aires: San Martín, Alvear, Regio, Ribera, Sarmiento y El Plata. Teatro, danza, música, cine, títeres.',
    'https://complejoteatral.gob.ar',
    7,         -- weekly crawl
    'ver',     -- URL filter: show detail pages follow /ver/{slug}
    30,        -- max pages
    'primary',
    1,         -- javascript_enabled (SPA site)
    5,         -- delay_before_return_html (seconds)
    1          -- scan_full_page
);

SET @ctba_id = LAST_INSERT_ID();

-- ============================================================================
-- WEBSITE URLS (one per theater programming page)
-- ============================================================================

INSERT INTO website_urls (website_id, url, sort_order) VALUES
(@ctba_id, 'https://complejoteatral.gob.ar/teatro-san-martin', 1),
(@ctba_id, 'https://complejoteatral.gob.ar/teatro-presidente-alvear', 2),
(@ctba_id, 'https://complejoteatral.gob.ar/teatro-regio', 3),
(@ctba_id, 'https://complejoteatral.gob.ar/teatro-de-la-ribera', 4),
(@ctba_id, 'https://complejoteatral.gob.ar/teatro-sarmiento', 5),
(@ctba_id, 'https://complejoteatral.gob.ar/cine-teatro-el-plata', 6);

-- ============================================================================
-- WEBSITE <-> LOCATION LINKS
-- ============================================================================

INSERT INTO website_locations (website_id, location_id)
SELECT @ctba_id, id FROM locations
WHERE name IN (
    'Teatro San Martín',
    'Teatro Presidente Alvear',
    'Teatro Regio',
    'Teatro de la Ribera',
    'Teatro Sarmiento',
    'Cine Teatro El Plata'
)
AND address LIKE '%CABA%';

-- ============================================================================
-- WEBSITE TAGS
-- ============================================================================

INSERT INTO website_tags (website_id, tag) VALUES
(@ctba_id, 'teatro'),
(@ctba_id, 'danza'),
(@ctba_id, 'música'),
(@ctba_id, 'cine'),
(@ctba_id, 'gobierno');

-- ============================================================================
-- INSTAGRAM
-- ============================================================================

INSERT INTO instagram_accounts (handle, name, description) VALUES
('complejoteatralba', 'Complejo Teatral de Buenos Aires', 'Cuenta oficial del CTBA');

SET @ig_id = LAST_INSERT_ID();

-- Link Instagram to website
INSERT INTO website_instagram (website_id, instagram_id) VALUES (@ctba_id, @ig_id);

-- Link Instagram to main theater (Teatro San Martín)
INSERT INTO location_instagram (location_id, instagram_id) VALUES (@tsm_id, @ig_id);
