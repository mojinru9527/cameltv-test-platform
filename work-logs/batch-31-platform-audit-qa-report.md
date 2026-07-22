# Batch 31 — QA 报告

> **QA (🔍)** | Date: 2026-07-22 | Verdict: **PASS（本地）/ 生产需求 NEEDS WORK**

## 1. 可执行门禁

| 检查 | 结果 | 证据摘要 |
|---|---|---|
| 后端 F821 | PASS | `ruff check app --select F821`，0 error |
| 后端全量 | PASS | 653 passed，5 warnings，224.96s（最终补丁复验） |
| 后端专项 | PASS | 蓝湖/性能/用例 65 passed |
| Alembic | PASS | 单 head；revision 长度测试 1 passed |
| 前端 typecheck | PASS | `tsc -b` exit 0 |
| 前端干净安装 | PASS | `npm ci`，897 packages installed |
| 前端全量 | PASS | 22 files / 96 tests passed，7.82s |
| 前端 build | PASS | 3328 modules，7.13s |
| UI 告警专项 | PASS | Lanhu Drawer + API Case 5 passed，无 ref/button nesting 警告 |

## 2. 页面级验收

### 测试平台知识中心

- 桌面：标题、统一检索、13 个知识视图、健康度、项目球正常渲染；标签滚动被限制在局部。
- 移动 390×844：搜索输入/模式/按钮纵排；顶栏无遮挡；修复后 `scrollWidth=clientWidth=375`。
- 项目球：发布包、深度、图谱/列表、刷新与节点/关系统计可见，无 console error。
- 版本任务：旧入口重定向后显示“版本发布包”，具备新建、搜索、状态筛选和空状态。
- 局限：本地新库无真实蓝湖发布包数据，因此未宣称完成有数据的导入→diff→确认端到端；相关 API/组件由全量测试覆盖。

### 蓝湖 vs 生产站点

| 验收项 | 蓝湖最新要求 | 生产 `camel1.tv` | 结论 |
|---|---|---|---|
| 用户首页赛事回放入口 | 15.0 / 2026-07-20 | 桌面、移动首页 DOM 均无 Replay/赛事回放入口 | FAIL |
| 回放列表/详情（MB/PC） | 15.0 / 2026-07-20 | 无入口，无法从生产完成路径 | BLOCKED/FAIL |
| 运营后台赛事回放管理 | 9.0 / 2026-07-20 | 未提供后台生产地址/账号 | BLOCKED |
| 生产首页基础可用性 | — | 桌面布局完整；移动可用但信息紧凑 | PASS with notes |

生产控制台仅观察到 Google FedCM/令牌网络告警，未发现页面脚本崩溃。未执行需要真实用户账号的登录、支付或后台写操作。

## 3. 发布建议

- 本批测试平台修复：允许进入 Draft PR。
- 体育项目最新回放需求：当前生产不符合最新蓝湖版本，不能签收。
- 合并前：GitHub CI 必须通过，并由审查者确认依赖漏洞与 Ruff 债务不在本批处理范围。
