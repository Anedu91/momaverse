-- Seed: Museos de Buenos Aires
-- Source: Major art museums in Ciudad Autonoma de Buenos Aires
-- 9 museums

USE fomo;

-- ============================================================================
-- LOCATIONS (9 museums)
-- ============================================================================

INSERT INTO locations (name, short_name, very_short_name, address, description, lat, lng, emoji) VALUES
('Museo de Arte Latinoamericano de Buenos Aires', 'MALBA', 'MALBA', 'Av. Pres. Figueroa Alcorta 3415, CABA', 'Museo dedicado al arte latinoamericano desde principios del siglo XX hasta la actualidad. Coleccion permanente y exposiciones temporales.', -34.577400, -58.403900, '🏛️'),
('Museo Nacional de Bellas Artes', 'Bellas Artes', 'MNBA', 'Av. del Libertador 1473, CABA', 'Principal museo de arte de Argentina. Coleccion de arte argentino, latinoamericano y europeo desde la Edad Media hasta el arte contemporaneo.', -34.583600, -58.393500, '🏛️'),
('Museo de Arte Moderno de Buenos Aires', 'Arte Moderno', 'MAMBA', 'Av. San Juan 350, CABA', 'Museo dedicado al arte moderno y contemporaneo argentino e internacional. Ubicado en San Telmo.', -34.622200, -58.370000, '🎨'),
('Museo de Arte Contemporaneo de Buenos Aires', 'MACBA', 'MACBA', 'Av. San Juan 328, CABA', 'Museo enfocado en arte geometrico y cinetico. Coleccion de arte abstracto latinoamericano y europeo.', -34.622000, -58.370500, '🎨'),
('Museo Nacional de Arte Decorativo', 'Arte Decorativo', 'MNAD', 'Av. del Libertador 1902, CABA', 'Museo de artes decorativas en el Palacio Errázuriz-Alvear. Colecciones de mobiliario, escultura y pintura europea.', -34.583100, -58.389000, '🏛️'),
('Museo Evita', 'Museo Evita', 'Evita', 'Lafinur 2988, CABA', 'Museo dedicado a la vida y obra de Eva Peron. Ubicado en un antiguo hogar de transito en Palermo.', -34.579700, -58.411600, '🏛️'),
('Museo Casa Rosada', 'Casa Rosada', 'CRosada', 'Paseo Colon 100, CABA', 'Museo historico ubicado en los subsuelos de la Casa de Gobierno. Arte, objetos y documentos presidenciales.', -34.608300, -58.370200, '🏛️'),
('Museo de Arte Espanol Enrique Larreta', 'Museo Larreta', 'Larreta', 'Av. Juramento 2291, CABA', 'Museo de arte espanol en la casona de Enrique Larreta. Jardin andaluz y coleccion de arte colonial.', -34.559300, -58.456900, '🏛️'),
('Centro Cultural Borges', 'CC Borges', 'Borges', 'Viamonte 525, CABA', 'Centro cultural con salas de exposicion, espectaculos y talleres. Ubicado en Galerias Pacifico.', -34.599200, -58.374700, '🎨');

-- ============================================================================
-- LOCATION ALTERNATE NAMES
-- ============================================================================

SET @malba_id = (SELECT id FROM locations WHERE name = 'Museo de Arte Latinoamericano de Buenos Aires' LIMIT 1);
INSERT INTO location_alternate_names (location_id, alternate_name) VALUES
(@malba_id, 'MALBA');

SET @mnba_id = (SELECT id FROM locations WHERE name = 'Museo Nacional de Bellas Artes' LIMIT 1);
INSERT INTO location_alternate_names (location_id, alternate_name) VALUES
(@mnba_id, 'MNBA');

SET @macba_id = (SELECT id FROM locations WHERE name = 'Museo de Arte Contemporaneo de Buenos Aires' LIMIT 1);
INSERT INTO location_alternate_names (location_id, alternate_name) VALUES
(@macba_id, 'MACBA');

SET @mamba_id = (SELECT id FROM locations WHERE name = 'Museo de Arte Moderno de Buenos Aires' LIMIT 1);
INSERT INTO location_alternate_names (location_id, alternate_name) VALUES
(@mamba_id, 'MAMBA'),
(@mamba_id, 'Moderno');
