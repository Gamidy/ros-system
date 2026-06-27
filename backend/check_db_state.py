"""检查数据库迁移状态"""
import sys
sys.path.insert(0, ".")
from sqlalchemy import create_engine, inspect, text
from app.core.config import settings

engine = create_engine(settings.db_url)
insp = inspect(engine)

with engine.connect() as conn:
    tables = insp.get_table_names()
    
    # product_plan_histories
    print("product_plan_histories exists:", "product_plan_histories" in tables)
    
    # product_plans version column
    if "product_plans" in tables:
        cols = [c["name"] for c in insp.get_columns("product_plans")]
        print("product_plans has version col:", "version" in cols)
    
    # verification_requirements product_plan_id type
    if "verification_requirements" in tables:
        cols = insp.get_columns("verification_requirements")
        for c in cols:
            if c["name"] == "product_plan_id":
                print(f"verification_requirements.product_plan_id type: {c['type']}")
    
    # user_notification_prefs schema
    if "user_notification_prefs" in tables:
        cols = [c["name"] for c in insp.get_columns("user_notification_prefs")]
        print(f"user_notification_prefs cols: {cols}")
    
    # Check competitor_models for source/source_url
    if "competitor_models" in tables:
        cols = [c["name"] for c in insp.get_columns("competitor_models")]
        print(f"competitor_models cols: {cols}")
        print("Has source:", "source" in cols)
        print("Has source_url:", "source_url" in cols)
    
    # Check plan_subs tables for version_id
    for t in ["product_plan_initiations", "product_plan_markets", "product_plan_tech_specs", "product_plan_teams"]:
        if t in tables:
            cols = [c["name"] for c in insp.get_columns(t)]
            print(f"{t} cols: {cols[:10]}...")
    
    # Current alembic version
    result = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
    print(f"Alembic current version: {result}")
