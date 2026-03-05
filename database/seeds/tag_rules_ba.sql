-- Seed: Tag Rules for Buenos Aires Pipeline
-- English-to-Spanish rewrites and BA-redundant exclusions
-- Tags display in Spanish for BA users

USE fomo;

-- ============================================================================
-- REWRITE RULES (English -> Spanish)
-- Gemini sometimes outputs English tags; normalize to Spanish
-- ============================================================================

INSERT INTO tag_rules (rule_type, pattern, replacement) VALUES
('rewrite', 'music', 'Música'),
('rewrite', 'dance', 'Danza'),
('rewrite', 'theater', 'Teatro'),
('rewrite', 'theatre', 'Teatro'),
('rewrite', 'art', 'Arte'),
('rewrite', 'exhibition', 'Exposición'),
('rewrite', 'concert', 'Concierto'),
('rewrite', 'show', 'Espectáculo'),
('rewrite', 'freeentry', 'Entrada Libre'),
('rewrite', 'free entry', 'Entrada Libre'),
('rewrite', 'photography', 'Fotografía'),
('rewrite', 'literature', 'Literatura'),
('rewrite', 'film', 'Cine'),
('rewrite', 'workshop', 'Taller'),
('rewrite', 'talk', 'Charla'),
('rewrite', 'lecture', 'Conferencia'),
('rewrite', 'fair', 'Feria'),
('rewrite', 'market', 'Mercado'),
('rewrite', 'circus', 'Circo'),
('rewrite', 'comedy', 'Comedia'),
('rewrite', 'poetry', 'Poesía'),
('rewrite', 'outdoor', 'Al Aire Libre'),
('rewrite', 'gallery', 'Galería'),
('rewrite', 'sculpture', 'Escultura'),
('rewrite', 'opening', 'Inauguración'),
('rewrite', 'museum', 'Museo');

-- ============================================================================
-- EXCLUDE RULES (BA-redundant tags)
-- ============================================================================

INSERT INTO tag_rules (rule_type, pattern) VALUES
('exclude', 'buenosaires'),
('exclude', 'argentina'),
('exclude', 'caba'),
('exclude', 'ba'),
('exclude', 'ciudaddebuenosaires');
