-- Seed: Teatros de Buenos Aires (fuera del CTBA)
-- Source: Major theaters in CABA not part of Complejo Teatral de Buenos Aires
-- 10 theaters

USE fomo;

-- ============================================================================
-- LOCATIONS (10 theaters)
-- ============================================================================

INSERT INTO locations (name, short_name, very_short_name, address, description, lat, lng, emoji) VALUES
('Teatro Colon', 'Colon', 'Colon', 'Cerrito 628, CABA', 'Teatro de opera y ballet de fama mundial. Considerado uno de los mejores teatros liricos del mundo por su acustica.', -34.601100, -58.383000, '🎭'),
('Teatro Metropolitan', 'Metropolitan', 'Metro', 'Av. Corrientes 1343, CABA', 'Teatro de gran capacidad sobre Av. Corrientes. Musicales, conciertos y espectaculos de gran formato.', -34.604200, -58.386500, '🎭'),
('Teatro Gran Rex', 'Gran Rex', 'GRex', 'Av. Corrientes 857, CABA', 'Mitico teatro de Av. Corrientes. Conciertos, festivales y espectaculos de primer nivel desde 1937.', -34.604300, -58.381200, '🎭'),
('Teatro Maipo', 'Maipo', 'Maipo', 'Esmeralda 443, CABA', 'Teatro historico de revista y variedades. Icono de la cultura portena desde 1908.', -34.603300, -58.378400, '🎭'),
('Teatro Nacional Cervantes', 'Cervantes', 'Cervantes', 'Libertad 815, CABA', 'Teatro Nacional de Argentina. Programacion de teatro, danza y musica. Edificio historico de estilo espanol.', -34.599700, -58.385200, '🎭'),
('Teatro Opera', 'Opera', 'Opera', 'Av. Corrientes 860, CABA', 'Gran teatro sobre Av. Corrientes. Conciertos, musicales y espectaculos de gran escala.', -34.604200, -58.381300, '🎭'),
('Teatro El Picadero', 'El Picadero', 'Picadero', 'Pasaje Enrique Santos Discepolo 1857, CABA', 'Teatro emblematico del circuito independiente porteno. Espacio mitico de la historia del teatro argentino.', -34.602900, -58.397700, '🎭'),
('Teatro Astral', 'Astral', 'Astral', 'Av. Corrientes 1639, CABA', 'Teatro clasico de Av. Corrientes. Obras de teatro, comedia y espectaculos variados.', -34.603900, -58.389400, '🎭'),
('Teatro Astros', 'Astros', 'Astros', 'Av. Corrientes 746, CABA', 'Teatro sobre Av. Corrientes con programacion variada de teatro y espectaculos.', -34.604700, -58.380200, '🎭'),
('Ciudad Cultural Konex', 'Konex', 'Konex', 'Sarmiento 3131, CABA', 'Centro cultural multidisciplinario en Abasto. Musica, teatro, danza, cine y artes visuales. Sede de La Bomba de Tiempo.', -34.603200, -58.412100, '🎭');

-- ============================================================================
-- LOCATION ALTERNATE NAMES
-- ============================================================================

SET @colon_id = (SELECT id FROM locations WHERE name = 'Teatro Colon' LIMIT 1);
INSERT INTO location_alternate_names (location_id, alternate_name) VALUES
(@colon_id, 'Teatro Colon de Buenos Aires'),
(@colon_id, 'Colon');

SET @konex_id = (SELECT id FROM locations WHERE name = 'Ciudad Cultural Konex' LIMIT 1);
INSERT INTO location_alternate_names (location_id, alternate_name) VALUES
(@konex_id, 'Konex'),
(@konex_id, 'Ciudad Cultural Konex');

SET @cervantes_id = (SELECT id FROM locations WHERE name = 'Teatro Nacional Cervantes' LIMIT 1);
INSERT INTO location_alternate_names (location_id, alternate_name) VALUES
(@cervantes_id, 'Cervantes');

SET @metropolitan_id = (SELECT id FROM locations WHERE name = 'Teatro Metropolitan' LIMIT 1);
INSERT INTO location_alternate_names (location_id, alternate_name) VALUES
(@metropolitan_id, 'Teatro Metropolitan Citi');
