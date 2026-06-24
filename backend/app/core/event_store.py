"""Event Store — 事件持久化 + Replay 系统 (Phase 4)

三层能力:
1. store_event() — 增强版事件落库 (含 plan state snapshot)
2. get_timeline() — 按 plan_id 获取有序事件链
3. replay() — 重建 ProductPlan 在任意时间点的状态

架构决策:
- 使用 raw SQL 访问增强字段 (state_snapshot / plan_id / saga_id)
- 现有 EventLog 模型通过 alembic 迁移逐步添加列，不阻塞代码发布
- 所有读写走独立 DB session，不污染事务上下文
"""
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════
# 辅助函数
# ════════════════════════════════════════════════════════


def _safe_iso(dt) -> Optional[str]:
    """将 datetime 转换为 ISO 8601 字符串，None-safe"""
    if dt is None:
        return None
    try:
        return dt.isoformat()
    except Exception:
        return None


# ════════════════════════════════════════════════════════
# Event Store — 持久化 + 查询 + Replay
# ════════════════════════════════════════════════════════


class EventStore:
    """事件存储服务 — 落库 + 时序查询 + Replay"""

    @staticmethod
    def _ensure_columns(db: Session) -> bool:
        """检查并创建 event_logs 增强字段（幂等）
        
        在生产环境是新老兼容的关键:
        - 如果字段已存在 → 跳过
        - 如果不存在 → ALTER TABLE 添加
        """
        try:
            db.execute(text("SELECT plan_id FROM event_logs LIMIT 0"))
            return True  # 字段已存在
        except Exception:
            pass
        try:
            db.execute(text(
                "ALTER TABLE event_logs "
                "ADD COLUMN plan_id VARCHAR(36) NULL AFTER payload, "
                "ADD COLUMN saga_id VARCHAR(36) NULL AFTER plan_id, "
                "ADD COLUMN state_snapshot LONGTEXT NULL AFTER saga_id, "
                "ADD INDEX ix_event_logs_plan_id (plan_id)"
            ))
            db.commit()
            logger.info("event_logs 增强字段创建完成: plan_id, saga_id, state_snapshot")
            return True
        except Exception as e:
            logger.warning("event_logs 增强字段创建失败（可能已存在）: %s", e)
            return False

    @staticmethod
    def store(
        db: Session,
        event_type: str,
        event_version: str = "v1",
        payload: Optional[dict] = None,
        plan_id: Optional[str] = None,
        saga_id: Optional[str] = None,
        state_snapshot: Optional[dict] = None,
        status: str = "emitted",
    ) -> int:
        """写入事件日志（增强版）"""
        EventStore._ensure_columns(db)
        from app.models.event_log import EventLog

        payload_json = json.dumps(payload or {}, ensure_ascii=False, default=str)
        snapshot_json = json.dumps(state_snapshot or {}, ensure_ascii=False, default=str) if state_snapshot else None

        log = EventLog(
            event_type=event_type,
            event_version=event_version,
            payload=payload_json,
            status=status,
        )
        db.add(log)
        db.flush()
        log_id = log.id

        # 增强字段通过 raw SQL 写入（避免 ORM 字段未定义）
        if plan_id or saga_id or snapshot_json:
            updates = []
            params: dict = {"id": log_id}
            if plan_id:
                updates.append("plan_id = :plan_id")
                params["plan_id"] = plan_id
            if saga_id:
                updates.append("saga_id = :saga_id")
                params["saga_id"] = saga_id
            if snapshot_json:
                updates.append("state_snapshot = :state_snapshot")
                params["state_snapshot"] = snapshot_json
            set_clause = ", ".join(updates)
            db.execute(
                text(f"UPDATE event_logs SET {set_clause} WHERE id = :id"),
                params,
            )

        return log_id

    @staticmethod
    def get_timeline(
        plan_id: str,
        db: Optional[Session] = None,
        limit: int = 200,
    ) -> List[dict]:
        """获取某个 ProductPlan 的完整事件时间线"""
        close_db = db is None
        if db is None:
            db = SessionLocal()
        try:
            EventStore._ensure_columns(db)
            rows = db.execute(
                text("""
                    SELECT id, event_type, event_version, payload,
                           state_snapshot, created_at, status, plan_id
                    FROM event_logs
                    WHERE plan_id = :plan_id
                    ORDER BY created_at ASC
                    LIMIT :lim
                """),
                {"plan_id": plan_id, "lim": limit},
            ).fetchall()

            result = []
            for r in rows:
                item = {
                    "id": r[0],
                    "event_type": r[1],
                    "event_version": r[2],
                    "payload": json.loads(r[3]) if r[3] else {},
                    "state_snapshot": json.loads(r[4]) if r[4] else None,
                    "created_at": _safe_iso(r[5]),
                    "status": r[6],
                    "plan_id": r[7],
                }
                result.append(item)
            return result
        finally:
            if close_db:
                db.close()

    @staticmethod
    def replay(
        plan_id: str,
        until_event_id: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> Tuple[bool, dict]:
        """重放 ProductPlan 事件，重建最终状态"""
        close_db = db is None
        if db is None:
            db = SessionLocal()
        try:
            EventStore._ensure_columns(db)

            if until_event_id:
                rows = db.execute(
                    text("""
                        SELECT id, event_type, event_version, payload,
                               state_snapshot, created_at, status, plan_id
                        FROM event_logs
                        WHERE plan_id = :plan_id AND id <= :until
                        ORDER BY created_at ASC
                    """),
                    {"plan_id": plan_id, "until": until_event_id},
                ).fetchall()
            else:
                rows = db.execute(
                    text("""
                        SELECT id, event_type, event_version, payload,
                               state_snapshot, created_at, status, plan_id
                        FROM event_logs
                        WHERE plan_id = :plan_id
                        ORDER BY created_at ASC
                    """),
                    {"plan_id": plan_id},
                ).fetchall()

            if not rows:
                return False, {"error": f"No events for plan_id={plan_id}"}

            state = {
                "plan_id": plan_id,
                "current_stage": None,
                "status": "unknown",
                "events_count": len(rows),
            }

            # 找最新的 state_snapshot 作为起始状态
            snapshot_idx = -1
            for i in range(len(rows) - 1, -1, -1):
                snapshot_raw = rows[i][4]  # state_snapshot
                if snapshot_raw:
                    try:
                        snap = json.loads(snapshot_raw)
                        if isinstance(snap, dict):
                            state.update(snap)
                            snapshot_idx = i
                            break
                    except (json.JSONDecodeError, TypeError):
                        continue

            # 从 snapshot 之后的事件增量回放
            replay_count = 0
            for i in range(snapshot_idx + 1, len(rows)):
                r = rows[i]
                try:
                    payload = json.loads(r[3]) if r[3] else {}
                except (json.JSONDecodeError, TypeError):
                    payload = {}

                event_name = r[1].split(".")[-1] if "." in r[1] else r[1]

                if event_name in ("approved",):
                    state["status"] = "approved"
                elif event_name in ("released",):
                    state["status"] = "released"
                elif event_name in ("competitor_done", "definition_done", "costing_done",
                                     "tech_input_done", "project_init_done"):
                    stage_map = {
                        "competitor_done": "竞品分析",
                        "definition_done": "产品定义",
                        "costing_done": "成本核算",
                        "tech_input_done": "技术输入",
                        "project_init_done": "项目初始化",
                    }
                    state["current_stage"] = stage_map.get(event_name, event_name)
                    if state.get("status") == "unknown":
                        state["status"] = "in_progress"

                if payload.get("plan_name"):
                    state["plan_name"] = payload["plan_name"]
                if payload.get("new_stage"):
                    state["current_stage"] = payload["new_stage"]
                if payload.get("status"):
                    state["status"] = payload["status"]

                replay_count += 1
                state["last_event"] = {
                    "id": r[0],
                    "type": r[1],
                    "at": _safe_iso(r[5]),
                }

            state["replayed_from_snapshot"] = snapshot_idx >= 0
            state["replay_count"] = replay_count
            logger.info("Replay plan=%s: %d events, from_snapshot=%s → status=%s",
                        plan_id, len(rows), snapshot_idx >= 0, state.get("status"))
            return True, state
        except Exception as e:
            logger.exception("Replay 失败: plan_id=%s", plan_id)
            return False, {"error": str(e)}
        finally:
            if close_db:
                db.close()

    @staticmethod
    def rebuild_all(
        db: Optional[Session] = None,
    ) -> List[dict]:
        """重建所有 ProductPlan 的当前状态"""
        close_db = db is None
        if db is None:
            db = SessionLocal()
        try:
            EventStore._ensure_columns(db)
            rows = db.execute(
                text("SELECT DISTINCT plan_id FROM event_logs WHERE plan_id IS NOT NULL"),
            ).fetchall()
            plan_ids = [r[0] for r in rows]

            results = []
            for pid in plan_ids:
                success, state = EventStore.replay(pid, db=db)
                if success:
                    results.append(state)
            return results
        finally:
            if close_db:
                db.close()

    # ════════════════════════════════════════════════════════
    # 新增: 分页时间线 + Saga 链 + 快照差异
    # ════════════════════════════════════════════════════════

    @staticmethod
    def paginated_timeline(
        plan_id: str,
        page: int = 1,
        page_size: int = 50,
        event_type: Optional[str] = None,
        status: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> dict:
        """分页查询事件时间线，支持按 event_type / status 过滤

        Returns:
            dict: {"items": [...], "total": int, "page": int, "page_size": int}
        """
        close_db = db is None
        if db is None:
            db = SessionLocal()
        try:
            EventStore._ensure_columns(db)

            # 构建 WHERE 条件
            conditions = "WHERE plan_id = :plan_id"
            params: dict = {"plan_id": plan_id}

            if event_type:
                conditions += " AND event_type = :event_type"
                params["event_type"] = event_type
            if status:
                conditions += " AND status = :status"
                params["status"] = status

            # 总数
            count_sql = text(f"SELECT COUNT(*) FROM event_logs {conditions}")
            total = db.execute(count_sql, params).scalar() or 0

            # 分页数据
            offset = (page - 1) * page_size
            data_sql = text(f"""
                SELECT id, event_type, event_version, payload,
                       state_snapshot, created_at, status, plan_id, saga_id
                FROM event_logs
                {conditions}
                ORDER BY created_at ASC
                LIMIT :limit OFFSET :offset
            """)
            params["limit"] = page_size
            params["offset"] = offset
            rows = db.execute(data_sql, params).fetchall()

            items = []
            for r in rows:
                items.append({
                    "id": r[0],
                    "event_type": r[1],
                    "event_version": r[2],
                    "payload": json.loads(r[3]) if r[3] else {},
                    "state_snapshot": json.loads(r[4]) if r[4] else None,
                    "created_at": _safe_iso(r[5]),
                    "status": r[6],
                    "plan_id": r[7],
                    "saga_id": r[8],
                })

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
            }
        finally:
            if close_db:
                db.close()

    @staticmethod
    def get_saga_chain(
        saga_id: str,
        db: Optional[Session] = None,
    ) -> List[dict]:
        """按 saga_id 查询完整步骤链（按时间升序）"""
        close_db = db is None
        if db is None:
            db = SessionLocal()
        try:
            EventStore._ensure_columns(db)
            rows = db.execute(
                text("""
                    SELECT id, event_type, event_version, payload,
                           state_snapshot, created_at, status, plan_id, saga_id
                    FROM event_logs
                    WHERE saga_id = :saga_id
                    ORDER BY created_at ASC
                """),
                {"saga_id": saga_id},
            ).fetchall()

            result = []
            for r in rows:
                result.append({
                    "id": r[0],
                    "event_type": r[1],
                    "event_version": r[2],
                    "payload": json.loads(r[3]) if r[3] else {},
                    "state_snapshot": json.loads(r[4]) if r[4] else None,
                    "created_at": _safe_iso(r[5]),
                    "status": r[6],
                    "plan_id": r[7],
                    "saga_id": r[8],
                })
            return result
        finally:
            if close_db:
                db.close()

    @staticmethod
    def get_snapshot_diff_for_event(
        event_id: int,
        db: Optional[Session] = None,
    ) -> Optional[dict]:
        """获取某个事件前后的状态快照差异

        对比该事件的 state_snapshot 与上一个同 plan_id 事件的 state_snapshot，
        返回差异字段列表及前后值。
        """
        close_db = db is None
        if db is None:
            db = SessionLocal()
        try:
            EventStore._ensure_columns(db)

            # 获取当前事件
            row = db.execute(
                text("""
                    SELECT id, event_type, plan_id, state_snapshot, created_at
                    FROM event_logs
                    WHERE id = :eid
                """),
                {"eid": event_id},
            ).fetchone()
            if not row:
                return None

            event_id_val, event_type, plan_id, snapshot_raw, created_at = row
            current_snapshot = json.loads(snapshot_raw) if snapshot_raw else {}

            # 没有 plan_id → 无法找到前一个事件
            if not plan_id:
                return {
                    "event_id": event_id_val,
                    "event_type": event_type,
                    "created_at": _safe_iso(created_at),
                    "previous_snapshot": None,
                    "current_snapshot": current_snapshot,
                    "diff": [],
                    "note": "该事件无关联 plan_id，无法计算前后差异",
                }

            # 找上一个有 state_snapshot 的事件（同 plan_id，id < 当前）
            prev_row = db.execute(
                text("""
                    SELECT id, state_snapshot
                    FROM event_logs
                    WHERE plan_id = :plan_id AND id < :eid AND state_snapshot IS NOT NULL
                    ORDER BY id DESC
                    LIMIT 1
                """),
                {"plan_id": plan_id, "eid": event_id_val},
            ).fetchone()

            prev_snapshot = {}
            prev_id = None
            if prev_row:
                prev_id = prev_row[0]
                prev_snapshot = json.loads(prev_row[1]) if prev_row[1] else {}

            # 计算差异
            diff = []
            all_keys = set(list(prev_snapshot.keys()) + list(current_snapshot.keys()))
            for key in sorted(all_keys):
                old_val = prev_snapshot.get(key)
                new_val = current_snapshot.get(key)
                if old_val != new_val:
                    diff.append({
                        "field": key,
                        "before": old_val,
                        "after": new_val,
                    })

            return {
                "event_id": event_id_val,
                "event_type": event_type,
                "created_at": _safe_iso(created_at),
                "previous_event_id": prev_id,
                "previous_snapshot": prev_snapshot,
                "current_snapshot": current_snapshot,
                "diff": diff,
            }
        finally:
            if close_db:
                db.close()


# 模块级单例
event_store = EventStore()
