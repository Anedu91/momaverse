-- Seed: Tag Rules for Buenos Aires Pipeline
-- Spanish-to-English rewrites and BA-redundant exclusions
-- 22 rewrite rules, 5 exclude rules

USE fomo;

-- ============================================================================
-- REWRITE RULES (Spanish -> English)
-- ============================================================================

INSERT INTO tag_rules (rule_type, pattern, replacement) VALUES
('rewrite', 'musica', 'Music'),
('rewrite', 'danza', 'Dance'),
('rewrite', 'teatro', 'Theater'),
('rewrite', 'arte', 'Art'),
('rewrite', 'exposicion', 'Exhibition'),
('rewrite', 'concierto', 'Concert'),
('rewrite', 'espectaculo', 'Show'),
('rewrite', 'gratis', 'Free Entry'),
('rewrite', 'entradalibre', 'Free Entry'),
('rewrite', 'entradalibr', 'Free Entry'),
('rewrite', 'fotografia', 'Photography'),
('rewrite', 'literatura', 'Literature'),
('rewrite', 'pelicula', 'Film'),
('rewrite', 'taller', 'Workshop'),
('rewrite', 'charla', 'Talk'),
('rewrite', 'conferencia', 'Lecture'),
('rewrite', 'feria', 'Fair'),
('rewrite', 'mercado', 'Market'),
('rewrite', 'festival', 'Festival'),
('rewrite', 'circo', 'Circus'),
('rewrite', 'comedia', 'Comedy'),
('rewrite', 'poesia', 'Poetry');

-- ============================================================================
-- EXCLUDE RULES (BA-redundant tags)
-- ============================================================================

INSERT INTO tag_rules (rule_type, pattern) VALUES
('exclude', 'buenosaires'),
('exclude', 'argentina'),
('exclude', 'caba'),
('exclude', 'ba'),
('exclude', 'ciudaddebuenosaires');
