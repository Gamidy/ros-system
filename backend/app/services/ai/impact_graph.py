"""M2 Impact Graph Engine — 变更传播图引擎

职责：给定一个 ECR/ECO，构建变更影响 DAG，计算传播路径和 ripple effect。

图拓扑:
  ECR/ECO → Prototype → BOM → Certification → Manufacturing → Cost

核心能力:
  ✅ DAG 构建 (ECR/ECO → Prototype → BOM → Certification → Manufacturing → Cost)
  ✅ BFS 遍历传播链 + 环检测
  ✅ Ripple effect 计算 (0-100)
  ✅ DAG 输出可序列化 JSON
  ❌ 不允许 free-text 输出
  ❌ 不允许修改 Risk Score (M1 的职责)

全类型注解，无 Any。
"""
import json
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.ecr_eco import ECRRequest, ECO, ECOItem
from app.models.change_impact import ChangeImpactRule, ChangeImpactRecord
from app.models.ci_v2_impact import ImpactGraphSnapshot
from app.schemas.ci_v2 import ImpactNode, ImpactEdge, ImpactGraphOut, RipplePath

logger = logging.getLogger(__name__)

# 默认传播拓扑权重 (source_type → target_type → weight)
_DEFAULT_PROPAGATION_WEIGHTS: dict[str, dict[str, float]] = {
    "ecr": {"eco": 1.0, "prototype": 0.8},
    "eco": {"prototype": 0.9, "bom": 0.7},
    "prototype": {"bom": 0.8, "certification": 0.6},
    "bom": {"certification": 0.7, "manufacturing": 0.5},
    "certification": {"manufacturing": 0.8, "cost": 0.4},
    "manufacturing": {"cost": 0.6},
}

# impact_level → numeric score for ripple calculation
_IMPACT_LEVEL_SCORE: dict[str, float] = {
    "critical": 1.0,
    "major": 0.7,
    "minor": 0.3,
    "none": 0.0,
}


class ImpactGraphEngine:
    """变更传播图引擎

    图拓扑:
    ECR/ECO → Prototype → BOM → Certification → Manufacturing → Cost

    遍历策略: BFS, 最大深度5层, 防止无限循环
    """

    MAX_DEPTH = 5
    NODE_TYPES = ["ecr", "eco", "prototype", "bom", "certification", "manufacturing", "cost"]

    @staticmethod
    def build_graph(ecr_id: int, db: Session) -> ImpactGraphOut:
        """从 ECR 出发构建完整影响图

        步骤:
        1. 查询 ECOItem 获取变更对象类型和范围
        2. 查询 ChangeImpactRule 获取影响规则
        3. 查询 ChangeImpactRecord 获取历史影响
        4. 构建 DAG
        5. BFS 遍历计算传播路径
        6. 计算 ripple_score
        7. 持久化 ImpactGraphSnapshot
        8. 返回 ImpactGraphOut
        """
        # 1. 查询 ECR
        ecr = db.query(ECRRequest).filter(ECRRequest.id == ecr_id).first()
        if ecr is None:
            logger.warning("ECR %s not found, returning empty graph", ecr_id)
            return ImpactGraphOut(
                nodes=[], edges=[], ripple_score=0.0, max_depth=0,
                node_count=0, edge_count=0,
            )

        # 2. 查询关联 ECO
        eco_list: list[ECO] = []
        if ecr.eco is not None:
            eco_list = [ecr.eco]

        # 3. 查询 ECOItem
        eco_items: list[ECOItem] = []
        for eco in eco_list:
            eco_items.extend(eco.items)

        # 4. 查询 ChangeImpactRecord 用于此 ecr_id
        impact_records = (
            db.query(ChangeImpactRecord)
            .filter(ChangeImpactRecord.ecr_id == ecr_id)
            .all()
        )

        # 5. 查询 ChangeImpactRule
        active_rules = (
            db.query(ChangeImpactRule)
            .filter(ChangeImpactRule.is_active.is_(True))
            .all()
        )

        # 6. 构建 nodes / edges
        nodes_map: dict[str, ImpactNode] = {}
        edges_list: list[ImpactEdge] = []
        visited: set[str] = set()

        # 6a. 创建根节点 ECR
        ecr_impact_score = ImpactGraphEngine._urgency_to_score(ecr.urgency)
        ecr_node_id = f"ecr_{ecr.id}"
        nodes_map[ecr_node_id] = ImpactNode(
            id=ecr_node_id,
            node_type="ecr",
            label=f"ECR: {ecr.code or ecr.title}",
            impact_score=ecr_impact_score,
            affected_objects=[{"id": ecr.id, "code": ecr.code, "title": ecr.title}],
            depth=0,
        )
        visited.add(ecr_node_id)

        # 6b. 创建 ECO 节点 并连接 ECR→ECO
        for eco in eco_list:
            eco_node_id = f"eco_{eco.id}"
            if eco_node_id not in visited:
                nodes_map[eco_node_id] = ImpactNode(
                    id=eco_node_id,
                    node_type="eco",
                    label=f"ECO: {eco.code or eco.title}",
                    impact_score=ImpactGraphEngine._urgency_to_score(eco.status),
                    affected_objects=[{"id": eco.id, "code": eco.code, "title": eco.title}],
                    depth=1,
                )
                visited.add(eco_node_id)

            # 边 ECR → ECO
            weight = ImpactGraphEngine._get_propagation_weight("ecr", "eco")
            edges_list.append(ImpactEdge(
                source_id=ecr_node_id,
                target_id=eco_node_id,
                weight=weight,
                label=f"{ecr.code or ecr.title} → {eco.code or eco.title}",
            ))

            # 6c. 根据 ECOItems 创建下游节点
            for item in eco_items:
                obj_type_str = str(item.object_type or "other")

                # 根据 object_type 决定传播到哪个下游域
                downstream_types = ImpactGraphEngine._map_object_type_to_downstream(obj_type_str)
                last_ds_type: Optional[str] = None
                for ds_type, ds_label in downstream_types:
                    last_ds_type = ds_type
                    ds_node_id = f"{ds_type}_{eco.id}_{item.id}"
                    if ds_node_id not in visited:
                        ds_score = ImpactGraphEngine._compute_item_impact(
                            item, active_rules, impact_records,
                        )
                        nodes_map[ds_node_id] = ImpactNode(
                            id=ds_node_id,
                            node_type=ds_type,
                            label=ds_label,
                            impact_score=ds_score,
                            affected_objects=[{
                                "id": item.id,
                                "object_type": str(item.object_type or ""),
                                "object_code": str(item.object_code or ""),
                                "object_name": str(item.object_name or ""),
                                "change_type": str(item.change_type or ""),
                            }],
                            depth=2,
                        )
                        visited.add(ds_node_id)

                    # 边 ECO → 下游
                    weight = ImpactGraphEngine._get_propagation_weight("eco", ds_type)
                    edges_list.append(ImpactEdge(
                        source_id=eco_node_id,
                        target_id=ds_node_id,
                        weight=weight,
                        label=f"ECO → {ds_type}",
                    ))

                # 6d. 从下游继续传播到更深的层 (depth 3~5)
                if last_ds_type is not None:
                    ImpactGraphEngine._expand_downstream(
                        last_ds_type, eco_node_id, eco, item,
                        nodes_map, edges_list, visited, 2,
                        active_rules, impact_records,
                    )

        # 7. BFS 遍历计算传播路径
        paths = ImpactGraphEngine.bfs_traverse(nodes_map, edges_list, ecr_node_id, ImpactGraphEngine.MAX_DEPTH)

        # 8. 计算 ripple_score
        ripple_score = ImpactGraphEngine.calculate_ripple_score(paths)

        # 9. 统计
        node_count = len(nodes_map)
        edge_count = len(edges_list)
        max_depth = max((n.depth for n in nodes_map.values()), default=0)

        # 10. 持久化快照
        graph_out = ImpactGraphOut(
            nodes=list(nodes_map.values()),
            edges=edges_list,
            ripple_score=round(ripple_score, 2),
            max_depth=max_depth,
            node_count=node_count,
            edge_count=edge_count,
        )
        snapshot = ImpactGraphSnapshot(
            ecr_id=ecr_id,
            graph_data=graph_out.model_dump(),
            ripple_score=round(ripple_score, 2),
            node_count=node_count,
            edge_count=edge_count,
            max_depth=max_depth,
        )
        db.add(snapshot)
        db.commit()

        return graph_out

    # ─── 私有辅助方法 ──────────────────────────────────────────────────

    @staticmethod
    def _map_object_type_to_downstream(object_type: str) -> list[tuple[str, str]]:
        """根据 ECOItem.object_type 映射到下游图节点类型"""
        mapping: dict[str, list[tuple[str, str]]] = {
            "part": [("prototype", "样机变更"), ("bom", "BOM变更")],
            "bom": [("bom", "BOM变更"), ("manufacturing", "制造变更")],
            "certification": [("certification", "认证变更"), ("manufacturing", "制造变更")],
            "document": [("prototype", "文档变更")],
            "process": [("manufacturing", "工艺变更")],
            "other": [("prototype", "其他变更")],
        }
        return mapping.get(object_type, [("prototype", "变更传播")])

    @staticmethod
    def _expand_downstream(
        current_type: str,
        eco_node_id: str,
        eco: ECO,
        item: ECOItem,
        nodes_map: dict[str, ImpactNode],
        edges_list: list[ImpactEdge],
        visited: set[str],
        depth: int,
        active_rules: list[ChangeImpactRule],
        impact_records: list[ChangeImpactRecord],
    ) -> None:
        """递归扩展下游节点 (depth+1) 直到 MAX_DEPTH"""
        if depth >= ImpactGraphEngine.MAX_DEPTH:
            return

        model_type = ImpactGraphEngine._map_node_type_to_model(current_type)
        if model_type is None:
            return

        # 从当前类型向下游传播
        propagation_map: dict[str, list[str]] = {
            "prototype": ["bom", "certification"],
            "bom": ["certification", "manufacturing"],
            "certification": ["manufacturing", "cost"],
            "manufacturing": ["cost"],
        }
        next_types = propagation_map.get(model_type, [])
        for next_type in next_types:
            child_id = f"{next_type}_{eco.id}_{item.id}_{depth}"
            if child_id in visited:
                continue

            ds_score = ImpactGraphEngine._compute_item_impact(item, active_rules, impact_records)
            nodes_map[child_id] = ImpactNode(
                id=child_id,
                node_type=next_type,
                label=f"{next_type.capitalize()} (from {model_type})",
                impact_score=ds_score,
                affected_objects=[{
                    "id": item.id,
                    "object_type": item.object_type,
                    "object_code": item.object_code,
                    "object_name": item.object_name,
                }],
                depth=depth + 1,
            )
            visited.add(child_id)

            weight = ImpactGraphEngine._get_propagation_weight(model_type, next_type)
            edges_list.append(ImpactEdge(
                source_id=eco_node_id if depth == 2 else f"{model_type}_{eco.id}_{item.id}_{depth - 1}",
                target_id=child_id,
                weight=weight,
                label=f"{model_type} → {next_type}",
            ))

            # 递归扩展
            ImpactGraphEngine._expand_downstream(
                next_type, eco_node_id, eco, item, nodes_map, edges_list, visited,
                depth + 1, active_rules, impact_records,
            )

    @staticmethod
    def _map_node_type_to_model(node_type: str) -> Optional[str]:
        """将节点类型映射到传播拓扑中的模型名"""
        valid = {"prototype", "bom", "certification", "manufacturing", "cost"}
        if node_type in valid:
            return node_type
        if node_type in ("ecr", "eco"):
            return None  # 根节点不参与下游扩展
        return None

    @staticmethod
    def _get_propagation_weight(source_type: str, target_type: str) -> float:
        """获取两类型之间的默认传播权重"""
        source_rules = _DEFAULT_PROPAGATION_WEIGHTS.get(source_type, {})
        return source_rules.get(target_type, 0.3)

    @staticmethod
    def _urgency_to_score(urgency_or_status: object) -> float:
        """根据 ECR urgency 或 ECO status 转为影响分数 (0-1)
        接受 str 或 SQLAlchemy Column，容错处理"""
        val = str(urgency_or_status) if urgency_or_status is not None else ""
        urgency_map: dict[str, float] = {
            "emergency": 1.0,
            "high": 0.8,
            "medium": 0.5,
            "low": 0.2,
        }
        status_map: dict[str, float] = {
            "implementing": 0.7,
            "effective": 0.6,
            "verified": 0.5,
            "closed": 0.3,
            "cancelled": 0.1,
            "draft": 0.4,
        }
        if val in urgency_map:
            return urgency_map[val]
        if val in status_map:
            return status_map[val]
        return 0.5

    @staticmethod
    def _compute_item_impact(
        item: ECOItem,
        active_rules: list[ChangeImpactRule],
        impact_records: list[ChangeImpactRecord],
    ) -> float:
        """计算某个 ECOItem 的影响分数

        综合规则匹配和历史记录，分数 0-1。
        """
        item_obj_type = str(item.object_type or "")
        item_obj_code = str(item.object_code or "")
        item_obj_name = str(item.object_name or "")
        item_change_type = str(item.change_type or "modify")

        # matched rules from object_type
        rule_score = 0.0
        for rule in active_rules:
            trigger_val = str(rule.trigger_value or "")
            impact_lvl = str(rule.impact_level or "")
            if trigger_val and item_obj_type and trigger_val in item_obj_type:
                rule_score = max(rule_score, _IMPACT_LEVEL_SCORE.get(impact_lvl, 0.5))
            if trigger_val and item_obj_code and trigger_val in item_obj_code:
                rule_score = max(rule_score, _IMPACT_LEVEL_SCORE.get(impact_lvl, 0.5))

        # matched records
        record_score = 0.0
        for rec in impact_records:
            changed_part = str(rec.changed_part or "")
            impact_lvl = str(rec.impact_level or "")
            if changed_part and item_obj_name and changed_part in item_obj_name:
                record_score = max(record_score, _IMPACT_LEVEL_SCORE.get(impact_lvl, 0.5))

        # 综合取最大值
        combined = max(rule_score, record_score)
        if combined > 0.0:
            return combined
        # 默认: 根据 change_type 推断
        change_score: dict[str, float] = {
            "add": 0.6,
            "modify": 0.4,
            "replace": 0.7,
            "delete": 0.5,
            "disable": 0.3,
        }
        return change_score.get(item_change_type, 0.4)

    @staticmethod
    def bfs_traverse(
        nodes: dict[str, ImpactNode],
        edges: list[ImpactEdge],
        start_node_id: str,
        max_depth: int = 5,
    ) -> list[RipplePath]:
        """BFS 遍历传播链，返回所有可达路径（含环检测）

        Args:
            nodes: 节点字典 {id: ImpactNode}
            edges: 边列表
            start_node_id: 起始节点ID
            max_depth: 最大深度限制

        Returns:
            list[RipplePath] — 从根到叶子的所有路径
        """
        if start_node_id not in nodes:
            return []

        # 构建邻接表
        adjacency: dict[str, list[tuple[str, float]]] = {nid: [] for nid in nodes}
        for edge in edges:
            if edge.source_id in adjacency and edge.target_id in adjacency:
                adjacency[edge.source_id].append((edge.target_id, edge.weight))

        paths: list[RipplePath] = []
        # BFS queue: (current_node_id, path_so_far, score_so_far, path_set)
        queue: deque[tuple[str, list[str], float, set[str], int]] = deque()
        queue.append((start_node_id, [start_node_id], 0.0, {start_node_id}, 0))

        while queue:
            current, path, score, path_set, depth = queue.popleft()

            neighbors = adjacency.get(current, [])
            if not neighbors or depth >= max_depth:
                # leaf node or max depth reached → record path
                paths.append(RipplePath(
                    path=list(path),
                    total_score=round(score, 4),
                    node_count=len(path),
                ))
                continue

            appended_any = False
            for neighbor, weight in neighbors:
                # 环检测: 如果 neighbor 已在当前路径中则跳过
                if neighbor in path_set:
                    continue

                appended_any = True
                neighbor_score = nodes.get(neighbor)
                node_score = neighbor_score.impact_score if neighbor_score else 0.0
                edge_contribution = weight * node_score
                new_path = path + [neighbor]
                new_set = set(path_set)
                new_set.add(neighbor)
                queue.append((
                    neighbor,
                    new_path,
                    score + edge_contribution,
                    new_set,
                    depth + 1,
                ))

            # 所有邻居都因环检测被跳过 → 当前节点视为叶子
            if not appended_any:
                paths.append(RipplePath(
                    path=list(path),
                    total_score=round(score, 4),
                    node_count=len(path),
                ))

        return paths

    @staticmethod
    def calculate_ripple_score(paths: list[RipplePath]) -> float:
        """根据传播路径计算整体 ripple effect score (0-100)

        计算公式:
          Σ(avg_score * depth_weight) * (1 + path_count / 10) / path_count
          归一化到 0-100

        Args:
            paths: BFS 遍历出的所有路径

        Returns:
            float — 0-100 的 ripple score
        """
        if not paths:
            return 0.0

        total_weighted = 0.0
        max_possible_depth = 5  # 理论最大深度
        path_count = len(paths)

        for p in paths:
            if p.node_count == 0:
                continue
            # 每条路径的贡献: total_score 除以节点数 (平均每节点影响)
            avg_score = p.total_score / p.node_count
            # 深度权重: 路径越长权重越高 (达到更深远的影响)
            depth_weight = p.node_count / max_possible_depth
            total_weighted += avg_score * depth_weight

        # 路径数量奖励: 分支越多 ripple 越大
        branch_factor = 1.0 + (path_count / 10.0)  # 10条路径 = +1.0倍

        raw_score = (total_weighted / max(path_count, 1)) * branch_factor

        # 归一化到 0-100
        normalized = min(raw_score * 25.0, 100.0)
        return round(normalized, 2)
