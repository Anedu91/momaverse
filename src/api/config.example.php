<?php
/**
 * Database Configuration
 *
 * Copy this file to config.php and fill in your database credentials.
 * NEVER commit config.php to version control.
 *
 * To create the database:
 * 1. Install PostgreSQL
 * 2. Run: python3 database/setup.py
 * 3. Load seeds: psql momaverse -f database/seeds/*.sql
 */

// Detect environment by hostname
$isLocal = in_array($_SERVER['HTTP_HOST'] ?? '', ['localhost', '127.0.0.1'])
        || strpos($_SERVER['HTTP_HOST'] ?? '', 'localhost:') === 0;

if ($isLocal) {
    // Local development
    define('DB_HOST', 'localhost');
    define('DB_NAME', 'momaverse');
    define('DB_USER', getenv('USER') ?: 'postgres');
    define('DB_PASS', '');
} else {
    // Production - fill in your credentials
    define('DB_HOST', 'localhost');
    define('DB_NAME', 'momaverse');
    define('DB_USER', 'momaverse');
    define('DB_PASS', getenv('DB_PASSWORD') ?: '');
}
