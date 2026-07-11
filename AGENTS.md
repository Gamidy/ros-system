# 吉德家用变频空调PLM系统 — 工程契约

> 本项目遵循 [vibe-coding 38条通用编程原则](https://github.com/nousresearch/hermes-agent)
> 引用自 `~/.hermes/skills/software-development/vibe-coding/`

---

## 技术栈

| 层级 | 技术 | 版本 |
|:---|:---|:---|
| 后端框架 | FastAPI | 0.115+ |
| ORM | SQLAlchemy | 2.0+ |
| 数据库 | PostgreSQL | 16 |
| 前端框架 | Vue 3 Composition API | 3.4+ |
| 语言 | TypeScript strict | 5.4+ |
| UI库 | Element Plus | 2.7+ |
| 构建工具 | Vite | 5+ |
| 测试 | pytest + Vitest | latest |

## 项目专用规则

### 后端 (backend/)
1. **API版本化**: 所有路由在 `/api/v1/` 下
2. **分层架构**: models/ → crud/ → schemas/ → api/ (不允许跨层调用)
3. **CRUD层**: 继承 `CRUDBase[T]`，禁止在API路由中直接写SQL
4. **Pydantic v2**: 使用 `model_validate` 和 `model_dump`
5. **异步优先**: 所有数据库操作用 `async def` + `AsyncSession`
6. **禁止裸 except**: 全部使用 `logger.exception("msg")`

### 前端 (frontend/)
1. **TypeScript strict mode**: 零 `any`
2. **Composition API + `<script setup>`**: 不混用 Options API
3. **状态管理**: Pinia
4. **API调用**: 统一通过 `src/api/index.ts` 的 axios 实例
5. **组件≤300行**: 超过拆分为 composables
6. **路由守卫**: authStore + hasRouteAccess

### 通用
1. **TDD**: 先写测试(RED)→后写实现(GREEN)→再重构(REFACTOR)
2. **Small Commits**: ≤200行/提交
3. **文件≤600行**: 超过必须拆分
4. **禁止硬编码**: 配置值全部走环境变量/Settings

## 设计文档

完整设计规范位于 `../plm-design/` 目录（59份文档）。
核心引用:
- `01-IPD-process-phase-gate.md` — IPD流程与阶段门
- `02-core-data-model.md` — 8层ERD核心数据模型
- `08-technical-architecture.md` — 五层微服务架构

## 快速启动

```bash
docker compose up -d          # 启动全部服务
docker compose exec backend alembic upgrade head  # 数据库迁移
docker compose exec backend python seed.py         # 种子数据
```

## 禁止行为

- ❌ 跳过TDD直接写实现代码
- ❌ 在API路由中直接 `db.query()` (应通过CRUD层)
- ❌ 硬编码配置值（密码/URL/密钥）
- ❌ 混用 `async def` 和同步ORM操作
- ❌ 提交包含 `print()` 或 `console.log()` 的调试代码
- ❌ 一次提交超过3个文件（无AI-Z审核）
