# ROS Phase 6 S3 — 变更控制中心（ECR/ECO）增量架构规划

> **版本**: v1.0  
> **日期**: 2026-06-24  
> **基于**: S1(实验中心+VR+样机+Gate规则) + S2(认证中心+ChangeImpactEngine) 已完成  
> **当前系统**: 313 routes, git commit b3d1c1e  
> **聚焦第一批范围**: ECR完整流程 + ECO基础管理 + 变更影响分析(复用S2) + BOM对比  

---

## 1. 现状分析

### 1.1 已完成基础

| 模块 | 状态 | 说明 |
|------|------|------|
| ECR 模型 (`test.py:ECR`) | ✅ 已存在 | 基本字段: ecr_no, title, change_type, trigger, status(draft/submitted/approved/rejected/implemented), impact_analysis(文本) |
| ECN 模型 (`test.py:ECN`) | ✅ 已存在 | 基本字段: ecn_no, ecr_id, title, bom_changes(JSON文本), status(draft/released/implemented), cdf_impact, certification_impact |
| ECR API (`certifications.py`) | ✅ 已存在 | GET/POST `/ecrs`, PATCH `/ecrs/{eid}?action=approve|reject` |
| ECN API (`certifications.py`) | ✅ 已存在 | GET/POST `/ecns` |
| ECR/ECN Schema (`schemas/__init__.py`) | ✅ 已存在 | ECRCreate, ECROut, ECNCreate, ECNOut |
| 状态机 (`state_machine.py`) | ✅ 已存在 | ECR: draft→submitted→reviewing→approved/rejected; ECN: draft→submitted→approved→implemented |
| 前端 ECR/ECN 页面 (`ChangesView.vue`) | ✅ 已存在 | Tab切换: ECR列表+编辑弹窗 + ECN列表+新建弹窗 |
| 前端路由 (`router/index.ts`) | ✅ 已存在 | `/changes` → ChangesView.vue, meta: `{ title: '变更管理' }` |
| 权限 (`permissions.py`) | ✅ 已存在 | `changes` 菜单，`certifications/ecrs`/`certifications/ecns` 映射到 `changes` |
| ChangeImpactEngine (`services/change_impact_engine.py`) | ✅ S2已完成 | `analyze_prototype_change()` 完整实现, `analyze_bom_change()` 预留 |
| ChangeImpactRule (`models/change_impact.py`) | ✅ S2已完成 | 规则: trigger_type+trigger_value → affected_cert_types + impact_level |
| ChangeImpactRecord (`models/change_impact.py`) | ✅ S2已完成 | 已有 `ecr_id` 字段(预留), 带 `prototype_id`, `changed_part` |
| S2 Certificate + CertProject + CertSample | ✅ S2已完成 | 全链路: 需求→项目→样机→执行→结果→证书 |
| S2 CertificationGateRule | ✅ S2已完成 | 认证门禁规则 |
| BOM模型 (`bom.py`) | ✅ 已存在 | Part(含CDF/market_cert_marks), PartAVL, BOM(含version), BOMItem(树形结构) |
| Prototype (`test.py`) | ✅ 已存在 | 含版本树(parent_prototype_id), bom_version(关联BOM版本) |
| GateRule (S1) | ✅ 已存在 | 可扩展用于变更门控 |

### 1.2 当前 ECR/ECN 状态机状态

**ECR 现有状态** (在 `state_machine.py`):
```
draft → submitted → reviewing → approved/rejected
```

**ECN 现有状态** (在 `state_machine.py`):
```
draft → submitted → approved → implemented
```

**ECR 模型现有状态字段** (在 `test.py`):
```
draft/submitted/approved/rejected/implemented
```

### 1.3 关键差距

| 差距 | 说明 |
|------|------|
| ECR 缺少 impact_analyzing/impact_analyzed 中间状态 | 审批前需等待影响分析完成 |
| 无自动触发影响分析 | submitted → 自动调用 S2 ChangeImpactEngine |
| ECR 缺少 urgency 字段 | 无法区分紧急程度 |
| ECR 缺少 reason 字段 | 变更原因文本字段 |
| ECO 缺少 eco_items 模型 | 无法管理变更明细行 |
| ECO 缺少 BOM应用流程 | released → implemented 时自动更新BOM |
| 无 BOM 版本对比引擎 | 无法对比两个版本差异 |
| 无 ECR→ECO 创建流程 | 从ECR批准后自动创建ECO |
| 无认证失效自动识别 | 变更物料与CDF/证书联动 |
| ECR API 在 certifications.py 中 | 与认证管理混合，需要独立拆分或增强 |

---

## 2. 增量 Domain Model

### 2.1 ECR 模型增强（修改 test.py）

现有 `ECR` 类需要增强以下字段：

```python
# ── ECR 增量字段 (Phase 6 S3) ──
urgency = Column(String(20), default="routine", comment="紧急程度: routine/urgent/emergency")
reason = Column(Text, nullable=True, comment="变更原因")
prototype_id = Column(Integer, ForeignKey("prototypes.id"), nullable=True, comment="关联样机(变更源)")
related_verification_req_ids = Column(Text, nullable=True, comment="关联验证需求ID列表 JSON")
impact_analysis_status = Column(String(20), default="pending", comment="影响分析状态: pending/running/done/failed")
eco_created = Column(Boolean, default=False, comment="是否已创建ECO")
```

**增强后的状态值**（需与 `state_machine.py` 对齐）:
```
draft → submitted → impact_analyzing → impact_analyzed → approved/rejected
    ↘ cancelled
approved → (manual: create_eco)
```

### 2.2 ECO 模型增强（修改 test.py → 重命名为 ECO）

将现有 `ECN` 类重命名为 `ECO`（统一命名），并新增字段：

```python
# ── ECO 增量字段 ──
target_bom_id = Column(Integer, ForeignKey("boms.id"), nullable=True, comment="目标BOM")
implementer = Column(String(50), nullable=True, comment="实施人")
approval_summary = Column(Text, nullable=True, comment="审批摘要")
prototype_id = Column(Integer, ForeignKey("prototypes.id"), nullable=True, comment="关联样机")
```

**增强后的状态值**:
```
draft → released → implemented → closed
                    ↘ cancelled
```

### 2.3 新增: ECOItem 模型（新文件 change_control.py）

```python
class ECOItem(Base):
    """ECO变更明细行"""
    __tablename__ = "eco_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    eco_id = Column(Integer, ForeignKey("ecos.id"), nullable=False, comment="关联ECO")
    change_operation = Column(String(20), nullable=False, comment="操作: add/remove/replace/modify")
    part_no = Column(String(50), nullable=False, comment="物料编码")
    part_name = Column(String(200), nullable=True)
    old_value = Column(Text, nullable=True, comment="旧值(如规格/用量/供应商)")
    new_value = Column(Text, nullable=True, comment="新值")
    position_no = Column(String(50), nullable=True, comment="位置号")
    change_reason = Column(Text, nullable=True, comment="变更原因")
    seq = Column(Integer, default=1, comment="顺序")
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
```

### 2.4 新增: ECOImpactAnalysis 模型（新文件 change_control.py）

```python
class ECOImpactAnalysis(Base):
    """变更影响分析记录"""
    __tablename__ = "eco_impact_analyses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ecr_id = Column(Integer, ForeignKey("ecrs.id"), nullable=False, comment="关联ECR")
    impact_category = Column(String(30), nullable=False, comment="影响类别: performance/safety/cost/schedule/certification/production")
    impact_level = Column(String(20), nullable=False, comment="影响等级: critical/major/minor/none")
    impact_description = Column(Text, nullable=True)
    affected_object = Column(String(100), nullable=True, comment="受影响对象: BOM项/产品/认证/供应商")
    affected_object_id = Column(String(50), nullable=True, comment="受影响对象ID")
    mitigation = Column(Text, nullable=True, comment="缓解措施/建议")
    analyzed_by = Column(String(50), nullable=True)
    analyzed_at = Column(DateTime, nullable=True)
    source = Column(String(20), default="auto", comment="来源: auto(引擎自动)/manual(人工修正)")
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
```

### 2.5 新增: EcoCertImpactResult 模型（新文件 change_control.py）

```python
class EcoCertImpactResult(Base):
    """认证失效自动识别结果"""
    __tablename__ = "eco_cert_impact_results"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ecr_id = Column(Integer, ForeignKey("ecrs.id"), nullable=False, comment="关联ECR")
    cert_id = Column(Integer, ForeignKey("certificates.id"), nullable=True, comment="关联证书")
    cert_type = Column(String(20), nullable=True, comment="认证类型")
    impact_type = Column(String(20), nullable=False, comment="影响类型: direct/indirect/none")
    impact_result = Column(String(30), nullable=False, comment="影响结果: cert_invalid/retest_required/redeclare/partial_update/no_impact")
    affected_items = Column(Text, nullable=True, comment="受影响的具体项JSON")
    required_actions = Column(Text, nullable=True, comment="需执行的动作JSON")
    suggestion = Column(Text, nullable=True)
    is_accepted = Column(Boolean, nullable=True, comment="是否接受建议")
    analyzed_at = Column(DateTime, server_default=func.now())
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
```

### 2.6 BOM 版本对比相关（无新增表，使用现有 BOM + BOMItem）

使用现有 `BOM` 和 `BOMItem` 模型，根据 `bom_no` + `version` 查询两个版本，在服务层做差异分析。

### 2.7 模型文件结构

```
backend/app/models/
├── test.py              # 修改: ECR增强, ECN重命名为ECO
├── change_control.py    # 新增: ECOItem, ECOImpactAnalysis, EcoCertImpactResult
├── change_impact.py     # 已有(S2): ChangeImpactRule, ChangeImpactRecord
├── bom.py               # 已有: BOM, BOMItem, Part(含CDF标记)
└── __init__.py          # 修改: 导入新模型
```

---

## 3. ECR/ECO 状态机设计

### 3.1 ECR 状态机（增强版）

```
     ┌──────────┐
     │  draft   │ ← 草稿（可编辑）
     └────┬─────┘
          │ submit
          ▼
     ┌──────────┐
     │ submitted│ ──→ 触发 ChangeImpactEngine（自动）
     └────┬─────┘
          │ analyze_complete
          ▼
    ┌─────────────────┐
    │impact_analyzed   │ ← 影响分析完成，等待审批
    └──────┬──────────┘
           │ approve / reject
           ├──────────────┐
           ▼              ▼
    ┌──────────┐   ┌──────────┐
    │ approved │   │ rejected │
    └────┬─────┘   └──────────┘
         │ create_eco（手动）
         ▼
    ┌──────────┐
    │eco_created│
    └──────────┘
```

**状态转换表**:

| 当前状态 | 目标状态 | 触发动作 | 自动处理 |
|----------|----------|----------|---------|
| draft | submitted | 提交审核 | 生成 ecr_no, 设置 submitted_by |
| submitted | impact_analyzing | (自动) | 触发 ChangeImpactEngine 异步分析 |
| impact_analyzing | impact_analyzed | (自动) | 引擎完成, 写入 impact_analyses 表 |
| impact_analyzed | approved | 批准 | 记录 approved_by, 可创建ECO |
| impact_analyzed | rejected | 驳回 | 记录审批意见 |
| approved | eco_created | 创建ECO | 自动创建ECO并关联ECR |
| draft | cancelled | 取消 | — |

### 3.2 ECO 状态机

```
draft → released → implemented → closed
                  ↘ cancelled
```

**状态转换表**:

| 当前状态 | 目标状态 | 触发动作 | 自动处理 |
|----------|----------|----------|---------|
| draft | released | 发布ECO | 校验ECO items 完整性 |
| released | implemented | 实施 | 更新BOM(暂缓，S4实现), 版本+1(暂缓) |
| implemented | closed | 关闭 | 归档 |
| released | cancelled | 取消 | — |

### 3.3 状态机配置变更（state_machine.py）

**ECR 配置更新**:
```python
"ECR": {
    "draft": ["submitted", "cancelled"],
    "submitted": ["impact_analyzing"],
    "impact_analyzing": ["impact_analyzed", "draft"],  # draft = 退回
    "impact_analyzed": ["approved", "rejected"],
    "approved": ["eco_created"],
    "rejected": [],
    "eco_created": [],
    "cancelled": [],
},
```

**ECO 配置新增**:
```python
"ECO": {
    "draft": ["released", "cancelled"],
    "released": ["implemented", "cancelled"],
    "implemented": ["closed"],
    "closed": [],
    "cancelled": [],
},
```

---

## 4. 变更影响分析流程

### 4.1 整体流程

```
ECR.submitted
    │
    ▼
┌──────────────────────────┐
│ 1. 收集变更上下文         │
│    - 获取 ECR 中的        │
│      prototype_id,        │
│      change_type,         │
│      description          │
└──────────┬───────────────┘
           ▼
┌──────────────────────────┐
│ 2. 调用 S2 ChangeImpact   │
│    Engine                 │
│    (复用已有引擎)          │
│                           │
│ 输入: prototype_id /      │
│       changed_parts       │
│                           │
│ 输出: impact_records      │
│       (写入               │
│        ChangeImpactRecord)│
└──────────┬───────────────┘
           ▼
┌──────────────────────────┐
│ 3. 认证失效自动识别       │
│    (新增 S3 引擎)          │
│                           │
│ 输入: changed_parts       │
│       (从 ECR 描述/        │
│        prototype 解析)     │
│                           │
│ 逻辑: 遍历变更物料 →       │
│       匹配 Part.CDF →     │
│       匹配 Certificate →   │
│       写入                 │
│       EcoCertImpactResult │
└──────────┬───────────────┘
           ▼
┌──────────────────────────┐
│ 4. 批量写入               │
│    ECOImpactAnalysis 表   │
│    (统一存储)              │
└──────────┬───────────────┘
           ▼
┌──────────────────────────┐
│ 5. 更新 ECR 状态          │
│    impact_analyzing →     │
│    impact_analyzed        │
│                           │
│ 6. 触发事件:               │
│    ecr.impact_analyzed    │
└──────────────────────────┘
```

### 4.2 影响分析引擎增强策略

**第一阶段（第一批）**: S2 ChangeImpactEngine 的 `analyze_prototype_change()` 已有完整实现，可直接通过 `prototype_id` 调用。新增的认证失效自动识别作为独立服务层函数。

**具体复用方式**:
```python
# S3 新增服务: backend/app/services/ecr_impact_service.py
from app.services.change_impact_engine import ChangeImpactEngine

class ECRImpactService:
    def __init__(self, db: Session):
        self.db = db
        self.impact_engine = ChangeImpactEngine(db)
    
    def run_full_impact_analysis(self, ecr_id: int) -> dict:
        """完整的 ECR 影响分析"""
        ecr = self.db.query(ECR).filter(ECR.id == ecr_id).first()
        
        # 1. 提取变更部件列表
        changed_parts = self._extract_changed_parts(ecr)
        
        # 2. 复用 S2 ChangeImpactEngine (prototype 路径)
        if ecr.prototype_id:
            impact_result = self.impact_engine.analyze_prototype_change(
                prototype_id=ecr.prototype_id,
                changed_parts=changed_parts,
            )
            # 将结果写入 ECOImpactAnalysis 表
            for rec in impact_result.get("impact_records", []):
                self._save_impact_analysis(ecr_id, rec)
        
        # 3. 认证失效自动识别（新增 S3 逻辑）
        cert_results = self._auto_detect_cert_impact(ecr, changed_parts)
        
        # 4. 更新 ECR 状态
        ecr.status = "impact_analyzed"
        ecr.impact_analysis_status = "done"
        self.db.commit()
        
        return {"prototype_impact": impact_result, "cert_impacts": cert_results}
```

### 4.3 认证失效自动识别引擎

```python
def _auto_detect_cert_impact(ecr, changed_parts: list[str], db: Session) -> list[dict]:
    """
    认证失效自动识别核心逻辑
    
    规则:
    1. 变更物料 part_no 在 Certificate.cdf_doc_ref → cert_invalid
    2. 变更物料 is_cdf_item=true 且 cdf_type in ('安全件','EMC件') → retest_required
    3. 变更物料 market_cert_marks 匹配 cert_type → redeclare
    4. 变更物料制造商变更 → 需要 update
    """
    results = []
    product_certs = db.query(Certificate).filter(
        Certificate.status == "active",
        # 通过产品关联...
    ).all()
    
    for part_no in changed_parts:
        part = db.query(Part).filter(Part.part_no == part_no).first()
        if not part:
            continue
        
        for cert in product_certs:
            impact = {"impact_result": "no_impact", "impact_type": "none"}
            
            # 规则1: CDF 直接匹配
            if part.is_cdf_item and part.cdf_cert_no == cert.cert_no:
                impact = {"impact_result": "cert_invalid", "impact_type": "direct"}
            
            # 规则2: CDF 类型匹配
            elif part.is_cdf_item and part.cdf_type in ("安全件", "EMC件"):
                impact = {"impact_result": "retest_required", "impact_type": "indirect"}
            
            # 规则3: 市场认证标记匹配
            elif part.market_cert_marks:
                marks = json.loads(part.market_cert_marks)
                if marks.get(cert.cert_type) == True:
                    impact = {"impact_result": "redeclare", "impact_type": "indirect"}
            
            if impact["impact_result"] != "no_impact":
                result = EcoCertImpactResult(
                    ecr_id=ecr.id,
                    cert_id=cert.id,
                    cert_type=cert.cert_type,
                    **impact,
                    suggestion=f"物料{part.part_no}变更影响证书{cert.cert_no}"
                )
                db.add(result)
                results.append(impact)
    
    db.commit()
    return results
```

---

## 5. API 端点设计

### 5.1 API 路由规划

**新路由前缀**: `/api/v1/ecr` 和 `/api/v1/eco`（独立模块，不再混合在 `/certifications` 下）

**注意**: 现有 ECR/ECN API 在 `certifications.py` 中，路径为 `/certifications/ecrs` 和 `/certifications/ecns`。S3 增强后，建议：
- 保留现有路径兼容（原有简单CRUD可用）
- **新增独立 API 文件** `change_control.py`，使用全新路由 `/api/v1/ecr` 和 `/api/v1/eco`
- 将增强逻辑集中在新文件中，避免修改已有的 `certifications.py` 过载（当前已 321 行）

### 5.2 ECR API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/v1/ecr` | ECR列表（增强筛选: urgency/trigger/status/change_type） | changes |
| GET | `/api/v1/ecr/{id}` | 详情（含影响分析、认证影响、ECO关联） | changes |
| POST | `/api/v1/ecr` | 创建ECR（增强字段: urgency, reason, prototype_id） | systems_engineer/quality_engineer |
| PUT | `/api/v1/ecr/{id}` | 更新ECR（仅 draft 状态） | systems_engineer |
| POST | `/api/v1/ecr/{id}/submit` | 提交审核（draft→submitted） | systems_engineer |
| POST | `/api/v1/ecr/{id}/run-impact-analysis` | **手动触发影响分析** | systems_engineer |
| GET | `/api/v1/ecr/{id}/impact-analyses` | 获取影响分析结果列表 | changes |
| GET | `/api/v1/ecr/{id}/cert-impacts` | 获取认证影响分析结果 | changes |
| POST | `/api/v1/ecr/{id}/approve` | 批准（impact_analyzed→approved） | rd_director/general_manager |
| POST | `/api/v1/ecr/{id}/reject` | 驳回（impact_analyzed→rejected） | rd_director/general_manager |
| POST | `/api/v1/ecr/{id}/create-eco` | **从ECR创建ECO**（approved→eco_created） | systems_engineer |

### 5.3 ECO API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/v1/eco` | ECO列表（增强筛选: status/product_code） | changes |
| GET | `/api/v1/eco/{id}` | 详情（含eco_items、关联ECR、BOM信息） | changes |
| POST | `/api/v1/eco` | 创建ECO（可独立或从ECR生成） | systems_engineer |
| PUT | `/api/v1/eco/{id}` | 更新ECO（仅 draft 状态） | systems_engineer |
| POST | `/api/v1/eco/{id}/release` | 发布（draft→released） | rd_director |
| POST | `/api/v1/eco/{id}/implement` | 实施（released→implemented） | systems_engineer/quality_engineer |
| POST | `/api/v1/eco/{id}/close` | 关闭（implemented→closed） | systems_engineer |

### 5.4 ECO Items API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/v1/eco/{id}/items` | 获取ECO变更明细列表 | changes |
| POST | `/api/v1/eco/{id}/items` | 添加变更条目 | systems_engineer |
| PUT | `/api/v1/eco/{id}/items/{item_id}` | 更新变更条目 | systems_engineer |
| DELETE | `/api/v1/eco/{id}/items/{item_id}` | 删除变更条目（仅 draft 状态） | systems_engineer |

### 5.5 BOM 版本对比 API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/v1/bom/compare` | BOM版本对比（传入bom_id, version_a, version_b） | changes/bom |
| GET | `/api/v1/ecr/{id}/bom-diff-preview` | ECR变更的BOM差异预览（基于prototype BOM版本） | changes |

### 5.6 现有 API 向后兼容

| 现有路径 | 操作 | 
|----------|------|
| `GET /certifications/ecrs` | 保留(仅返回基础ECR列表+) |
| `POST /certifications/ecrs` | 保留(仅基础创建) |
| `PATCH /certifications/ecrs/{eid}?action=approve|reject` | 保留(兼容) |
| `GET /certifications/ecns` | 保留(但建议逐步迁移到 `/api/v1/eco`) |
| `POST /certifications/ecns` | 保留(但建议逐步迁移) |

---

## 6. 前端页面设计

### 6.1 页面结构

```
views/changes/ (增强)
├── ECRListView.vue           ← ECR列表页（增强筛选+影响分析状态列）
├── ECRDetailView.vue         ← ECR详情页（新增: 影响分析面板+认证影响）
├── ECOListView.vue           ← ECO列表页（新增: 独立于ECN）
├── ECODetailView.vue         ← ECO详情页（新增: ECO Items管理+BOM差异对比）
├── BOMCompareView.vue        ← BOM版本对比页（新增）
└── ChangeDashboardView.vue   ← 变更控制仪表盘（新增）
```

### 6.2 核心组件拆分

| 组件 | 所属页面 | 功能 |
|------|---------|------|
| `ECRForm.vue` | ECRDetailView | ECR创建/编辑表单（含urgency, reason, prototype选择） |
| `ECRStatusStepper.vue` | ECRDetailView | ECR状态流程步骤条（draft→submitted→impact_analyzed→approved/rejected） |
| `ImpactAnalysisPanel.vue` | ECRDetailView | 影响分析结果展示面板（按类别分类: 性能/认证/成本） |
| `CertImpactCard.vue` | ECRDetailView | 认证影响卡片（红色=失效, 黄色=需重测, 绿色=无影响） |
| `ECOForm.vue` | ECODetailView | ECO创建/编辑表单 |
| `ECOItemEditor.vue` | ECODetailView | ECO变更明细行编辑器（add/remove/replace/modify） |
| `BOMDiffTable.vue` | BOMCompareView | BOM版本差异对比表格（红/绿标识变更） |
| `ChangeTimeline.vue` | ChangeDashboardView | 变更时间线（ECR→ECO→实施） |
| `CreateEcoDialog.vue` | ECRDetailView | 从ECR创建ECO的确认弹窗 |

### 6.3 页面路由（修改 router/index.ts）

```typescript
// S3 新增路由
{
  path: 'changes/ecr',
  name: 'ECRList',
  component: () => import('@/views/changes/ECRListView.vue'),
  meta: { title: 'ECR变更申请', menu: 'changes' },
},
{
  path: 'changes/ecr/:id',
  name: 'ECRDetail',
  component: () => import('@/views/changes/ECRDetailView.vue'),
  meta: { title: 'ECR详情', menu: 'changes' },
},
{
  path: 'changes/eco',
  name: 'ECOList',
  component: () => import('@/views/changes/ECOListView.vue'),
  meta: { title: 'ECO变更通知', menu: 'changes' },
},
{
  path: 'changes/eco/:id',
  name: 'ECODetail',
  component: () => import('@/views/changes/ECODetailView.vue'),
  meta: { title: 'ECO详情', menu: 'changes' },
},
{
  path: 'changes/bom-compare',
  name: 'BOMCompare',
  component: () => import('@/views/changes/BOMCompareView.vue'),
  meta: { title: 'BOM版本对比', menu: 'changes' },
},
{
  path: 'changes/dashboard',
  name: 'ChangeDashboard',
  component: () => import('@/views/changes/ChangeDashboardView.vue'),
  meta: { title: '变更仪表盘', menu: 'changes' },
},
```

**保留现有** `/changes` 路由作为变更管理的总入口（可重定向到 ECRList 或 dashboard）。

### 6.4 现有 ChangesView.vue 处理

现有 `ChangesView.vue` 包含 ECR/ECN 的 Tab 切换列表 + 弹窗 CRUD。S3 增强后：
1. **保留** ChangesView.vue 作为旧版简易入口（向后兼容）
2. **新增** 专用 ECR/ECO 详情页，提供完整的状态流转、影响分析、Item 管理
3. **建议** 将 ChangesView.vue 改为 Dashboard 风格入口，链接到新页面

---

## 7. 与 S1/S2 的集成点

### 7.1 集成矩阵

| 集成点 | 方向 | 已有准备 | S3 动作 |
|--------|------|---------|---------|
| S1 Prototype 版本树 → ECR | 变更触发 | Prototype已有 parent_prototype_id | ECR 新增 prototype_id FK，提交时携带版本信息 |
| S1 GateRule → 变更门控 | ECR 审批 | GateRule 模型已存在 | 扩展: 变更审批前检查 GateRule（第二阶段） |
| S2 ChangeImpactEngine → 影响分析 | 引擎调用 | `analyze_prototype_change()` 已实现 | ECR 提交后自动调用，传 prototype_id + changed_parts |
| S2 ChangeImpactRecord → ECR | 记录关联 | 已有 ecr_id 预留字段 | S3 写入时填充 ecr_id（当前只填 prototype_id） |
| S2 Certificate → 认证失效检测 | 数据源 | Certificate.status = active | 遍历产品有效证书，匹配 Part.CDF |
| S2 CertificationGateRule → 变更门禁 | 变更门禁 | CertificationGateRule 已存在 | ECR 影响分析后检查是否触犯门禁 |
| S2 CertificationProject/Sample | 影响分析输入 | 完整的认证项目+样机链 | 变更影响通过 prototype 回溯到 cert_project |
| S1/BOM → ECO 应用 | 变更落地 | BOM + BOMItem 已存在 | 第一批不实现自动应用，仅做 BOM 版本对比 |

### 7.2 集成点详解

#### 集成点①: S1 Prototype → ECR 变更触发

```
Prototype 版本迭代 (V1.0→V2.0)
    → 用户选择"发起变更"
    → 自动创建 ECR，携带 prototype_id
    → ECR 提交后自动触发影响分析
    → 分析结果参考 Prototype 版本链
```

**数据流**:
```python
# 前端: PrototypeDetailView.vue → "发起变更"按钮
# API: POST /api/v1/ecr { prototype_id, ... }
# 后端: ECR.prototype_id = prototype_id
#        ECR 提交: run_full_impact_analysis → 调用 ChangeImpactEngine
```

#### 集成点②: S2 ChangeImpactEngine → 影响分析

```
ECR.status = submitted
    → ECRImpactService.run_full_impact_analysis(ecr_id)
    → ChangeImpactEngine.analyze_prototype_change(
           prototype_id=ecr.prototype_id,
           changed_parts=[...]
       )
    → 写入 ChangeImpactRecord (填充 ecr_id 字段)
    → 转换为 ECOImpactAnalysis 记录
    → ECR.status = impact_analyzed
```

**已就绪**: `ChangeImpactRecord` 已有 `ecr_id` 字段（当前为 nullable），S3 直接使用。

#### 集成点③: S2 Certificate → 认证失效自动识别

```
ECR 影响分析阶段
    → 遍历变更物料 (从 prototype 的 BOM 版本获取)
    → Part.is_cdf_item 检查
    → Part.cdf_cert_no → Certificate 匹配
    → Part.market_cert_marks → cert_type 匹配
    → 写入 EcoCertImpactResult
    → Dashboard 红色告警
```

---

## 8. 任务分解（按 Sprint）

### Sprint 1: ECR 增强 + 基础流程（预估: 5人天）

| # | 任务 | 文件 | 预估(人天) |
|---|------|------|-----------|
| 1.1 | ECR 模型增强: 添加 urgency, reason, prototype_id, impact_analysis_status 字段 | `test.py` | 0.5 |
| 1.2 | 状态机配置更新: 新增 impact_analyzing/impact_analyzed/eco_created 状态 | `state_machine.py` | 0.5 |
| 1.3 | Pydantic Schema 增强: ECRCreate/ECROut 新增字段 | `schemas/__init__.py` | 0.5 |
| 1.4 | 创建独立 ECR API 文件: list, detail, create, update, submit, approve, reject | `change_control.py` (新增) | 2 |
| 1.5 | ECR 提交自动触发影响分析（调用 S2 ChangeImpactEngine） | `change_control.py` | 1 |
| 1.6 | ECR 前端列表页增强: 新增 urgency/impact_status 筛选 + 状态步骤条 | `ECRListView.vue` | 0.5 |
| 1.7 | ECR 前端表单增强: 紧急程度、变更原因、关联样机选择器 | `ECRForm.vue` | 1 |

### Sprint 2: ECO 基础管理（预估: 5人天）

| # | 任务 | 文件 | 预估(人天) |
|---|------|------|-----------|
| 2.1 | ECN 重命名为 ECO (向后兼容保留ECN引用) | `test.py` | 0.5 |
| 2.2 | ECO 模型增强: 添加 target_bom_id, implementer, approval_summary 字段 | `test.py` | 0.5 |
| 2.3 | 新增 ECOItem 模型 | `change_control.py` (新增) | 0.5 |
| 2.4 | ECO/ECOItem Schema | `schemas/__init__.py` | 0.5 |
| 2.5 | ECO API: list, detail, create, update, release, implement, close | `change_control.py` | 1.5 |
| 2.6 | ECO Items API: CRUD (list, add, update, delete) | `change_control.py` | 0.5 |
| 2.7 | ECO 前端列表页 + 详情页 + Item 编辑器 | `ECOListView.vue`, `ECODetailView.vue` | 1 |

### Sprint 3: 变更影响分析 + 认证失效识别（预估: 6人天）

| # | 任务 | 文件 | 预估(人天) |
|---|------|------|-----------|
| 3.1 | 新增 ECOImpactAnalysis 模型 | `change_control.py` | 0.5 |
| 3.2 | 新增 EcoCertImpactResult 模型 | `change_control.py` | 0.5 |
| 3.3 | 创建 ECRImpactService（影响分析编排层） | `services/ecr_impact_service.py` (新增) | 2 |
| 3.4 | 认证失效自动识别引擎（CDF匹配 + Certificate联动） | `services/ecr_impact_service.py` | 1.5 |
| 3.5 | 影响分析 API (run-impact-analysis, get-impact-analyses, get-cert-impacts) | `change_control.py` | 1 |
| 3.6 | ECR提交后自动触发影响分析（Event/钩子） | `change_control.py` | 0.5 |
| 3.7 | 影响分析前端面板 (ImpactAnalysisPanel, CertImpactCard) | `ImpactAnalysisPanel.vue` | 1.5 |

### Sprint 4: BOM 版本对比 + 集成联调（预估: 4人天）

| # | 任务 | 文件 | 预估(人天) |
|---|------|------|-----------|
| 4.1 | BOM 版本对比服务（比较两个 version 的 BOMItem 差异） | `services/bom_compare_service.py` (新增) | 1.5 |
| 4.2 | BOM 对比 API | `bom.py` (增强) | 0.5 |
| 4.3 | ECR → ECO 创建流程（从 approved 一键生成 ECO + ECOItem） | `change_control.py` | 1 |
| 4.4 | BOM 差异对比前端组件（BOMDiffTable） | `BOMCompareView.vue` | 1.5 |
| 4.5 | 变更仪表盘前端 | `ChangeDashboardView.vue` | 1 |
| 4.6 | 权限配置更新 + 路由注册 | `permissions.py`, `router/index.ts` | 0.5 |

### 总工作量

| Sprint | 内容 | 人天 |
|--------|------|------|
| Sprint 1 | ECR 增强 + 基础流程 | 5 人天 |
| Sprint 2 | ECO 基础管理 | 5 人天 |
| Sprint 3 | 变更影响分析 + 认证失效识别 | 6 人天 |
| Sprint 4 | BOM 版本对比 + 集成联调 | 4 人天 |
| **合计** | **第一批全范围** | **20 人天** |

---

## 9. 配置文件变更清单

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 修改 | `backend/app/models/test.py` | ECR 增强字段 + ECN→ECO 重命名/增强 |
| 新增 | `backend/app/models/change_control.py` | ECOItem, ECOImpactAnalysis, EcoCertImpactResult |
| 修改 | `backend/app/models/__init__.py` | 导入新模型 |
| 新增 | `backend/app/services/ecr_impact_service.py` | ECR影响分析编排 + 认证失效识别 |
| 新增 | `backend/app/services/bom_compare_service.py` | BOM版本对比引擎 |
| 修改 | `backend/app/services/change_impact_engine.py` | 增强 `analyze_bom_change()` 实现（当前为 TODO） |
| 修改 | `backend/app/services/state_machine.py` | ECR/ECO 状态机配置更新 |
| 修改 | `backend/app/schemas/__init__.py` | 新增 ECO/ECOItem/ECOImpactAnalysis/EcoCertImpactResult Schema |
| 新增 | `backend/app/api/change_control.py` | ECR/ECO/Items/Impact API 路由 |
| 修改 | `backend/app/api/certifications.py` | 向后兼容保留旧路由 |
| 修改 | `backend/app/core/permissions.py` | 新增 S3 相关菜单和 API 路径映射 |
| 新增 | `frontend/src/views/changes/ECRListView.vue` | ECR列表页 |
| 新增 | `frontend/src/views/changes/ECRDetailView.vue` | ECR详情页 |
| 新增 | `frontend/src/views/changes/ECOListView.vue` | ECO列表页 |
| 新增 | `frontend/src/views/changes/ECODetailView.vue` | ECO详情页 |
| 新增 | `frontend/src/views/changes/BOMCompareView.vue` | BOM版本对比页 |
| 新增 | `frontend/src/views/changes/ChangeDashboardView.vue` | 变更仪表盘 |
| 修改 | `frontend/src/router/index.ts` | 新增 S3 路由 |
| 修改 | `frontend/src/types/roles.ts` | 新增 S3 菜单（如需要） |
| 新增 | `migrations/versions/xxxx_phase6_s3_change_control.py` | 数据库迁移脚本 |

---

## 10. 设计决策记录

### 决策 1: ECN → ECO 重命名

**决定**: 将现有 `ECN` 模型重命名为 `ECO`（工程变更通知 → Engineering Change Order/Official）

**理由**:
- 业界标准术语为 ECO (Engineering Change Order)，非 ECN
- phase6-plan.md 中明确使用 ECO 术语
- 向后兼容保留 ECN 别名引用

**影响**:
- `backend/app/models/__init__.py` 中保留 `ECN = ECO` 别名导出
- `api/certifications.py` 中 `_gen_ecn_no()` 保留
- 新代码统一使用 `ECO`

### 决策 2: 独立 API 文件 vs 增强现有

**决定**: 新建 `backend/app/api/change_control.py`，使用独立路由 `/api/v1/ecr` 和 `/api/v1/eco`

**理由**:
- `certifications.py` 已 321 行，较复杂
- 变更控制中心是独立业务域，API 应独立
- 新路由使用 RESTful API v1 风格

**影响**:
- 旧路由 `/certifications/ecrs` 保留向后兼容
- 新功能开发在新文件中

### 决策 3: 影响分析存储复用 vs 新增

**决定**: 复用 S2 `ChangeImpactRecord` 作为原始分析记录，新增 `ECOImpactAnalysis` 作为业务展示层

**理由**:
- `ChangeImpactRecord` 已有 ecr_id 预留字段和完整的 rule 关联
- S2 引擎输出直接写入 `ChangeImpactRecord`，无需改造
- `ECOImpactAnalysis` 作为 ECR 详情页展示用，包含 mitigation(缓解措施)等业务字段

### 决策 4: BOM 自动应用（第一批不做）

**决定**: 第一批范围不实现 BOM 自动更新，仅做 BOM 版本差异对比

**理由**:
- 任务说明中明确"完整的 BOM 自动应用（太复杂，留到 S4）"
- BOM 版本一致性和事务性需要谨慎设计
- BOM 对比已满足第一批需求（查看差异 → 人工操作更新）

---

## 11. 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| ECN→ECO 重命名导致前端兼容问题 | 低 | 中 | 保留 ECN 别名 + 旧 API 路由，前端逐步迁移 |
| S2 ChangeImpactEngine `analyze_bom_change()` 是TODO | 中 | 中 | 第一批通过 `analyze_prototype_change()` 路径复用，绕过 BOM 路径 |
| 认证失效规则需要业务专家定义 | 中 | 高 | 先实现基础规则（CDF直接匹配 + 类型匹配），复杂规则后续迭代 |
| 现有 ECR 数据无法迁移到新状态机 | 低 | 低 | 旧数据状态保持不变，新流程使用新状态；通过数据迁移脚本更新 |
| ECO Items 与 BOMItem 数据一致性 | 中 | 中 | 第一批不自动应用 BOM，仅做差异展示，依赖人工确认 |

---

## 12. 附录: 现有代码引用

### 现有 ECR 模型 (`backend/app/models/test.py`, 第 209-227 行)

```python
class ECR(Base):
    __tablename__ = "ecrs"
    id, ecr_no, title, product_code, change_type, trigger, status,
    description, impact_analysis, submitted_by, approved_by, org_id,
    created_at, updated_at
```

### 现有 ECN 模型 (`backend/app/models/test.py`, 第 230-250 行)

```python
class ECN(Base):
    __tablename__ = "ecns"
    id, ecn_no, ecr_id, title, product_code, change_scope, bom_changes,
    cdf_impact, certification_impact, status, effective_date, org_id,
    created_at, updated_at
```

### 现有 ChangeImpactRecord (`backend/app/models/change_impact.py`, 第 34-51 行)

```python
class ChangeImpactRecord(Base):
    __tablename__ = "change_impact_records"
    id, ecr_id(预留), prototype_id, changed_part, matched_rule_id,
    impact_level, affected_cert_types, analysis_detail, org_id, created_at
```

### 现有 Part CDF 标记 (`backend/app/models/bom.py`, 第 30-70 行)

```python
class Part(Base):
    # CDF相关
    is_cdf_item = Column(Boolean, default=False)
    cdf_type = Column(String(50), nullable=True)  # 安全件/EMC件/能效件
    cdf_cert_no = Column(String(100), nullable=True)
    cdf_expiry_date = Column(Date, nullable=True)
    market_cert_marks = Column(String(300), nullable=True)  # {"CE":true,"UL":false}
    mq_required = Column(Boolean, default=False)
    mq_status = Column(String(20), nullable=True)
```

---

> **文档结束** — 本计划基于现有系统状态(b3d1c1e)和 phase6-plan.md 的 S3 设计，聚焦第一批范围。
> 预计实施周期: 20 人天（4 个 Sprint）
> 建议与 S2 维护并行推进，避免阻塞。
