-- Seed: Centros Culturales de Buenos Aires
-- Source: Major government and independent cultural centers in CABA
-- 9 cultural centers

USE fomo;

-- ============================================================================
-- LOCATIONS (9 cultural centers)
-- ============================================================================

INSERT INTO locations (name, short_name, very_short_name, address, description, lat, lng, emoji) VALUES
('Centro Cultural Kirchner', 'CCK', 'CCK', 'Sarmiento 151, CABA', 'Centro cultural en el antiguo Palacio de Correos. Salas de concierto, galerias y espacios de exposicion. Uno de los centros culturales mas grandes de Latinoamerica.', -34.604600, -58.369500, '🏛️'),
('Centro Cultural Recoleta', 'CC Recoleta', 'CCR', 'Junin 1930, CABA', 'Centro cultural ubicado junto al Cementerio de la Recoleta. Salas de exposicion, auditorio y espacio para artes visuales y escenicas.', -34.587000, -58.392700, '🏛️'),
('Usina del Arte', 'Usina del Arte', 'Usina', 'Av. Pedro de Mendoza 501, CABA', 'Centro cultural en una antigua usina electrica en La Boca. Sala sinfonica, galerias y espacio para festivales.', -34.636900, -58.352800, '🏛️'),
('Centro Cultural San Martin', 'CC San Martin', 'CCSM', 'Sarmiento 1551, CABA', 'Centro cultural del Gobierno de la Ciudad. Salas de teatro, cine, exposiciones y talleres.', -34.604300, -58.388900, '🏛️'),
('La Rural - Predio Ferial', 'La Rural', 'Rural', 'Av. Sarmiento 2704, CABA', 'Predio ferial y centro de exposiciones en Palermo. Sede de arteBA y otros eventos culturales y comerciales.', -34.578000, -58.419900, '🎪'),
('Centro Cultural de la Memoria Haroldo Conti', 'CC Conti', 'Conti', 'Av. del Libertador 8151, CABA', 'Centro cultural dedicado a la memoria, los derechos humanos y la cultura. Ubicado en el ex ESMA.', -34.543800, -58.463400, '🏛️'),
('Parque de la Memoria', 'Parque Memoria', 'PMemoria', 'Av. Costanera Norte R. Obligado 6745, CABA', 'Monumento a las victimas del terrorismo de Estado. Esculturas al aire libre y sala de exposiciones PAyS.', -34.540700, -58.448100, '🏛️'),
('Proa21', 'Proa21', 'Proa21', 'Av. Pedro de Mendoza 2073, CABA', 'Espacio de arte contemporaneo de Fundacion Proa enfocado en nuevos medios y arte digital. Ubicado en La Boca.', -34.639100, -58.361300, '🎨'),
('Palais de Glace', 'Palais de Glace', 'Palais', 'Posadas 1725, CABA', 'Palacio Nacional de las Artes. Sede de salones nacionales y exposiciones de artes visuales.', -34.586600, -58.393500, '🏛️');

-- ============================================================================
-- LOCATION ALTERNATE NAMES
-- ============================================================================

SET @cck_id = (SELECT id FROM locations WHERE name = 'Centro Cultural Kirchner' LIMIT 1);
INSERT INTO location_alternate_names (location_id, alternate_name) VALUES
(@cck_id, 'CCK'),
(@cck_id, 'Kirchner Cultural Centre');

SET @ccr_id = (SELECT id FROM locations WHERE name = 'Centro Cultural Recoleta' LIMIT 1);
INSERT INTO location_alternate_names (location_id, alternate_name) VALUES
(@ccr_id, 'CCR'),
(@ccr_id, 'Centro Cultural de la Recoleta');

SET @ccsm_id = (SELECT id FROM locations WHERE name = 'Centro Cultural San Martin' LIMIT 1);
INSERT INTO location_alternate_names (location_id, alternate_name) VALUES
(@ccsm_id, 'CCSM');

SET @conti_id = (SELECT id FROM locations WHERE name = 'Centro Cultural de la Memoria Haroldo Conti' LIMIT 1);
INSERT INTO location_alternate_names (location_id, alternate_name) VALUES
(@conti_id, 'Centro Cultural Conti'),
(@conti_id, 'Conti');

SET @palais_id = (SELECT id FROM locations WHERE name = 'Palais de Glace' LIMIT 1);
INSERT INTO location_alternate_names (location_id, alternate_name) VALUES
(@palais_id, 'Palacio Nacional de las Artes');
