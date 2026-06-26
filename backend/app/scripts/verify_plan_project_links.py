#!/usr/bin/env python3
"""
数据一致性验证脚本 — ProductPlan ↔ Project 关联完整性检查

功能:
  1. 检查所有 ProductPlan 是否有对应的 ProductPlanProjectLink
  2. 检查所有 Project 是否有对应的 ProductPlanProjectLink（通过 project_id）
  3. 检查是否有 Project 通过旧的 product_plan_id 字段关联但缺少 ProductPlanProjectLink
  4. 对缺失的 Link 自动修复（创建 ProductPlanProjectLink 记录）
  5. 输出统计数据（总计划数、有链接数、缺失数、修复数）

独立可运行: python3 app/scripts/verify_plan_project_links.py
使用 SQLAlchemy 标准查询（无 raw SQL）。
"""

import sys
import os

# 确保项目根目录在 sys.path 中，以便导入 app 模块
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.product_plan import ProductPlan, ProductPlanProjectLink
from app.models.project import Project


def check_product_plan_links(db: Session) -> dict:
    """
    检查所有 ProductPlan 是否有对应的 ProductPlanProjectLink。
    Returns: (total, with_links, missing_plan_ids)
    """
    plans = db.query(ProductPlan).all()
    plan_ids = {p.id for p in plans}
    total = len(plan_ids)

    # 查询所有已存在的链接对应的 plan_id
    linked_plan_ids = {
        row[0]
        for row in db.query(ProductPlanProjectLink.product_plan_id).distinct().all()
    }

    with_links = len(plan_ids & linked_plan_ids)
    missing_plan_ids = sorted(plan_ids - linked_plan_ids)
    missing = len(missing_plan_ids)

    return {
        "total": total,
        "with_links": with_links,
        "missing_plan_ids": missing_plan_ids,
        "missing": missing,
    }


def check_project_links(db: Session) -> dict:
    """
    检查所有 Project 是否有对应的 ProductPlanProjectLink（通过 project_id）。
    Returns: (total, with_links, missing_project_ids)
    """
    projects = db.query(Project).all()
    project_ids = {p.id for p in projects}
    total = len(project_ids)

    # 查询所有已存在的链接对应的 project_id
    linked_project_ids = {
        row[0]
        for row in db.query(ProductPlanProjectLink.project_id).distinct().all()
    }

    with_links = len(project_ids & linked_project_ids)
    missing_project_ids = sorted(project_ids - linked_project_ids)
    missing = len(missing_project_ids)

    return {
        "total": total,
        "with_links": with_links,
        "missing_project_ids": missing_project_ids,
        "missing": missing,
    }


def check_legacy_product_plan_id(db: Session) -> list:
    """
    检查是否有 Project 通过旧的 product_plan_id 字段关联了 ProductPlan，
    但缺少对应的 ProductPlanProjectLink 记录。
    Returns: list of (project_id, project_code, project_name, product_plan_id)
    """
    # 先获取所有已有链接的 project_id 集合（避免复杂相关子查询）
    linked_project_ids = {
        row[0]
        for row in db.query(ProductPlanProjectLink.project_id).distinct().all()
    }

    query = db.query(Project.id, Project.code, Project.name, Project.product_plan_id).filter(
        Project.product_plan_id.isnot(None),
    )

    if linked_project_ids:
        query = query.filter(~Project.id.in_(linked_project_ids))

    results = query.all()
    return [dict(zip(("project_id", "project_code", "project_name", "product_plan_id"), r)) for r in results]


def repair_missing_links(
    db: Session,
    plan_results: dict,
    legacy_results: list,
) -> dict:
    """
    自动修复缺失的 ProductPlanProjectLink 记录。
    修复策略：
      - 对没有链接的 ProductPlan：跳过（不知道关联哪个 Project）
      - 对通过 product_plan_id 遗留字段关联但缺少 Link 的 Project：创建 Link

    Returns: {repaired_count, repaired_details}
    """
    repaired = []
    for item in legacy_results:
        project_id = item["project_id"]
        product_plan_id = item["product_plan_id"]

        # 二次确认确实不存在（避免并发小窗口问题）
        existing = (
            db.query(ProductPlanProjectLink)
            .filter(
                ProductPlanProjectLink.project_id == project_id,
                ProductPlanProjectLink.product_plan_id == product_plan_id,
            )
            .first()
        )
        if existing:
            continue

        # 确认 ProductPlan 存在
        plan = db.query(ProductPlan).filter(ProductPlan.id == product_plan_id).first()
        if not plan:
            # ProductPlan 不存在，跳过
            continue

        link = ProductPlanProjectLink(
            product_plan_id=product_plan_id,
            project_id=project_id,
            link_type="primary",
        )
        db.add(link)
        repaired.append(
            {
                "project_id": project_id,
                "project_code": item["project_code"],
                "project_name": item["project_name"],
                "product_plan_id": product_plan_id,
            }
        )
        print(f"  ✅ 修复: Project '{item['project_code']}' (id={project_id}) "
              f"← ProductPlan '{product_plan_id}'")

    if repaired:
        db.commit()
        print(f"  📝 已提交 {len(repaired)} 条修复记录到数据库")

    return {
        "repaired_count": len(repaired),
        "repaired_details": repaired,
    }


def print_report(
    plan_results: dict,
    project_results: dict,
    legacy_results: list,
    repair_results: dict,
):
    """输出可读的统计报告"""
    sep = "=" * 64
    print(f"\n{sep}")
    print(f"  📊 ProductPlan ↔ Project 关联完整性检查报告")
    print(f"{sep}")

    # ProductPlan 统计
    print(f"\n【ProductPlan 维度】")
    print(f"  总计划数:          {plan_results['total']}")
    print(f"  有链接数:          {plan_results['with_links']}")
    print(f"  缺失链接数:        {plan_results['missing']}")
    if plan_results["missing"] > 0:
        print(f"  缺失链接的 Plan ID:")
        for pid in plan_results["missing_plan_ids"]:
            print(f"    - {pid}")

    # Project 统计
    print(f"\n【Project 维度】")
    print(f"  总项目数:          {project_results['total']}")
    print(f"  有链接数:          {project_results['with_links']}")
    print(f"  缺失链接数:        {project_results['missing']}")
    if project_results["missing"] > 0 and len(project_results["missing_project_ids"]) <= 20:
        print(f"  缺失链接的 Project ID:")
        for pid in project_results["missing_project_ids"]:
            print(f"    - {pid}")
    elif project_results["missing"] > 0:
        print(f"  缺失链接的 Project ID (前20个):")
        for pid in project_results["missing_project_ids"][:20]:
            print(f"    - {pid}")
        print(f"    ... 共 {project_results['missing']} 个")

    # 遗留字段检查
    print(f"\n【遗留字段 product_plan_id 检查】")
    print(f"  使用旧字段但仍缺 Link 的项目数: {len(legacy_results)}")
    if legacy_results:
        print(f"  详情:")
        for item in legacy_results:
            print(f"    - Project '{item['project_code']}' (id={item['project_id']}) "
                  f"→ product_plan_id={item['product_plan_id']}")

    # 修复统计
    print(f"\n【自动修复结果】")
    print(f"  修复链接数:        {repair_results['repaired_count']}")
    if repair_results["repaired_details"]:
        print(f"  修复详情:")
        for item in repair_results["repaired_details"]:
            print(f"    - Project '{item['project_code']}' (id={item['project_id']}) "
                  f"← Plan '{item['product_plan_id']}'")

    # 汇总
    print(f"\n{sep}")
    plan_missing = plan_results["missing"]
    proj_missing = project_results["missing"]
    legacy_count = len(legacy_results)
    repaired_count = repair_results["repaired_count"]
    total_missing = plan_missing + proj_missing
    print(f"  总 ProductPlan:      {plan_results['total']}")
    print(f"  总 Project:          {project_results['total']}")
    print(f"  总计缺失 Link:       {total_missing}")
    print(f"  遗留字段待修复:      {legacy_count}")
    print(f"  实际修复数:          {repaired_count}")
    if repaired_count > 0:
        print(f"  状态: ✅ 已修复 {repaired_count} 条缺失链接")
    elif total_missing == 0 and legacy_count == 0:
        print(f"  状态: ✅ 全部一致，无缺失")
    else:
        print(f"  状态: ⚠️ 发现 {total_missing} 处缺失（仅 ProductPlan/Project 维度缺失，未自动修复）")
    print(f"{sep}\n")


def main():
    """主入口"""
    print(f"🔍 开始 ProductPlan ↔ Project 关联完整性检查...")
    print(f"   时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    db = SessionLocal()
    try:
        # 1. ProductPlan 维度检查
        print("📋 步骤 1/4: 检查 ProductPlan 维度...")
        plan_results = check_product_plan_links(db)
        print(f"   → 总计 {plan_results['total']} 个计划, "
              f"{plan_results['with_links']} 个有链接, "
              f"{plan_results['missing']} 个缺失")

        # 2. Project 维度检查
        print("\n📋 步骤 2/4: 检查 Project 维度...")
        project_results = check_project_links(db)
        print(f"   → 总计 {project_results['total']} 个项目, "
              f"{project_results['with_links']} 个有链接, "
              f"{project_results['missing']} 个缺失")

        # 3. 遗留字段检查
        print("\n📋 步骤 3/4: 检查遗留 product_plan_id 字段...")
        legacy_results = check_legacy_product_plan_id(db)
        print(f"   → 发现 {len(legacy_results)} 个项目通过旧字段关联但缺少 Link")
        for item in legacy_results[:5]:
            print(f"     - Project '{item['project_code']}' (id={item['project_id']}) "
                  f"→ product_plan_id={item['product_plan_id']}")
        if len(legacy_results) > 5:
            print(f"     ... 共 {len(legacy_results)} 个")

        # 4. 自动修复
        print("\n📋 步骤 4/4: 自动修复缺失链接...")
        repair_results = repair_missing_links(db, plan_results, legacy_results)

        # 5. 输出报告
        print_report(plan_results, project_results, legacy_results, repair_results)

    except Exception as e:
        print(f"\n❌ 检查过程中发生错误: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
