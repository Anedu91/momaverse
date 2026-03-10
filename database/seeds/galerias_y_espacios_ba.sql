-- Seed: Galerias y Espacios de Arte de Buenos Aires
-- Source: Art galleries, foundations, and alternative spaces in CABA
-- 12 galleries and art spaces

-- ============================================================================
-- LOCATIONS (12 galleries and art spaces)
-- ============================================================================

INSERT INTO locations (name, short_name, very_short_name, address, description, lat, lng, emoji) VALUES
('Fundacion Proa', 'Proa', 'Proa', 'Av. Pedro de Mendoza 1929, CABA', 'Fundacion dedicada al arte contemporaneo internacional. Exposiciones, cine y actividades educativas en La Boca.', -34.638700, -58.362400, '🎨'),
('Coleccion de Arte Amalia Lacroze de Fortabat', 'Coleccion Fortabat', 'Fortabat', 'Olga Cossettini 141, CABA', 'Museo privado en Puerto Madero con coleccion de arte argentino e internacional. Obras de Berni, Xul Solar, Warhol y Turner.', -34.608000, -58.363600, '🎨'),
('Fundacion Klemm', 'Klemm', 'Klemm', 'Marcelo T. de Alvear 626, CABA', 'Fundacion dedicada al arte contemporaneo. Exposiciones y coleccion permanente de arte argentino e internacional.', -34.596700, -58.377800, '🎨'),
('Galeria Ruth Benzacar', 'Ruth Benzacar', 'Benzacar', 'Juan Ramirez de Velasco 1287, CABA', 'Galeria de arte contemporaneo referente en la escena argentina. Artistas emergentes y consagrados.', -34.593700, -58.435000, '🖼️'),
('Galeria Nora Fisch', 'Nora Fisch', 'NFisch', 'Av. Scalabrini Ortiz 1278, CABA', 'Galeria de arte contemporaneo en Palermo. Enfoque en arte argentino emergente y latinoamericano.', -34.593100, -58.425200, '🖼️'),
('Mite Galeria', 'Mite', 'Mite', 'Loyola 32, CABA', 'Galeria de arte contemporaneo en Villa Crespo. Programa de exposiciones de artistas jovenes argentinos.', -34.591600, -58.431600, '🖼️'),
('Barro Galeria', 'Barro', 'Barro', 'Cabrera 3752, CABA', 'Galeria de arte contemporaneo en Palermo. Arte latinoamericano emergente y establecido.', -34.591700, -58.423700, '🖼️'),
('Herlitzka + Faria', 'Herlitzka+Faria', 'H+F', 'Libertad 1630, CABA', 'Galeria de arte contemporaneo en Recoleta. Artistas argentinos y latinoamericanos.', -34.590300, -58.391300, '🖼️'),
('W Gallery', 'W Gallery', 'WGall', 'Parana 1145, CABA', 'Galeria de arte contemporaneo. Programa de artistas emergentes y exposiciones tematicas.', -34.594800, -58.390400, '🖼️'),
('Pabellon 4', 'Pabellon 4', 'Pab4', 'Av. Infanta Isabel 1, CABA', 'Espacio de arte contemporaneo del Gobierno de la Ciudad en el Parque Lezama.', -34.626500, -58.380400, '🎨'),
('Casa Nacional del Bicentenario', 'Bicentenario', 'CNB', 'Riobamba 985, CABA', 'Espacio cultural del Gobierno Nacional. Exposiciones de arte contemporaneo, cine y actividades culturales.', -34.597500, -58.397300, '🏛️'),
('Espacio de Arte Fundacion OSDE', 'Espacio OSDE', 'OSDE', 'Suipacha 658, CABA', 'Espacio de exposiciones de la Fundacion OSDE. Muestras de arte argentino y latinoamericano.', -34.600500, -58.377400, '🎨');

-- ============================================================================
-- LOCATION ALTERNATE NAMES
-- ============================================================================

INSERT INTO location_alternate_names (location_id, alternate_name) VALUES
((SELECT id FROM locations WHERE name = 'Coleccion de Arte Amalia Lacroze de Fortabat' LIMIT 1), 'Museo Fortabat'),
((SELECT id FROM locations WHERE name = 'Coleccion de Arte Amalia Lacroze de Fortabat' LIMIT 1), 'Coleccion Fortabat');

INSERT INTO location_alternate_names (location_id, alternate_name) VALUES
((SELECT id FROM locations WHERE name = 'Fundacion Proa' LIMIT 1), 'Fundacion PROA'),
((SELECT id FROM locations WHERE name = 'Fundacion Proa' LIMIT 1), 'Proa');

INSERT INTO location_alternate_names (location_id, alternate_name) VALUES
((SELECT id FROM locations WHERE name = 'Galeria Ruth Benzacar' LIMIT 1), 'Ruth Benzacar');
