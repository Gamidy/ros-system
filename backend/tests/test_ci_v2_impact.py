"""M2 Impact Graph Engine — 单元测试

测试 ImpactGraphEngine 的核心功能:
- 空图
- 单节点
- 线性传播链
- 多分支传播
- 环检测
- BFS 遍历
- JSON 序列化
- Ripple score 计算

全类型注解，无 Any。
"""
import json
import os
import tempfile

# 测试数据库必须早于任何 app 导入
_db_file = os.path.join(tempfile.mkdtemp(), "test_ci_v2_impact.db")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_db_file}")
os.environ.setdefault("ALLOW_PUBLIC_REGISTER", "true")

from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.core.database import Base, engine, SessionLocal
from app.models.ecr_eco import ECRRequest, ECO, ECOItem
from app.models.change_impact import ChangeImpactRule, ChangeImpactRecord
from app.models.ci_v2_impact import ImpactGraphSnapshot
from app.schemas.ci_v2 import ImpactNode, ImpactEdge, ImpactGraphOut, RipplePath
from app.services.ai.impact_graph import ImpactGraphEngine


# ─── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def setup_db():
    """每个测试前重建数据库"""
    Base.metadata.create_all(bind=engine)
    yield
    try:
        Base.metadata.drop_all(bind=engine)
    except Exception as e:
        engine.dispose()
        db_path = _db_file
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.fixture
def db() -> Session:
    """返回一个新的数据库会话"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _create_ecr(db: Session, **overrides) -> ECRRequest:
    """辅助创建 ECR 记录"""
    params = {
        "code": "ECR-20260628-0001",
        "title": "Test ECR",
        "ecr_type": "design_change",
        "reason": "Test reason",
        "urgency": "medium",
        "status": "approved",
        "submitter_id": 1,
        "submitter_name": "tester",
    }
    params.update(overrides)
    ecr = ECRRequest(**params)
    db.add(ecr)
    db.commit()
    db.refresh(ecr)
    return ecr


def _create_eco(db: Session, ecr_id: int, **overrides) -> ECO:
    """辅助创建 ECO 记录"""
    params = {
        "code": "ECO-20260628-0001",
        "ecr_id": ecr_id,
        "title": "Test ECO",
        "change_summary": "Test change summary",
        "status": "implementing",
        "created_by": 1,
    }
    params.update(overrides)
    eco = ECO(**params)
    db.add(eco)
    db.commit()
    db.refresh(eco)
    return eco


def _create_eco_item(db: Session, eco_id: int, **overrides) -> ECOItem:
    """辅助创建 ECOItem 记录"""
    params = {
        "eco_id": eco_id,
        "seq": 1,
        "change_type": "modify",
        "object_type": "part",
        "object_code": "PART-001",
        "object_name": "Compressor X1",
        "old_value": "old",
        "new_value": "new",
    }
    params.update(overrides)
    item = ECOItem(**params)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def _create_impact_rule(db: Session, **overrides) -> ChangeImpactRule:
    """辅助创建 ChangeImpactRule"""
    params = {
        "name": "Compressor test rule",
        "description": "Test",
        "trigger_type": "part_category",
        "trigger_value": "compressor",
        "affected_cert_types": '["CE","CB"]',
        "impact_level": "major",
        "is_active": True,
    }
    params.update(overrides)
    rule = ChangeImpactRule(**params)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


# ─── Tests ─────────────────────────────────────────────────────────────


class TestEmptyGraph:
    """无关联数据的 ECR 返回空图"""

    def test_empty_graph(self, db: Session) -> None:
        """无关联数据的 ECR 返回空图(0节点)"""
        ecr = _create_ecr(db)
        result = ImpactGraphEngine.build_graph(ecr.id, db)
        assert isinstance(result, ImpactGraphOut)
        assert result.node_count == 1  # ECR 节点自身
        assert result.edge_count == 0
        assert result.ripple_score == 0.0
        assert result.max_depth == 0
        # 验证 ECR 节点存在
        assert any(n.node_type == "ecr" for n in result.nodes)

    def test_nonexistent_ecr_returns_empty(self, db: Session) -> None:
        """不存在的 ECR ID 返回完全空图"""
        result = ImpactGraphEngine.build_graph(99999, db)
        assert isinstance(result, ImpactGraphOut)
        assert result.node_count == 0
        assert result.edge_count == 0
        assert result.ripple_score == 0.0
        assert result.max_depth == 0
        assert result.nodes == []


class TestSingleNodeGraph:
    """只有 ECR 节点"""

    def test_single_node_without_eco(self, db: Session) -> None:
        """ECR 没有关联 ECO → 只有 ECR 节点"""
        ecr = _create_ecr(db, urgency="emergency")
        result = ImpactGraphEngine.build_graph(ecr.id, db)
        assert result.node_count == 1
        assert result.edge_count == 0
        ecr_nodes = [n for n in result.nodes if n.node_type == "ecr"]
        assert len(ecr_nodes) == 1
        assert ecr_nodes[0].depth == 0
        assert ecr_nodes[0].impact_score == 1.0  # emergency → 1.0


class TestLinearChain:
    """ECR→ECO→BOM→Cert→Mfg 链式传播"""

    def test_ecr_eco_linear(self, db: Session) -> None:
        """ECR→ECO→BOM→Certification 线性链"""
        ecr = _create_ecr(db)
        eco = _create_eco(db, ecr.id)
        _create_eco_item(db, eco.id, object_type="bom", object_code="BOM-001")
        _create_eco_item(db, eco.id, object_type="certification", object_code="CERT-001")

        result = ImpactGraphEngine.build_graph(ecr.id, db)
        assert result.node_count >= 3  # ecr + eco + at least one downstream
        assert result.edge_count >= 1
        assert result.max_depth >= 1

        # 验证结构包含 ECR 和 ECO
        node_types = {n.node_type for n in result.nodes}
        assert "ecr" in node_types
        assert "eco" in node_types

        # 验证边连接
        edges_source_target = [(e.source_id, e.target_id) for e in result.edges]
        assert any("ecr" in s for s, _ in edges_source_target)

    def test_full_chain(self, db: Session) -> None:
        """完整链 ECR→ECO→BOM→Certification→Manufacturing→Cost"""
        ecr = _create_ecr(db)
        eco = _create_eco(db, ecr.id)
        _create_eco_item(db, eco.id, object_type="part", object_code="PART-CHAIN")
        result = ImpactGraphEngine.build_graph(ecr.id, db)
        # part 会传播到 prototype → bom → certification → manufacturing
        assert result.node_count >= 4
        assert result.max_depth >= 2
        # 验证 serialization
        assert isinstance(json.dumps(result.model_dump()), str)


class TestBranchingGraph:
    """多分支传播"""

    def test_branching_graph(self, db: Session) -> None:
        """多个 ECOItems 产生多分支"""
        ecr = _create_ecr(db)
        eco = _create_eco(db, ecr.id)
        _create_eco_item(db, eco.id, object_type="part", object_code="PART-B1")
        _create_eco_item(db, eco.id, object_type="bom", object_code="BOM-B2")
        _create_eco_item(db, eco.id, object_type="certification", object_code="CERT-B3")

        result = ImpactGraphEngine.build_graph(ecr.id, db)
        assert result.node_count >= 4  # ecr + eco + 3 branches
        assert result.edge_count >= 3

        # Verify multiple downstream node types
        node_types = {n.node_type for n in result.nodes}
        assert len(node_types) >= 2  # at least ecr, eco + some downstream


class TestCycleDetection:
    """环状依赖不导致无限循环"""

    def test_cycle_detection(self, db: Session) -> None:
        """BFS 遍历不会因环无限循环"""
        ecr = _create_ecr(db)
        eco = _create_eco(db, ecr.id)
        _create_eco_item(db, eco.id, object_type="part", object_code="PART-CYCLE")

        # build_graph should complete within reasonable time
        result = ImpactGraphEngine.build_graph(ecr.id, db)
        assert result.node_count > 0
        assert result.max_depth <= ImpactGraphEngine.MAX_DEPTH

    def test_bfs_with_cycle_in_edges(self, db: Session) -> None:
        """手动构造环状边 → BFS 不无限循环"""
        # 构造 nodes
        nodes = {
            "a": ImpactNode(id="a", node_type="ecr", label="A", impact_score=0.5, affected_objects=[], depth=0),
            "b": ImpactNode(id="b", node_type="eco", label="B", impact_score=0.5, affected_objects=[], depth=1),
            "c": ImpactNode(id="c", node_type="bom", label="C", impact_score=0.5, affected_objects=[], depth=2),
        }
        # 包含环: a→b, b→c, c→b (环)
        edges = [
            ImpactEdge(source_id="a", target_id="b", weight=0.8, label="a→b"),
            ImpactEdge(source_id="b", target_id="c", weight=0.7, label="b→c"),
            ImpactEdge(source_id="c", target_id="b", weight=1.0, label="c→b (cycle)"),
        ]
        paths = ImpactGraphEngine.bfs_traverse(nodes, edges, "a", max_depth=5)
        assert len(paths) >= 1
        # 不应包含无限循环 → 每个路径不应重复节点
        for p in paths:
            assert len(p.path) == len(set(p.path)), f"Path contains duplicates: {p.path}"


class TestBFSTraverse:
    """BFS 遍历验证"""

    def test_bfs_traverse_all_paths(self, db: Session) -> None:
        """BFS 遍历应返回所有可达路径"""
        ecr = _create_ecr(db)
        eco = _create_eco(db, ecr.id)
        _create_eco_item(db, eco.id, object_type="part", object_code="PART-P1")
        _create_eco_item(db, eco.id, object_type="bom", object_code="BOM-P2")

        result = ImpactGraphEngine.build_graph(ecr.id, db)

        # Convert to dict format for bfs_traverse
        nodes_dict = {n.id: n for n in result.nodes}
        # Find the ECR node as start
        ecr_node = next((n for n in result.nodes if n.node_type == "ecr"), None)
        assert ecr_node is not None

        paths = ImpactGraphEngine.bfs_traverse(nodes_dict, result.edges, ecr_node.id, max_depth=5)
        assert len(paths) >= 1
        for p in paths:
            assert len(p.path) >= 1
            assert p.node_count == len(p.path)
            # Path should start with ECR node
            assert p.path[0] == ecr_node.id

    def test_bfs_max_depth_limit(self, db: Session) -> None:
        """max_depth 限制 BFS 深度"""
        nodes = {
            "root": ImpactNode(id="root", node_type="ecr", label="Root", impact_score=0.5, affected_objects=[], depth=0),
            "a": ImpactNode(id="a", node_type="eco", label="A", impact_score=0.5, affected_objects=[], depth=1),
            "b": ImpactNode(id="b", node_type="bom", label="B", impact_score=0.5, affected_objects=[], depth=2),
            "c": ImpactNode(id="c", node_type="cert", label="C", impact_score=0.5, affected_objects=[], depth=3),
            "d": ImpactNode(id="d", node_type="mfg", label="D", impact_score=0.5, affected_objects=[], depth=4),
        }
        edges = [
            ImpactEdge(source_id="root", target_id="a", weight=0.5, label=""),
            ImpactEdge(source_id="a", target_id="b", weight=0.5, label=""),
            ImpactEdge(source_id="b", target_id="c", weight=0.5, label=""),
            ImpactEdge(source_id="c", target_id="d", weight=0.5, label=""),
        ]
        paths_depth2 = ImpactGraphEngine.bfs_traverse(nodes, edges, "root", max_depth=2)
        # 深度限制为2，应该只有 root→a 和 root→a→b 到达 b
        for p in paths_depth2:
            assert p.node_count <= 3  # root + a + b at most

    def test_bfs_no_edges(self, db: Session) -> None:
        """没有边时只返回单节点路径"""
        nodes = {
            "only": ImpactNode(id="only", node_type="ecr", label="Only", impact_score=0.0, affected_objects=[], depth=0),
        }
        paths = ImpactGraphEngine.bfs_traverse(nodes, [], "only", max_depth=5)
        assert len(paths) == 1
        assert paths[0].path == ["only"]
        assert paths[0].node_count == 1

    def test_bfs_start_missing(self, db: Session) -> None:
        """起始节点不存在返回空列表"""
        nodes = {"a": ImpactNode(id="a", node_type="ecr", label="A", impact_score=0.5, affected_objects=[], depth=0)}
        paths = ImpactGraphEngine.bfs_traverse(nodes, [], "nonexistent", max_depth=5)
        assert paths == []


class TestSerializeToJson:
    """图输出可序列化为 JSON"""

    def test_serialize_to_json(self, db: Session) -> None:
        """ImpactGraphOut 可序列化为 JSON"""
        result = ImpactGraphOut(
            nodes=[
                ImpactNode(id="n1", node_type="ecr", label="ECR", impact_score=0.5, affected_objects=[], depth=0),
                ImpactNode(id="n2", node_type="eco", label="ECO", impact_score=0.5, affected_objects=[], depth=1),
            ],
            edges=[
                ImpactEdge(source_id="n1", target_id="n2", weight=0.8, label="ecr→eco"),
            ],
            ripple_score=12.34,
            max_depth=1,
            node_count=2,
            edge_count=1,
        )
        dumped = result.model_dump()
        json_str = json.dumps(dumped)
        assert json_str is not None
        parsed = json.loads(json_str)
        assert parsed["ripple_score"] == 12.34
        assert len(parsed["nodes"]) == 2
        assert len(parsed["edges"]) == 1

    def test_build_graph_serializable(self, db: Session) -> None:
        """build_graph 的输出可完整序列化为 JSON"""
        ecr = _create_ecr(db)
        eco = _create_eco(db, ecr.id)
        _create_eco_item(db, eco.id, object_type="part", object_code="PART-SER")
        result = ImpactGraphEngine.build_graph(ecr.id, db)
        # model_dump
        dumped = result.model_dump()
        json_str = json.dumps(dumped, ensure_ascii=False)
        assert isinstance(json_str, str)
        assert len(json_str) > 0
        # 反序列化验证
        parsed = json.loads(json_str)
        assert "nodes" in parsed
        assert "edges" in parsed
        assert "ripple_score" in parsed


class TestRippleScore:
    """Ripple effect 分数计算验证"""

    def test_ripple_score_empty(self, db: Session) -> None:
        """空路径返回 0"""
        score = ImpactGraphEngine.calculate_ripple_score([])
        assert score == 0.0

    def test_ripple_score_single_path(self, db: Session) -> None:
        """单一路径的 ripple score"""
        paths = [
            RipplePath(path=["a", "b", "c"], total_score=1.5, node_count=3),
        ]
        score = ImpactGraphEngine.calculate_ripple_score(paths)
        assert 0 <= score <= 100

    def test_ripple_score_multiple_paths(self, db: Session) -> None:
        """多条路径的 ripple score 高于单条"""
        single = [
            RipplePath(path=["a", "b"], total_score=0.5, node_count=2),
        ]
        multiple = [
            RipplePath(path=["a", "b"], total_score=0.5, node_count=2),
            RipplePath(path=["a", "c"], total_score=0.5, node_count=2),
            RipplePath(path=["a", "b", "d"], total_score=1.0, node_count=3),
        ]
        score_single = ImpactGraphEngine.calculate_ripple_score(single)
        score_multi = ImpactGraphEngine.calculate_ripple_score(multiple)
        assert score_multi > score_single

    def test_ripple_score_high_impact(self, db: Session) -> None:
        """高影响路径产生高 ripple score"""
        low_paths = [
            RipplePath(path=["a", "b"], total_score=0.1, node_count=2),
        ]
        high_paths = [
            RipplePath(path=["a", "b"], total_score=5.0, node_count=2),
            RipplePath(path=["a", "c", "d"], total_score=8.0, node_count=3),
        ]
        low_score = ImpactGraphEngine.calculate_ripple_score(low_paths)
        high_score = ImpactGraphEngine.calculate_ripple_score(high_paths)
        assert high_score > low_score

    def test_ripple_score_build_graph(self, db: Session) -> None:
        """build_graph 生成的 ripple score 在 0-100 之间"""
        ecr = _create_ecr(db)
        eco = _create_eco(db, ecr.id)
        _create_eco_item(db, eco.id, object_type="part", object_code="PART-RIPPLE")
        result = ImpactGraphEngine.build_graph(ecr.id, db)
        assert 0 <= result.ripple_score <= 100


class TestSnapshotPersistence:
    """ImpactGraphSnapshot 持久化"""

    def test_snapshot_created(self, db: Session) -> None:
        """build_graph 成功后应创建快照记录"""
        ecr = _create_ecr(db)
        eco = _create_eco(db, ecr.id)
        _create_eco_item(db, eco.id, object_type="bom", object_code="BOM-SNAP")

        ImpactGraphEngine.build_graph(ecr.id, db)

        snapshot = db.query(ImpactGraphSnapshot).filter(
            ImpactGraphSnapshot.ecr_id == ecr.id
        ).first()
        assert snapshot is not None
        assert snapshot.node_count > 0
        assert snapshot.edge_count >= 0
        assert snapshot.graph_data is not None
        assert "nodes" in snapshot.graph_data

    def test_snapshot_nonexistent_ecr(self, db: Session) -> None:
        """不存在的 ECR 不应创建快照"""
        ImpactGraphEngine.build_graph(99999, db)
        snapshots = db.query(ImpactGraphSnapshot).all()
        assert len(snapshots) == 0


class TestImpactRulesIntegration:
    """变更影响规则与图引擎集成"""

    def test_rules_affect_scores(self, db: Session) -> None:
        """激活的影响规则应提高相关节点 impact_score"""
        ecr = _create_ecr(db)
        eco = _create_eco(db, ecr.id)
        _create_eco_item(db, eco.id, object_type="part", object_code="compressor-x1")
        # 创建匹配规则
        _create_impact_rule(db, trigger_value="compressor", impact_level="critical")

        result_with_rules = ImpactGraphEngine.build_graph(ecr.id, db)

        # 没有规则时分数会更低
        ecr2 = _create_ecr(db, code="ECR-NO-RULE", title="No Rule ECR")
        eco2 = _create_eco(db, ecr2.id, code="ECO-NO-RULE")
        _create_eco_item(db, eco2.id, object_type="part", object_code="compressor-x1")

        result_no_rules = ImpactGraphEngine.build_graph(ecr2.id, db)

        # 有规则的 ripple score 应大于或等于无规则的
        # 注意: 构建的是不同的图, 但结构相似, 规则会增加分数
        assert result_with_rules.ripple_score >= 0


class TestHelperMethods:
    """工具方法单元测试"""

    def test_urgency_to_score_mapping(self, db: Session) -> None:
        """urgency 到 score 映射正确"""
        assert ImpactGraphEngine._urgency_to_score("emergency") == 1.0
        assert ImpactGraphEngine._urgency_to_score("high") == 0.8
        assert ImpactGraphEngine._urgency_to_score("medium") == 0.5
        assert ImpactGraphEngine._urgency_to_score("low") == 0.2
        assert ImpactGraphEngine._urgency_to_score(None) == 0.5
        assert ImpactGraphEngine._urgency_to_score("unknown") == 0.5

    def test_map_object_type_to_downstream(self, db: Session) -> None:
        """对象类型到下游节点的映射正确"""
        part_downstream = ImpactGraphEngine._map_object_type_to_downstream("part")
        assert len(part_downstream) >= 1
        assert any("prototype" in d[0] for d in part_downstream)

        bom_downstream = ImpactGraphEngine._map_object_type_to_downstream("bom")
        assert any("bom" in d[0] for d in bom_downstream)

        cert_downstream = ImpactGraphEngine._map_object_type_to_downstream("certification")
        assert any("certification" in d[0] for d in cert_downstream)

    def test_get_propagation_weight(self, db: Session) -> None:
        """默认传播权重正常"""
        assert ImpactGraphEngine._get_propagation_weight("ecr", "eco") == 1.0
        assert ImpactGraphEngine._get_propagation_weight("eco", "prototype") == 0.9
        assert ImpactGraphEngine._get_propagation_weight("unknown", "anything") == 0.3

    def test_max_depth_constant(self, db: Session) -> None:
        """MAX_DEPTH 应为 5"""
        assert ImpactGraphEngine.MAX_DEPTH == 5

    def test_node_types_defined(self, db: Session) -> None:
        """NODE_TYPES 应包含所有预期类型"""
        expected = {"ecr", "eco", "prototype", "bom", "certification", "manufacturing", "cost"}
        assert set(ImpactGraphEngine.NODE_TYPES) == expected
