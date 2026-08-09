# Batch 130 — PM Plan（用例模块聚合与异常覆盖加固）
> **PM (🟨)** | Date: 2026-08-09

## 开发任务

### [x] Task 1：规范化分类事实源

- 新增纯函数，将原始 `domain/module/case_type` 映射为 `surface/业务域/业务子路径`。
- 去除完整终端节点及 PC/Web/移动端后缀，合并重复路径片段；保留未知域为“其他”。
- 以旧 Batch 110/122/125 代表数据做参数化回归。

### [x] Task 2：taxonomy 与列表筛选闭环

- taxonomy 使用规范化业务域和路径聚合计数。
- 列表新增 `surface/taxonomy_domain/taxonomy_module/positive_negative/case_id` 查询。
- 规范节点按前缀聚合子树；分页 total、列表和 taxonomy 计数守恒。

### [x] Task 3：用例服务异常场景可视化

- 前端分类树和域/模块下拉改用 taxonomy 契约，不再把显示节点回传为原始 domain。
- 增加“全部场景/正向/负向/边界”筛选和表格标签。
- 保持默认功能用例、四态、请求清理、响应式和键盘可操作。

### [x] Task 4：全量导入器修复

- 生成跨模块稳定唯一 `case_id`；API 支持精确 case_id 查重。
- 导入器接收集合模块上下文，写入规范 domain/module，并把 client scope/platforms 转成 `端:*` tags。
- 增加 mocked API 幂等测试，覆盖“项目有无关用例”“同编号跨模块”“重复执行”。

### [x] Task 5：异常覆盖 overlay 与质量门禁

- 为 38 个业务模块补充可执行的故障恢复、重复/并发用例；按模块主操作给出具体数据与副作用断言。
- 合并时补齐历史深度用例的 `positive_negative/case_design_method/test_data_note`。
- 新增质量审计：38/38 正负向、对抗维度、必填字段、稳定 ID、规范节点无终端壳层、计数守恒。

### [x] Task 6：QA、浏览器与交付

- 相关测试先行，再跑后端受影响 pytest/F821/全量、前端 Vitest/typecheck/build/全量。
- 运行 consolidated dry-run 与质量审计，保存脱敏 JSON 证据。
- 1440×900、768×1024、390×844 走查分类聚合、异常筛选、详情标签与 Network。
- 完成 QA、Leader、复盘、C 条件审计；用户总确认后才推送/PR/合入。

## 质量要求

- [x] 规范化函数纯净、确定、幂等，未知数据不静默误归。
- [x] 终端差异可追溯但不成为 taxonomy 节点。
- [x] 每个业务模块至少一正一负；所有补充场景有可观察副作用断言。
- [x] 导入精确查重、稳定 ID、重复执行零新增。
- [x] 列表/分类计数守恒，单次筛选不产生 N+1。
- [x] 前端异步 effect cleanup、无 Radix 空 value、桌面/平板/手机可用。
