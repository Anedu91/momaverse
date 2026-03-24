#!/usr/bin/env python3
"""
Schema Migration Script (PostgreSQL)

Compares the current database schema against schema_postgres.sql and applies any missing
columns, indexes, or tables.

Usage:
    python migrate_schema.py
    python migrate_schema.py --dry-run  # Show what would be changed without applying
"""

import argparse
import os
import re
import sys
from pathlib import Path

try:
    import psycopg2
    from psycopg2 import Error
except ImportError:
    print("Error: psycopg2 is required.")
    print("Install it with: pip install psycopg2-binary")
    sys.exit(1)


# Database Configuration
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

SCRIPT_DIR = Path(__file__).parent
SCHEMA_FILE = SCRIPT_DIR / "schema_postgres.sql"


def get_db_config():
    """Get database config based on environment."""
    env = os.environ.get("MOMAVERSE_ENV", "local")
    if env not in DB_CONFIG:
        env = "local"
    return DB_CONFIG[env]


def create_connection():
    """Create database connection."""
    config = get_db_config()
    try:
        return psycopg2.connect(
            host=config["host"],
            database=config["database"],
            user=config["user"],
            password=config["password"],
        )
    except Error as e:
        print(f"Error connecting to database: {e}")
        return None


def get_current_schema(cursor):
    """Get current database schema as a structured dict."""
    schema = {"tables": {}}

    # Get all tables
    cursor.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    """)
    tables = [row[0] for row in cursor.fetchall()]

    for table in tables:
        schema["tables"][table] = {"columns": {}, "indexes": {}}

        # Get columns
        cursor.execute(
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
        """,
            (table,),
        )

        for row in cursor.fetchall():
            col_name = row[0]
            schema["tables"][table]["columns"][col_name] = {
                "type": row[1],
                "nullable": row[2] == "YES",
                "default": row[3],
            }

        # Get indexes
        cursor.execute(
            """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public' AND tablename = %s
        """,
            (table,),
        )

        for row in cursor.fetchall():
            schema["tables"][table]["indexes"][row[0]] = {"definition": row[1]}

    return schema


def parse_schema_sql():
    """Parse schema_postgres.sql to extract expected tables and columns."""
    with open(SCHEMA_FILE) as f:
        content = f.read()

    schema = {"tables": {}}

    # Find all CREATE TABLE statements
    table_pattern = re.compile(
        r"CREATE TABLE IF NOT EXISTS (\w+)\s*\((.*?)\);", re.DOTALL | re.IGNORECASE
    )

    for match in table_pattern.finditer(content):
        table_name = match.group(1)
        table_body = match.group(2)

        schema["tables"][table_name] = {"columns": {}, "indexes": {}}

        lines = [line.strip() for line in table_body.split("\n") if line.strip()]

        for line in lines:
            line = line.rstrip(",")
            if not line or line.startswith("--"):
                continue
            # Skip constraints
            if any(
                line.upper().startswith(kw)
                for kw in ["UNIQUE", "FOREIGN KEY", "PRIMARY KEY"]
            ):
                continue

            # Parse column definitions
            col_match = re.match(
                r"(\w+)\s+(SERIAL|INTEGER|BOOLEAN|TEXT|VARCHAR\([^)]+\)|DATE|TIMESTAMP|DECIMAL\([^)]+\)|CHAR\([^)]+\)|JSONB|\w+)",
                line,
                re.IGNORECASE,
            )
            if col_match:
                col_name = col_match.group(1)
                col_type = col_match.group(2).lower()
                nullable = "NOT NULL" not in line.upper()

                schema["tables"][table_name]["columns"][col_name] = {
                    "type": col_type,
                    "nullable": nullable,
                    "full_definition": line,
                }

    # Find CREATE INDEX statements
    index_pattern = re.compile(r"CREATE INDEX (\w+) ON (\w+)", re.IGNORECASE)
    for match in index_pattern.finditer(content):
        idx_name = match.group(1)
        table_name = match.group(2)
        if table_name in schema["tables"]:
            schema["tables"][table_name]["indexes"][idx_name] = {
                "definition": match.group(0)
            }

    return schema


def generate_migrations(current, expected):
    """Compare schemas and generate migration SQL statements."""
    migrations = []

    for table_name in expected["tables"]:
        if table_name not in current["tables"]:
            migrations.append(
                (f"Table {table_name} is missing - run setup.py to create it", None)
            )
            continue

        current_table = current["tables"][table_name]
        expected_table = expected["tables"][table_name]

        # Check for missing columns
        for col_name, col_info in expected_table["columns"].items():
            if col_name not in current_table["columns"]:
                col_def = col_info["full_definition"]
                col_def = col_def.rstrip(",")
                sql = f"ALTER TABLE {table_name} ADD COLUMN {col_def}"
                migrations.append((f"Add column {table_name}.{col_name}", sql))

        # Check for missing indexes
        for idx_name in expected_table["indexes"]:
            if idx_name not in current_table["indexes"]:
                migrations.append(
                    (
                        f"Add index {idx_name} on {table_name}",
                        expected_table["indexes"][idx_name].get("definition"),
                    )
                )

    return migrations


def run_migrations(cursor, connection, migrations, dry_run=False):
    """Execute migration statements."""
    if not migrations:
        print("No migrations needed - schema is up to date.")
        return True

    print(f"{'[DRY RUN] ' if dry_run else ''}Found {len(migrations)} migration(s)...\n")

    for description, sql in migrations:
        if sql is None:
            print(f"  [SKIP] {description}")
            continue

        if dry_run:
            print(f"  [WOULD RUN] {description}")
            print(f"    SQL: {sql}")
        else:
            try:
                print(f"  - {description}...")
                cursor.execute(sql)
                connection.commit()
                print("    [OK]")
            except Error as e:
                print(f"    [ERROR] {e}")
                connection.rollback()
                return False

    return True


def main():
    parser = argparse.ArgumentParser(description="Migrate database schema")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without applying",
    )
    args = parser.parse_args()

    print("Schema Migration (PostgreSQL)")
    print("=" * 40)

    if not SCHEMA_FILE.exists():
        print(f"Error: schema_postgres.sql not found at {SCHEMA_FILE}")
        sys.exit(1)

    connection = create_connection()
    if not connection:
        sys.exit(1)

    cursor = connection.cursor()

    try:
        print("Parsing schema_postgres.sql...")
        expected_schema = parse_schema_sql()
        print(f"  Found {len(expected_schema['tables'])} tables in schema_postgres.sql")

        print("Reading current database schema...")
        current_schema = get_current_schema(cursor)
        print(f"  Found {len(current_schema['tables'])} tables in database")

        print("\nComparing schemas...")
        migrations = generate_migrations(current_schema, expected_schema)

        success = run_migrations(cursor, connection, migrations, dry_run=args.dry_run)

        if success:
            if args.dry_run:
                print("\n[DRY RUN] No changes made.")
            else:
                print("\n[OK] Migration complete!")
        else:
            print("\n[ERROR] Some migrations failed.")
            sys.exit(1)

    except Error as e:
        print(f"\nDatabase error: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
