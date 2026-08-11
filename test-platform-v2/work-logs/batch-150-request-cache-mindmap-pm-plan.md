# Batch 150 — PM 计划（请求缓存/防抖/退避 + mindmap 聚合）

> **PM (🟨)** | Date: 2026-08-11 | 与 PRD 对齐

## 开发任务
### [ ] T1: 脚手架（工件 + 看板）
### [ ] T2: client cachedGet + clearApiCache（缓存+去重）
**涉及**: frontend/src/api/client.ts
### [ ] T3: menus/environments/domains 接缓存 + CRUD 清理
**涉及**: api/auth.ts、api/environment.ts、api/testcase.ts（fetchDomains/CRUD）
### [ ] T4: useDebouncedValue + defect 搜索防抖
**涉及**: hooks/useDebouncedValue.ts、pages/defect/index.tsx
### [ ] T5: usePerfWebSocket 轮询指数退避
**涉及**: hooks/usePerfWebSocket.ts
### [ ] T6: integration 探针改 stats
**涉及**: pages/integration/index.tsx
### [ ] T7: mindmap 改用 taxonomy 聚合
**涉及**: pages/mindmap/index.tsx、pages/mindmap/caseTaxonomy.ts、mindmap/index.test.tsx
### [ ] T8: 测试 + 冒烟
**涉及**: client cache 测试、useDebouncedValue 测试、mindmap 测试更新、Network 冒烟

## 质量要求
- [x] 无 N+1/重复请求
- [x] useEffect 清理（timer/abort）
- [x] 单测覆盖缓存/防抖/脑图
- [x] 无 console 报错
