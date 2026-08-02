# Batch 67 — PM Plan（AI 验收与正式域名发布前置条件收口）

> **PM (🟨)** | Date: 2026-08-02

## 规格摘要
**原始需求**: 按 `docs/production-delivery/外部前置条件清单.md` 收口 2.x（AI/蓝湖/OCR 凭据）与 6.1（DevOps 服务器），
登记真实状态（C63-2），解锁平台 AI 验收与正式域名发布的前置条件。
**目标时间**: 2026-08-02（本批）；用户换 Key 与 Railway URL 为外部解锁项。

## 开发任务

### [x] Task 1: 清单 2.x/6.1 状态与登记更新
**描述**: 更新 `外部前置条件清单.md` §2 与 §6.1：2.1 先标 ⏳（实测 401），用户换新 Key 实测 200 后标 ✅；
2.2 ✅（蓝湖账密已写入 backend/.env、Cookie 在 lanhu-mcp/.env）；2.3 ✅（本地 PaddleOCR 无需云凭据）；
6.1 ⏳（待 Railway URL 或服务器地址，附解锁步骤引用手册 §1）。
**验收标准**:
- 状态列与 QA 实测一致；登记列含提供人/日期/授权范围/证据位置
- 无明文 Secret；2.1 仅在有 200 实测证据后标 ✅（C63-2）
**涉及文件**: `docs/production-delivery/外部前置条件清单.md` — §2/§6.1 行
**参考**: PRD §2/§3；DevOps 手册 §1

### [x] Task 2: 凭据实测证据采集（QA 协同）
**描述**: 读取 backend/.env 中 `AI_API_KEY`（不回显），调用 DeepSeek `/models`；扫描 .env 占位符；
核对蓝湖/OCR 键存在性。
**验收标准**: 记录命令、HTTP 状态码与结论；证据写入 QA 报告。
**涉及文件**: `test-platform-v2/backend/.env`（只读，gitignored）
**参考**: PRD §5

### [x] Task 3: 六部门工件 + 看板
**描述**: 产出 PRD/PM/Design/QA/Leader 工件与 `kanbans/DEV-batch-67-ai-acceptance-release.md`，
看板记录 Slice 状态与阻塞。
**验收标准**: 工件齐全、命名规范、看板当前位置明确。
**涉及文件**: `test-platform-v2/work-logs/batch-67-ai-acceptance-release-*.md`、`kanbans/DEV-batch-67-ai-acceptance-release.md`

### [x] Task 4: C-CONDITIONS 追加 C67 条件
**描述**: Leader 判决后把 C67-1~C67-3 追加到 C-CONDITIONS.md Open 节。
**验收标准**: C 编号与判决一致，登记日期/来源批次。
**涉及文件**: `C-CONDITIONS.md`

### [x] Task 5: requirements.lock 跨平台依赖修复（B67-Q3）
**描述**: Railway 构建在 pip 依赖阶段失败——锁文件为 Windows 环境生成，缺平台标记与 Linux 依赖。
修复：`pywin32==312` 加 `sys_platform == "win32"` 标记；补 `secretstorage==3.5.0` / `jeepney==0.9.0`
（`sys_platform == "linux"`）与 `uvloop==0.22.1`（`sys_platform != "win32"`）哈希锁。
**验收标准**: `docker build --target builder` 0 错误；Windows 本地安装不受影响（标记隔离）。
**涉及文件**: `test-platform-v2/backend/requirements.lock`

## 质量要求
- [x] 密钥扫描 0 命中（无 password/token/key/cookie 明文入库）
- [x] `git diff --check` 通过
- [x] 清单状态与 .env 实测一致，禁止补登假证据（C63-2）
- [x] 变更以文档为主，唯一代码文件为 requirements.lock（依赖锁），本地 Docker 构建验证通过
