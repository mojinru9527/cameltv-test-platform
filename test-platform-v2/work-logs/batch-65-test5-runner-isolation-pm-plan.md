# Batch 65 — PM Plan（Test5 验收执行器隔离 + 外部前置条件清单）

> **PM (🟨)** | Date: 2026-08-02

## 规格摘要

**原始需求**: PRD §1（Test5 与 AI 网络互斥 → 执行器隔离；前置条件清单）。本批为**零业务代码改动**的方案批次。
**目标时间**: 单批次（2026-08-02）。

## 开发任务

### [x] Task 1: Test5 执行器隔离方案设计
**描述**: 设计 WSL2/容器形态的 Test5 验收执行器：网络拓扑（主机 vpn07 全局 vs 执行器 OpenVPN）、
WSL2 与 Docker 与 VM 取舍、执行器职责（apitest/UI 自动化/环境探活对 Test5 的调用）、
与 ADR-0015 环境执行器契约对齐、验证矩阵与回退路径。
**验收标准**: 文档含 mermaid 拓扑、选型对比表、验证矩阵、batch-66 实测清单；无前后端代码改动。
**涉及文件**: 新增 `test-platform-v2/docs/operations/test5-runner-isolation.md`
**参考**: PRD §4、ADR-0015、`生产测试平台固定配置与双VPN切换验收手册.md`（已暂停）

### [x] Task 2: ADR-0017 决策落库
**描述**: 新增 ADR「Test5 验收执行器网络隔离（WSL/容器）」：背景、决策、后果、弃选方案
（本机路由分流 / 双机 / 切换模式）、分阶段实施；同步 ADR README。
**验收标准**: ADR 含弃选方案与证据（batch-64 实测）；README 索引新增 0017。
**涉及文件**: 新增 `docs/adr/0017-test5-runner-network-isolation.md`；更新 `docs/adr/README.md`
**参考**: ADR template、ADR-0015、batch-64 QA 报告

### [x] Task 3: 外部前置条件清单
**描述**: 把 Test5/VPN、AI/蓝湖/OCR、通知/缺陷/ELK、真机、旧 PG 快照、DevOps 基础设施、
DB/Redis/MQ 地址等前置条件整理为单份可勾选清单，含「提供物 / 存放位置 / 登记人 / 日期 / 授权范围」字段，
无明文 Secret。
**验收标准**: 7 类 12+ 项；每项可登记；与 C63-2 要求一致；与生产交付清单交叉引用。
**涉及文件**: 新增 `docs/production-delivery/外部前置条件清单.md`
**参考**: PRD §4、C-CONDITIONS C63-2、`docs/production-delivery/生产环境交付清单.md`

### [x] Task 4: 六部门工件与 C 条件
**描述**: 补齐 PRD/PM/Design/看板/QA/Leader；Leader 将 C65 条件追加到 C-CONDITIONS.md。
**验收标准**: 工件互相引用；C65 落库；`git diff --check` 通过。
**涉及文件**: `test-platform-v2/work-logs/batch-65-*.md`、`test-platform-v2/work-logs/kanbans/DEV-batch-65-*.md`、`C-CONDITIONS.md`

## 质量要求

- [x] 纯文档批次：0 业务代码改动
- [x] 无明文 Secret；OpenVPN 真实配置不入库（仅模板片段）
- [x] 文档遵循 document-standards 元数据约定
- [x] 方案与 ADR-0015/0016 无冲突
