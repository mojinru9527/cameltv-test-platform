# Batch 66 — PM Plan（Test5 验收执行器搭建）

> **PM (🟨)** | Date: 2026-08-02

## 规格摘要

**原始需求**: PRD §1（窗口 2026-08-03 11:00–18:00 + WSL2 形态 → 搭建执行器）。
**目标时间**: 本批交付物 2026-08-02 完成；实测在窗口内。

## 开发任务

### [x] Task 1: WSL2 执行器安装脚本
**描述**: `scripts/executor/wsl2-executor-setup.sh`：tun 检查/创建、apt 安装 openvpn、部署 .ovpn、
写入凭据文件（chmod 600，不入库）、后台启动、验证提示。
**验收标准**: `bash -n` 通过；含 --ovpn/--auth-user 参数校验；无真实 CA/凭据。
**涉及文件**: 新增 `scripts/executor/wsl2-executor-setup.sh`
**参考**: ADR-0017、test5-runner-isolation.md §4

### [x] Task 2: 执行器 README
**描述**: 前置（发行版安装）、安装用法、V1–V5 验证矩阵登记表、日常启停、安全约束。
**验收标准**: 覆盖窗口执行全流程；无明文 Secret。
**涉及文件**: 新增 `scripts/executor/README.md`

### [x] Task 3: 前置条件登记
**描述**: 清单 1.1（窗口）与 1.5（WSL2）状态置 ✅ 并登记提供人/日期/授权范围。
**验收标准**: 登记字段完整，与聊天记录一致。
**涉及文件**: `docs/production-delivery/外部前置条件清单.md`

### [x] Task 4: 六部门工件与 C 条件
**描述**: PRD/PM/Design/看板/QA/Leader + C66 条件落库。
**涉及文件**: `test-platform-v2/work-logs/batch-66-*.md`、`kanbans/DEV-batch-66-*.md`、`C-CONDITIONS.md`

## 质量要求

- [x] 脚本 `bash -n` 语法通过；零业务代码改动
- [x] 无明文 Secret/CA；凭据仅本地文件
- [x] 文档遵循 document-standards
