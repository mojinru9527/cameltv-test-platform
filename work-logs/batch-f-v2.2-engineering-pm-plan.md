# 批次 F — V2.2 工程化基线 + 追溯增强 PM 计划

> 日期：2026-07-02 | PM: PM Department | 批次编号：批次一（V2.2 起步）

## 背景

P1 安全基线（批次 A-E、8/8 项）已于 2026-07-02 全部合并至 develop。现在启动 backlog 中的**批次一**（Epic G + T），聚焦工程化健康度与质量追溯能力。

## 侦察发现（关键调整）

| 原计划 | 侦察结论 | 策略 |
|--------|---------|------|
| T1（覆盖率聚合接口） | **已存在** — `GET /trace/coverage`、`GET /trace/case/{id}`、`GET /trace/requirement/{doc_id}` 均已实现 | 增强而非新建：补齐缺失指标 + 前端覆盖 |
| T2（追溯矩阵可视化） | **基础已有** — `/trace` 路由和页面已存在（`trace_service.py` 348 行） | 审核并增强 UI，确保「覆盖率色阶 + 下钻」可用 |
| G2（消除 N+1） | **5 处确认** — 其中 2 处严重（report_service, project_service） | 按严重度分 2 轮修复 |
| G3（事务装饰器） | **transaction() 已存在**但只用 4 次 — 大部分路由裸写 db.commit() | 关键路径先覆盖 |
| G4（测试基建） | 后端 88 tests 全在安全回归，前端 7 tests 只有 utils | 补 3 条关键业务路径 |

## 调整后实施计划

| # | 任务 | 原预估 | 调整后 | 理由 |
|---|------|--------|--------|------|
| G1 | 密钥外置 + 启动拦截 | 4h | **3h** | 改动集中在 config.py + seed.py |
| G2 | N+1 修复 + 分页统一 | 6h | **8h** | 5 处 N+1 + 分页模式统一 |
| G3 | 事务装饰器推广 | 5h | **4h** | transaction() 已有，只需推广+修 bug |
| T1/T2 | 追溯矩阵 API 增强 + 前端 | 12h | **6h** | 基础已有，增强而非新建 |
| G4 | 测试基建补强 | 6h | **6h** | 3 条关键路径 + CI 骨架 |
| **合计** | | **33h** | **27h** | 因 T1 基础已有节省 6h |

## 交付切片

### Slice 1 (G1): 密钥外置 — 1.5h
- config.py: 移除硬编码 fallback 密钥/密码
- seed.py: tester 密码环境变量化
- .env.example: 补充缺失项
- 启动时强制校验生产模式必填项

### Slice 2 (G2 round 1): 严重 N+1 修复 — 3h
- report_service._build_content: 批量查最新 execution trace_id
- project_service.list_all_projects: 用 batch_user_names 替换逐条 get
- role_service.list_roles: 预加载 RolePermission + Permission
- 验证：页面上线后查询数减少

### Slice 3 (G2 round 2): 分页统一 + 中等 N+1 — 3h
- 推广 paginate() helper 到全部 service
- 统一 Page[T] schema 响应格式
- trace_service.get_case_detail: 批量查 executions
- report_service.get_trends: 批量查 open defects

### Slice 4 (G3): 事务推广 — 2h
- import_cases 原子性修复（内部异常重抛）
- 关键多写入方法加 transaction() 包装
- audit 日志补写

### Slice 5 (T1/T2): 追溯增强 — 3h
- 后端: requirement_coverage_rate 指标补全
- 后端: 缺失关系的 ORM relationship 补充
- 前端: 追溯页面 UI 审核 + 覆盖率色阶优化

### Slice 6 (G4): 测试基建 — 3h
- 后端: auth 关键路径 pytest (3 条)
- 后端: test_plan 执行闭环 pytest (2 条)
- 前端: useApi hook vitest (3 条)
- CI 骨架: .github/workflows/test.yml

## 风险

| 风险 | 概率 | 缓解 |
|------|------|------|
| G1 密钥轮换后 AI 功能中断 | 中 | 保留 .env 备份，验证 DeepSeek API 连通性 |
| G2 批量查询改动引入回归 | 低 | 每条修复后跑对应模块页面功能测试 |
| G3 事务推广改动面大 | 低 | 只覆盖关键多写入路径，不全量改 |

## 验收标准

- [ ] `.env` 中不包含硬编码 secret key 回退值
- [ ] 生产模式启动时 secret_key/admin_password 为空则拒绝启动
- [ ] report_service 列表页查询数降低 80%+
- [ ] project_service 列表页查询数为常量（不随项目数增长）
- [ ] 所有分页 API 统一使用 Page[T] 响应
- [ ] import_cases 异常时完整回滚（不留半成品）
- [ ] 新增 test 文件 ≥ 3 个，覆盖 ≥ 8 条新增用例
- [ ] 追溯页面色阶可读、需求→用例→执行→缺陷链完整

## 批次一状态

```
批次 F (2026-07-02): G1+G2+G3+G4+T1/T2 → develop
预计工时：27h
```
