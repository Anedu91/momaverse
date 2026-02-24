# Technology Stack

**Analysis Date:** 2026-02-24

## Languages

**Primary:**
- JavaScript (ES2020) - Frontend application, UI modules, map interactions
- Python 3 - Pipeline: data crawling, extraction, processing, frequency analysis
- PHP - Backend API endpoints, database operations, admin panel
- SQL - Database schema and queries (MySQL 8.0)
- CSS 3 - Styling with CSS variables for theme support

**Secondary:**
- HTML 5 - Markup structure with semantic elements
- Markdown - Documentation and build system documentation

## Runtime

**Environment:**
- Node.js (for build tooling only)
- Python 3.8+ (for data pipeline)
- PHP 8.0+ (for backend API and admin)
- MySQL 8.0+ (database)

**Package Manager:**
- npm - JavaScript dependencies
  - Lockfile: `package-lock.json` (present)
- pip - Python dependencies (requirements inferred from imports)
  - No `requirements.txt` found; dependencies specified in code imports

## Frameworks

**Core Frontend:**
- MapLibre GL 4.7.1 - Web mapping library (source: `unpkg.com`)
- No frontend framework (vanilla JavaScript with modular architecture)

**Build/Dev:**
- esbuild 0.25.0 - JavaScript and CSS minification/bundling (`build.js`)
- Custom build system using Node.js fs and crypto modules

**Data Pipeline:**
- crawl4ai - Advanced web scraping with Markdown conversion
- google-genai (google-generativeai) - Gemini AI API for structured event extraction

**Backend/Database:**
- mysql-connector-python - Python MySQL client for pipeline
- PDO (PHP Data Objects) - PHP database abstraction layer
- No ORM; raw SQL queries used in both PHP and Python

## Key Dependencies

**Critical Frontend:**
- flatpickr 4.6.13 - Date range picker (bundled in build)
- maplibre-gl 4.7.1 - Web mapping and marker rendering
- Inter font (from rsms.me) - Typography

**Pipeline:**
- crawl4ai - Website crawling with content filtering and deep crawling support
- google-genai - Gemini AI with structured output (Pydantic schemas)
- mysql-connector-python - Database connectivity
- python-dotenv - Environment variable management
- Pillow (PIL) - Image processing for screenshot extraction
- httpx - Async HTTP client for web requests
- pydantic - Data validation and schema definition

**Deployment/FTP:**
- FTP client (native Python ftplib) - File upload to server
- SSH client (paramiko-based) - Database synchronization

## Configuration

**Environment:**
- `.env.example` defines required configuration for:
  - `GEMINI_API_KEY` - Google Gemini API key
  - `FTP_HOST`, `FTP_USER`, `FTP_PASSWORD` - FTP upload credentials
  - `SSH_HOST`, `SSH_USER`, `SSH_PORT` - SSH/database sync credentials
  - `PROD_DB_NAME`, `PROD_DB_USER`, `PROD_DB_PASS` - Production database
- Local development uses environment detection in PHP (`config.php`)
- Python pipeline reads `.env` for configuration

**Build:**
- `build.js` - Custom esbuild-based bundler
- Concatenates `flatpickr.js` + all app modules in order
- Minifies JS/CSS in production, passes through in dev
- Generates content-hashed bundle names in production
- CSS bundles include font path adjustments

**Database:**
- `database/schema.sql` - Complete table structure (23 tables)
- `database/setup.py` - Database initialization script with schema creation
- Supports both local (XAMPP) and production (Namecheap) environments

## Platform Requirements

**Development:**
- Node.js 14+ (for build system only)
- Python 3.8+ (for pipeline)
- MySQL 8.0+ (local or networked)
- PHP 8.0+ (local or networked)
- Modern browser with WebGL support (for MapLibre)

**Production:**
- Web hosting with:
  - PHP 8.0+ with PDO MySQL driver
  - MySQL 8.0+ database
  - FTP access for file uploads
  - SSH access for database synchronization (optional, for Namecheap-style hosting)
- Node.js NOT required (builds to static files + PHP)

## Build Pipeline

**Development:**
```bash
npm run dev          # Builds to dist/ in dev mode, watches for changes
```

**Production:**
```bash
npm run build        # Builds to dist/ with minification and hashing
```

**Output:**
- `dist/app.[hash].js` - Bundled and minified JavaScript
- `dist/app.[hash].css` - Bundled and minified CSS
- `dist/index.html` - Transformed HTML with bundled references
- `dist/` includes symlinks to `data/`, `images/`, `fonts/`, `api/`, `admin/` (dev) or full copies (prod)

## Asset Pipeline

**JavaScript Bundling:**
- Extracts script load order from `index.html` (script tag order)
- Concatenates in order: flatpickr, then app modules
- Single bundle for production

**CSS Bundling:**
- esbuild processes `src/css/index.css` with @import resolution
- Prepends flatpickr CSS
- Font paths adjusted from `../fonts/` to `fonts/` (root level)
- Minified in production

**Data Assets:**
- `src/data/` - JSON files (events, locations, tags, map styles)
- `src/images/` - SVG icons and images
- `src/fonts/` - Compressed font files (TTF, WOFF2)
- No image optimization in build pipeline

---

*Stack analysis: 2026-02-24*
