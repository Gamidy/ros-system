#!/usr/bin/env python3
"""Smart SQLite -> MariaDB migration with column diff handling"""
import os, sys
os.environ['DB_TYPE'] = 'mysql'
os.environ['DB_HOST'] = '172.17.0.1'
os.environ['DB_PASSWORD'] = 'NingBo2026*'
os.environ['DB_NAME'] = 'ros'

import logging, sqlite3
from sqlalchemy import create_engine, text, inspect

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
log = logging.getLogger(__name__)

SQLITE_PATH = '/app/ros.db'
sqlite_conn = sqlite3.connect(SQLITE_PATH)
sqlite_conn.row_factory = sqlite3.Row

tables = [t['name'] for t in sqlite_conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name != 'alembic_version'"
).fetchall()]

MYSQL_URL = "mysql+pymysql://ros:NingBo2026*@172.17.0.1:3306/ros?charset=utf8mb4"
engine = create_engine(MYSQL_URL, pool_pre_ping=True)

# Create ORM tables first
log.info("Creating ORM tables...")
sys.path.insert(0, '/app')
from app.core.database import Base
from app.models import *
Base.metadata.create_all(bind=engine)
log.info("ORM tables created")

# Clear existing data
with engine.connect() as conn:
    with conn.begin():
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        inspector = inspect(engine)
        for t in inspector.get_table_names():
            conn.execute(text(f"TRUNCATE TABLE `{t}`"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
log.info("Data cleared")

# Migrate table by table with column intersection
inspector = inspect(engine)
mysql_tables = inspector.get_table_names()

with engine.connect() as conn:
    for tbl in tables:
        if tbl not in mysql_tables:
            log.warning("  SKIP %s: not in MariaDB", tbl)
            continue
        
        # Get SQLite columns
        sqlite_cols_raw = sqlite_conn.execute(f'PRAGMA table_info("{tbl}")').fetchall()
        sqlite_col_names = {col['name'] for col in sqlite_cols_raw}
        
        # Get MariaDB columns
        mysql_cols = [col['name'] for col in inspector.get_columns(tbl)]
        mysql_col_names = {col for col in mysql_cols}
        
        # Find columns in SQLite but not in MariaDB - ADD them
        missing = sqlite_col_names - mysql_col_names
        if missing:
            log.info("  %s: adding %d missing columns", tbl, len(missing))
            for col_info in sqlite_cols_raw:
                cname = col_info['name']
                if cname in missing:
                    ctype = col_info['type']
                    nullable = "NULL" if col_info['notnull'] == 0 else "NOT NULL"
                    default = f"DEFAULT '{col_info['dflt_value']}'" if col_info['dflt_value'] else ""
                    try:
                        conn.execute(text(f"ALTER TABLE `{tbl}` ADD COLUMN `{cname}` {ctype} {nullable} {default}".strip()))
                    except Exception as e:
                        log.warning("    ADD COLUMN %s: %s", cname, str(e)[:80])
        
        # Re-read MariaDB columns after ALTER
        mysql_cols2 = [col['name'] for col in inspector.get_columns(tbl)]
        
        # Intersect columns for INSERT
        common_cols = [c for c in sqlite_cols_raw if c['name'] in mysql_cols2]
        col_names = [c['name'] for c in common_cols]
        
        if not col_names:
            log.warning("  %s: no common columns, skip", tbl)
            continue
        
        rows = sqlite_conn.execute(f'SELECT * FROM "{tbl}"').fetchall()
        if not rows:
            log.info("  %s: 0 rows, skip", tbl)
            continue
        
        placeholders = ', '.join([':' + c for c in col_names])
        cols_fmt = ', '.join([f'`{c}`' for c in col_names])
        insert_sql = f'INSERT INTO `{tbl}` ({cols_fmt}) VALUES ({placeholders})'
        
        inserted = 0
        for row in rows:
            record = {}
            for i, col in enumerate(col_names):
                val = row[i]
                if isinstance(val, bytes):
                    val = val.decode('utf-8', errors='replace')
                record[col] = val
            try:
                conn.execute(text(insert_sql), record)
                inserted += 1
            except Exception as e:
                log.warning("    %s row err: %s", tbl, str(e)[:120])
        
        log.info("  %s: %d rows", tbl, inserted)

# Verify
log.info("=" * 50)
log.info("Verification")
ok = fail = 0
with engine.connect() as conn:
    for tbl in tables:
        if tbl not in mysql_tables:
            continue
        src = len(sqlite_conn.execute(f'SELECT COUNT(*) FROM "{tbl}"').fetchall())
        if src == 0:
            continue
        try:
            dst = conn.execute(text(f"SELECT COUNT(*) FROM `{tbl}`")).scalar()
            status = "✅" if dst == src else "❌"
            log.info("  %s: %d -> %d %s", tbl, src, dst, status)
            if dst == src: ok += 1
            else: fail += 1
        except:
            pass
log.info("Result: %d OK, %d FAIL", ok, fail)
sqlite_conn.close()
log.info("🎉 Done")
