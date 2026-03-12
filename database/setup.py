#!/usr/bin/env python3
"""
Database Setup Script for Momaverse

Creates the database schema. Run this once when initially setting up the project.
For existing data, restore from a backup instead (see README.md).

Usage:
    python setup.py [--drop-tables]

Options:
    --drop-tables      Drop existing tables before creating (WARNING: deletes data)
"""

import argparse
import os
import sys
from pathlib import Path

try:
    import psycopg2
    from psycopg2 import Error
except ImportError:
    print("Error: psycopg2 is required.")
    print("Install it with: pip install psycopg2-binary")
    sys.exit(1)


# Configuration
DB_CONFIG = {
    "local": {
        "host": "localhost",
        "database": "momaverse",
        "user": os.environ.get("USER", "postgres"),
        "password": "",
    },
    "production": {
        "host": "localhost",
        "database": "momaverse",
        "user": "momaverse",
        "password": os.environ.get("DB_PASSWORD", ""),
    },
}

# Paths
SCRIPT_DIR = Path(__file__).parent
SCHEMA_FILE = SCRIPT_DIR / "schema_postgres.sql"

# Tables in order for dropping (respects foreign keys)
ALL_TABLES = [
    # Sync & history
    "conflicts",
    "sync_state",
    "edits",
    # Crawl data (must be dropped before events)
    "event_sources",
    "crawl_event_tags",
    "crawl_event_occurrences",
    "crawl_events",
    "crawl_results",
    "crawl_runs",
    # Events
    "event_tags",
    "location_tags",
    "event_urls",
    "event_occurrences",
    "events",
    # Instagram
    "website_instagram",
    "location_instagram",
    "instagram_accounts",
    # Websites and locations
    "website_tags",
    "website_locations",
    "website_urls",
    "websites",
    "location_alternate_names",
    "locations",
    "tags",
    # Other
    "tag_rules",
    "feedback",
    "users",
    "grantees",
]

# Enum types to drop
ALL_TYPES = [
    "source_type",
    "crawl_mode",
    "crawl_run_status",
    "crawl_result_status",
    "tag_rule_type",
    "edit_action",
    "edit_source",
    "sync_source",
    "conflict_status",
]


def get_db_config():
    """Get database config based on environment."""
    env = os.environ.get("MOMAVERSE_ENV", "local")
    if env not in DB_CONFIG:
        print(f"Warning: Unknown environment '{env}', using 'local'")
        env = "local"
    return DB_CONFIG[env]


def create_connection(database=None):
    """Create database connection."""
    config = get_db_config()
    conn_params = {
        "host": config["host"],
        "user": config["user"],
        "password": config["password"],
        "database": database or config["database"],
    }

    try:
        connection = psycopg2.connect(**conn_params)
        return connection
    except Error as e:
        print(f"Error connecting to database: {e}")
        return None


def create_database():
    """Create database if it doesn't exist."""
    config = get_db_config()
    connection = create_connection(database="postgres")
    if not connection:
        return False

    try:
        connection.autocommit = True
        cursor = connection.cursor()
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (config["database"],)
        )
        if not cursor.fetchone():
            cursor.execute(f"CREATE DATABASE {config['database']}")
            print(f"Database '{config['database']}' created.")
        else:
            print(f"Database '{config['database']}' already exists.")
        return True
    except Error as e:
        print(f"Error creating database: {e}")
        return False
    finally:
        cursor.close()
        connection.close()


def drop_tables(connection):
    """Drop all tables and enum types."""
    cursor = connection.cursor()
    try:
        for table in ALL_TABLES:
            cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            print(f"  Dropped table: {table}")
        for type_name in ALL_TYPES:
            cursor.execute(f"DROP TYPE IF EXISTS {type_name} CASCADE")
            print(f"  Dropped type: {type_name}")
        connection.commit()
        return True
    except Error as e:
        print(f"Error dropping tables: {e}")
        connection.rollback()
        return False
    finally:
        cursor.close()


def create_schema(connection):
    """Create tables from schema_postgres.sql."""
    cursor = connection.cursor()

    try:
        with open(SCHEMA_FILE, "r") as f:
            schema_sql = f.read()

        cursor.execute(schema_sql)
        connection.commit()
        print("Schema created successfully.")
        return True
    except Error as e:
        print(f"Error creating schema: {e}")
        connection.rollback()
        return False
    finally:
        cursor.close()


def show_stats(connection):
    """Show database statistics."""
    cursor = connection.cursor()
    try:
        tables = [
            ("locations", "Locations"),
            ("websites", "Websites"),
            ("events", "Events"),
            ("tags", "Unique tags"),
            ("crawl_runs", "Crawl runs"),
            ("crawl_results", "Crawl results"),
        ]

        print("\n--- Database Statistics ---")
        for table, label in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"{label}: {count}")
            except Error:
                connection.rollback()

    except Error as e:
        print(f"Error getting stats: {e}")
    finally:
        cursor.close()


def main():
    parser = argparse.ArgumentParser(description="Setup Momaverse database schema")
    parser.add_argument(
        "--drop-tables",
        action="store_true",
        help="Drop existing tables before creating (WARNING: deletes data)",
    )
    args = parser.parse_args()

    print("Momaverse Database Setup")
    print("=" * 40)

    # Create database if needed
    if not create_database():
        sys.exit(1)

    # Connect to database
    connection = create_connection()
    if not connection:
        sys.exit(1)

    try:
        # Drop tables if requested
        if args.drop_tables:
            print("\nDropping existing tables...")
            if not drop_tables(connection):
                sys.exit(1)

        # Create schema
        print("\nCreating schema...")
        if not create_schema(connection):
            sys.exit(1)

        # Show stats
        show_stats(connection)

        print("\nSetup complete!")
        print("\nTo populate with seed data, run:")
        print("  psql momaverse -f database/seeds/museos_ba.sql")
        print("  psql momaverse -f database/seeds/teatros_ba.sql")
        print("  # ... etc")

    finally:
        connection.close()


if __name__ == "__main__":
    main()
