#!/usr/bin/env python3
"""
Data migration: Copy Sheet1–5 data from existing Project records into ProductPlan sub-tables.

Requirements:
1. Reads all Projects with non-null product_type (meaning they have Sheet1-5 data)
2. For each Project, find/create a ProductPlan (match by name+series)
3. Copy Sheet1 fields → ProductPlan direct fields + ProductPlanInitiation sub-table
4. Copy Sheet2 fields → ProductPlanMarket
5. Copy Sheet3 fields → ProductPlanTechSpec
6. Parse JSON team_members → ProductPlanTeam rows
7. Set ProductPlan.project_id = Project.id
8. IDEMPOTENT — skips if initiation sub-table already exists
9. Supports --dry-run
10. Prints summary

Usage:
    cd /Users/gamidy/ros-source/ros-system/backend
    python3 -m app.migrate_p1_sheet_data                # real run
    python3 -m app.migrate_p1_sheet_data --dry-run      # preview

Safe to run multiple times — idempotent.
"""
import json
import sys
import uuid
import logging

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine
from app.models.project import Project
from app.models.product_plan import ProductPlan, ProductPlanStage
from app.models.product_plan_subs import (
    ProductPlanInitiation,
    ProductPlanMarket,
    ProductPlanTechSpec,
    ProductPlanTeam,
)

logger = logging.getLogger(__name__)


# ── Field mappings ──────────────────────────────────────────────────────────

# Columns we try to copy from Project → ProductPlan direct fields.
# The script validates each column exists on the actual table before using it.
PRODUCT_PLAN_DIRECT_MAP = {
    # 以下 11 个字段已迁移到 ProductPlanInitiation 子表，不再写入 ProductPlan 直接字段
    # product_type → product_type (now in product_plan_initiations)
    # climate_zone → climate_zone (now in product_plan_initiations)
    # refrigerant → refrigerant (now in product_plan_initiations)
    # capacity_range → capacity_range (now in product_plan_initiations)
    # voltage_freq → voltage_freq (now in product_plan_initiations)
    # series_name → series_name (now in product_plan_initiations)
    # energy_rating → energy_rating (now in product_plan_initiations)
    # dev_category → dev_category (now in product_plan_initiations)
    # project_origin → project_origin (now in product_plan_initiations)
    # project_duration → project_duration (now in product_plan_initiations)
    # ip_ownership → ip_ownership (now in product_plan_initiations)
    "target_market": "target_market_detail",  # Project.target_market → ProductPlan.target_market_detail
}

# Sheet1 fields → ProductPlanInitiation
INITIATION_FIELDS = [
    "product_type",
    "target_market",
    "climate_zone",
    "refrigerant",
    "capacity_range",
    "voltage_freq",
    "series_name",
    "energy_rating",
    "ip_ownership",
    "project_duration",
    "dev_category",
    "project_origin",
    "background_basis",
    "overall_goal",
    "tech_goal",
    "cost_goal",
    "sales_goal",
    "cert_goal",
    "schedule_goal",
    "patent_goal",
    "other_goals",
    "deliverables",
    "sample_qty",
    "required_date",
]

# Sheet2 fields → ProductPlanMarket
MARKET_FIELDS = [
    "main_capacity",
    "energy_efficiency_req",
    "cert_requirements",
    "target_price",
    "customer_requirements",
]

# Sheet3 fields → ProductPlanTechSpec
TECH_SPEC_FIELDS = [
    "core_performance",
    "safety_compliance",
    "optional_config",
]


# ── Helpers ─────────────────────────────────────────────────────────────────

def _existing_project_columns() -> set:
    """Return the set of column names that actually exist on the `projects` table."""
    return {c["name"] for c in inspect(engine).get_columns("projects")}


def _existing_plan_columns() -> set:
    """Return the set of column names that actually exist on the `product_plans` table."""
    return {c["name"] for c in inspect(engine).get_columns("product_plans")}


def _table_exists(name: str) -> bool:
    """Check if a table exists in the database."""
    return name in inspect(engine).get_table_names()


def _safe_get(proj_row: dict, field: str, default=None):
    """Get a value from a dict (returned by raw query), returning default if missing."""
    return proj_row.get(field, default)


def _parse_team_members(raw_value):
    """Parse team_members JSON from a project row into a list of dicts."""
    if not raw_value:
        return []
    if isinstance(raw_value, str):
        try:
            return json.loads(raw_value)
        except (json.JSONDecodeError, TypeError):
            return []
    if isinstance(raw_value, list):
        return raw_value
    return []


def _build_project_query() -> str:
    """
    Build a raw SELECT query for projects, using only columns that actually exist.

    Returns the SQL string with columns explicitly listed.
    """
    existing = _existing_project_columns()
    # Core columns we always need
    required = {"id", "name", "series_name", "product_type"}
    # All Sheet1–5 columns
    all_source = (
        required
        | set(PRODUCT_PLAN_DIRECT_MAP.keys())
        | set(INITIATION_FIELDS)
        | set(MARKET_FIELDS)
        | set(TECH_SPEC_FIELDS)
        | {"team_members"}
    )

    safe_cols = [c for c in all_source if c in existing]
    # Always include id and name
    for c in ("id", "name"):
        if c not in safe_cols:
            safe_cols.append(c)

    cols = ", ".join(f"p.{c}" for c in safe_cols)
    return f"SELECT {cols} FROM projects p WHERE p.product_type IS NOT NULL AND p.product_type != ''"


def _get_sub_table_columns(table_name: str) -> set:
    """Return column names for a sub-table, or empty set if table doesn't exist."""
    try:
        return {c["name"] for c in inspect(engine).get_columns(table_name)}
    except Exception as e:
        logger.warning(f"get_columns failed for {table_name}: {e}")
        return set()


# ── Main migration ─────────────────────────────────────────────────────────

def migrate(dry_run: bool = False):
    """Execute the migration."""
    db: Session = SessionLocal()
    try:
        # Discover which tables/columns exist
        plan_cols = _existing_plan_columns()
        init_exists = _table_exists("product_plan_initiations")
        market_exists = _table_exists("product_plan_markets")
        tech_exists = _table_exists("product_plan_tech_specs")
        team_exists = _table_exists("product_plan_teams")

        # Warn if sub-tables are missing (expected — they'll be created by Alembic first)
        missing_tables = []
        if not init_exists:
            missing_tables.append("product_plan_initiations")
        if not market_exists:
            missing_tables.append("product_plan_markets")
        if not tech_exists:
            missing_tables.append("product_plan_tech_specs")
        if not team_exists:
            missing_tables.append("product_plan_teams")
        if missing_tables:
            print(
                f"WARNING: Sub-tables not found in DB: {', '.join(missing_tables)}. "
                f"Run Alembic migrations first (alembic upgrade head).",
                file=sys.stderr,
            )
            if not dry_run:
                print("Aborting — schema missing.", file=sys.stderr)
                return 1

        # 1. Read all projects with Sheet1-5 data
        query_sql = _build_project_query()
        result = db.execute(text(query_sql))
        rows = result.mappings().all()

        if not rows:
            print("No projects with non-null product_type found.")
            return 0

        migrated_count = 0
        created_plan_count = 0
        skipped_count = 0

        for row in rows:
            proj_id = row["id"]
            proj_name = row["name"]
            series_val = _safe_get(row, "series_name") or ""

            # 2. Find or create ProductPlan (match by name + series)
            plan = (
                db.query(ProductPlan)
                .filter(
                    ProductPlan.name == proj_name,
                    ProductPlan.series == series_val,
                )
                .first()
            )

            is_new_plan = plan is None
            if is_new_plan:
                if dry_run:
                    print(
                        f"[DRY-RUN] Would create ProductPlan: name={proj_name!r}, "
                        f"series={series_val!r}, project_id={proj_id}"
                    )
                    # Fake in-memory plan for idempotency check below
                    plan = ProductPlan(
                        id=str(uuid.uuid4()),
                        name=proj_name,
                        series=series_val,
                    )
                else:
                    plan = ProductPlan(
                        id=str(uuid.uuid4()),
                        name=proj_name,
                        series=series_val,
                    )
                    db.add(plan)
                    db.flush()
                created_plan_count += 1
            else:
                if dry_run:
                    print(
                        f"[DRY-RUN] Found existing ProductPlan: id={plan.id}, "
                        f"name={proj_name!r}"
                    )

            # 3. Idempotency check — skip if initiation sub-table already exists
            existing_init = None
            if init_exists:
                existing_init = (
                    db.query(ProductPlanInitiation)
                    .filter(ProductPlanInitiation.product_plan_id == plan.id)
                    .first()
                )
            if existing_init is not None:
                skipped_count += 1
                if dry_run:
                    print(
                        f"  [DRY-RUN] SKIP (already migrated): project_id={proj_id}, "
                        f"plan_id={plan.id}"
                    )
                continue

            # ── Copy data ────────────────────────────────────────────────
            if dry_run:
                print(f"  [DRY-RUN] Would migrate: project_id={proj_id}, plan_id={plan.id}")
                direct_vals = {src: _safe_get(row, src) for src in PRODUCT_PLAN_DIRECT_MAP}
                print(f"    ProductPlan direct fields: {direct_vals}")
                init_vals = {f: _safe_get(row, f) for f in INITIATION_FIELDS}
                print(f"    Initiation fields: {init_vals}")
                market_vals = {f: _safe_get(row, f) for f in MARKET_FIELDS}
                print(f"    Market fields: {market_vals}")
                tech_vals = {f: _safe_get(row, f) for f in TECH_SPEC_FIELDS}
                print(f"    TechSpec fields: {tech_vals}")
                team_data = _parse_team_members(_safe_get(row, "team_members"))
                print(f"    Team members ({len(team_data)} rows): {team_data}")
                migrated_count += 1
                continue

            # ── Real write operations ───────────────────────────────────

            # 3a. ProductPlan direct fields (only for columns that exist)
            for src_field, dst_field in PRODUCT_PLAN_DIRECT_MAP.items():
                if dst_field in plan_cols:
                    val = _safe_get(row, src_field)
                    setattr(plan, dst_field, val)

            # Also set market, project_id, and status on the plan
            if "market" in plan_cols:
                plan.market = _safe_get(row, "target_market")
            if "project_id" in plan_cols:
                plan.project_id = proj_id
            if plan.status is None and "status" in plan_cols:
                plan.status = ProductPlanStage.PROJECT_INIT

            # 3b. ProductPlanInitiation
            if init_exists:
                init_cols = _get_sub_table_columns("product_plan_initiations")
                init_kwargs = {"product_plan_id": plan.id}
                for f in INITIATION_FIELDS:
                    if f in init_cols:
                        init_kwargs[f] = _safe_get(row, f)
                initiation = ProductPlanInitiation(**init_kwargs)
                db.add(initiation)

            # 4. ProductPlanMarket
            if market_exists:
                mkt_cols = _get_sub_table_columns("product_plan_markets")
                mkt_kwargs = {"product_plan_id": plan.id}
                for f in MARKET_FIELDS:
                    if f in mkt_cols:
                        mkt_kwargs[f] = _safe_get(row, f)
                market = ProductPlanMarket(**mkt_kwargs)
                db.add(market)

            # 5. ProductPlanTechSpec
            if tech_exists:
                tech_cols = _get_sub_table_columns("product_plan_tech_specs")
                tech_kwargs = {"product_plan_id": plan.id}
                for f in TECH_SPEC_FIELDS:
                    if f in tech_cols:
                        tech_kwargs[f] = _safe_get(row, f)
                tech_spec = ProductPlanTechSpec(**tech_kwargs)
                db.add(tech_spec)

            # 6. Parse team_members → ProductPlanTeam rows
            if team_exists:
                team_cols = _get_sub_table_columns("product_plan_teams")
                team_data = _parse_team_members(_safe_get(row, "team_members"))
                for member in team_data:
                    team_kwargs = {"product_plan_id": plan.id}
                    for c in ("role_name", "member_name", "department", "responsibility"):
                        if c in team_cols:
                            team_kwargs[c] = member.get(c)
                    team_row = ProductPlanTeam(**team_kwargs)
                    db.add(team_row)

            migrated_count += 1

        # ── Commit ──────────────────────────────────────────────────────
        if dry_run:
            print()
            print(
                f"[DRY-RUN SUMMARY] Would migrate {migrated_count} projects, "
                f"create {created_plan_count} plans, skip {skipped_count}"
            )
        else:
            db.commit()
            print(
                f"Migrated {migrated_count} projects, "
                f"created {created_plan_count} plans, "
                f"skipped {skipped_count}"
            )

        return 0

    finally:
        db.close()


def main():
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        sys.argv.remove("--dry-run")
        print("=== DRY RUN MODE — no changes will be made ===\n")
    return migrate(dry_run=dry_run)


if __name__ == "__main__":
    sys.exit(main())
