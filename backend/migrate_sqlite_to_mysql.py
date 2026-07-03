#!/usr/bin/env python3
"""Migration script: SQLite -> MariaDB for ROS system.

Run inside the container: python3 /tmp/migrate_sqlite_to_mysql.py
"""
import sys
import os

# Set DB_TYPE to mysql BEFORE importing app modules
os.environ['DB_TYPE'] = 'mysql'
os.environ['DB_HOST'] = '127.0.0.1'
os.environ['DB_PORT'] = '3306'
os.environ['DB_USER'] = 'ros'
os.environ['DB_PASSWORD'] = 'NingBo2026*'
os.environ['DB_NAME'] = 'ros'

import logging
import sqlite3
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
log = logging.getLogger(__name__)

# ---- Step 1: Connect to SQLite ----
SQLITE_PATH = '/app/ros.db'
log.info("Connecting to SQLite: %s", SQLITE_PATH)
sqlite_conn = sqlite3.connect(SQLITE_PATH)
sqlite_conn.row_factory = sqlite3.Row

# Get all tables from SQLite
tables = sqlite_conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall()
table_names = [t['name'] for t in tables if not t['name'].startswith('sqlite_') and t['name'] != 'alembic_version']
log.info("SQLite tables (%d): %s", len(table_names), table_names)

# Get row counts
row_counts = {}
for name in table_names:
    try:
        count = sqlite_conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
        row_counts[name] = count
    except Exception as e:
        log.warning("  %s: ERROR - %s", name, e)
        row_counts[name] = -1

for name, count in row_counts.items():
    log.info("  %s: %s rows", name, count)

# ---- Step 2: Set up MariaDB connection ----
MYSQL_URL = f"mysql+pymysql://ros:NingBo2026*@127.0.0.1:3306/ros?charset=utf8mb4"
log.info("Connecting to MariaDB: %s", MYSQL_URL.replace('NingBo2026*', '****'))
mysql_engine = create_engine(MYSQL_URL, pool_pre_ping=True)

# ---- Step 3: Create all tables in MariaDB via SQLAlchemy models ----
log.info("Creating tables in MariaDB via SQLAlchemy...")
sys.path.insert(0, '/app')
from app.core.database import Base

# Import all models so they register with Base
from app.models import *  # noqa: F401, F403

Base.metadata.create_all(bind=mysql_engine)
log.info("Tables created in MariaDB ✅")

# ---- Step 4: Get MariaDB table list ----
inspector = inspect(mysql_engine)
mysql_tables = inspector.get_table_names()
log.info("MariaDB tables (%d): %s", len(mysql_tables), mysql_tables)

# ---- Step 5: Copy data table by table ----
# Get column info for each table from both databases
log.info("=" * 60)
log.info("Starting data migration...")
log.info("=" * 60)

mysql_conn = mysql_engine.connect()

# Disable autocommit for safety
with mysql_conn.begin() as trans:
    for table_name in table_names:
        if table_name not in mysql_tables:
            log.warning("  SKIP %s: not found in MariaDB", table_name)
            continue
        
        # Get columns from SQLite
        sqlite_cols = sqlite_conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
        col_names = [col['name'] for col in sqlite_cols]
        
        # Get row count
        src_count = row_counts.get(table_name, 0)
        if src_count == 0:
            log.info("  %s: 0 rows, skipping", table_name)
            continue
        
        log.info("  %s: %d rows, columns: %s", table_name, src_count, col_names)
        
        # Fetch all data from SQLite
        try:
            rows = sqlite_conn.execute(f'SELECT * FROM "{table_name}"').fetchall()
        except Exception as e:
            log.warning("  %s: SELECT error - %s", table_name, e)
            continue
        
        # Build insert statement
        placeholders = ', '.join([':' + c for c in col_names])
        cols_formatted = ', '.join([f'"{c}"' for c in col_names])
        insert_sql = f'INSERT INTO "{table_name}" ({cols_formatted}) VALUES ({placeholders})'
        
        # Convert rows to dicts
        records = []
        for row in rows:
            record = {}
            for i, col in enumerate(col_names):
                val = row[i]
                # Convert bytes to string if needed
                if isinstance(val, bytes):
                    val = val.decode('utf-8', errors='replace')
                record[col] = val
            records.append(record)
        
        # Insert in batches
        batch_size = 100
        total_inserted = 0
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            try:
                mysql_conn.execute(text(insert_sql), batch)
                total_inserted += len(batch)
            except Exception as e:
                log.warning("  %s: batch insert error at offset %d: %s", table_name, i, e)
                # Try one by one
                for j, record in enumerate(batch):
                    try:
                        mysql_conn.execute(text(insert_sql), record)
                        total_inserted += 1
                    except Exception as e2:
                        log.warning("    %s row %d: %s", table_name, i + j, e2)
        
        log.info("  %s: inserted %d/%d rows", table_name, total_inserted, src_count)

# ---- Step 6: Verify ----
log.info("=" * 60)
log.info("Verification")
log.info("=" * 60)

with mysql_conn.begin() as trans:
    for table_name in table_names:
        if table_name not in mysql_tables:
            continue
        try:
            result = mysql_conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
            mysql_count = result.scalar()
            src_count = row_counts.get(table_name, 0)
            status = "✅" if mysql_count == src_count else "❌"
            log.info("  %s: SQLite=%d → MariaDB=%d %s", table_name, src_count, mysql_count, status)
        except Exception as e:
            log.warning("  %s: verify error - %s", table_name, e)

mysql_conn.close()
sqlite_conn.close()
log.info("Migration complete! 🎉")
