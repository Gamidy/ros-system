"""DB Migration: add step_type + step_meta columns"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import engine
from sqlalchemy import text

with engine.begin() as conn:
    for stmt in [
        "ALTER TABLE approval_steps ADD COLUMN step_type VARCHAR(20) DEFAULT 'sequential'",
        "ALTER TABLE approval_requests ADD COLUMN step_meta JSON DEFAULT NULL",
    ]:
        try:
            conn.execute(text(stmt))
            print(f"OK: {stmt.split()[3]}")
        except Exception as e:
            err = str(e)
            if "Duplicate" in err or "already exists" in err:
                print(f"EXISTS: {stmt.split()[3]}")
            else:
                print(f"ERROR: {stmt.split()[3]}: {err}")
    print("Migration complete")
