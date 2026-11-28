# AIQE V1.6.2 整改 — 并行 Agent 协作简报

**工作目录（唯一）**：`F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v162-hardening`
**分支**：`feature/aiqe-v162-hardening`（基线 `origin/main` = `2d2f508d5d1fd452972e7af49d9b4f3bde2e7b01`）
**整改手册**：`C:\Users\26029\Downloads\CamelTv_AIQE_V1.6.2_整改开发落地实施手册.md`（1389 行，先读相关章节）
**复审基线报告**：`C:\Users\26029\Downloads\CamelTv_AIQE_V1.6_Main_9bbbdbb_Code_Audit.md`

## 已落地的共享基础设施（不要重复实现、不要破坏）

- `scripts/aiqe/statuses.py`：唯一状态词表（PASS/FAIL/BLOCKED/NOT_RUN/NOT_PROVEN/PARTIAL/WAIVED/UNKNOWN）；
  `SEMI_AUTOMATIC/MANUAL/SCREENSHOT` 只能映射 `PARTIAL`；只有 `PASS` 计入通过。
- `scripts/aiqe/validators/models.py`：`GateCheck`（`add()` 自动降级到 NOT_PROVEN，`note()` 不降级）。
- `scripts/aiqe/validators/{runtime_index,product_tc,platform,production,branch,provenance,acceptance,common}.py`
  - `runtime_index.validate_runtime_index(...)`
  - `product_tc.validate_product_config(...)` / `validate_product_results(...)`
  - `platform.validate_platform_results(...)`
  - `production.validate_production_evidence(...)`
  - `branch.validate_branch_protection(...)`，`AIQE_AGGREGATE_CHECK = "AIQE V1.6 Governance Gate"`
  - `provenance.validate_provenance(...)`
  - `acceptance.validate_acceptance_identity(...)` / `verify_github_identity(...)`
- `scripts/aiqe/release_verdict.py` 已接入上述 validator：Gate E 不再因矩阵 10/10 PASS，
  `--require-ga` 在 `runtime ga_ready=false` 时退出 1。测试：`tests/test_aiqe_v162_release_verdict.py`（13 passed）。

## 铁律

1. **禁止假 PASS**：缺 Runner/环境/断言/artifact/SHA/审批 → `BLOCKED`/`NOT_PROVEN`/`PARTIAL`。
   不得降低断言、删除失败用例、改写历史结果来制造通过。
2. **不要动别人的文件**（见任务分配）。不要修改 `scripts/aiqe/statuses.py`、`validators/models.py`、
   `validators/product_tc.py`、`validators/runtime_index.py`、`validators/platform.py`、
   `validators/production.py`、`validators/branch.py`、`validators/provenance.py`、`release_verdict.py`
   （除本任务明确允许的文件）。
3. **不要 git commit / push / 切分支 / 改 GitHub 设置**。所有改动留在工作区，由 lead 统一审查提交。
4. **不要运行全量 pytest / 前端构建**（太慢）。只跑本任务相关测试，命令：
   `cd test-platform-v2/backend; $env:PYTHONIOENCODING="utf-8"; python -m pytest tests/<file> -q -p no:cacheprovider`
5. 每个交付必须包含：实现 + 正向测试 + 反向测试 + 文档/证据 + 明确的未完成项（BLOCKED 原因）。
6. 不要写真实密码/token。外部账号/生产环境/真实 Reviewer 无法获得时，如实 BLOCKED，并写 owner/unblock_action。
7. Python 用 3.12，UTF-8；新文件行尾 LF。不要写 emoji。

## 测试与验收通用要求

- 修改脚本后，至少运行：本任务测试 + `tests/test_aiqe_v162_release_verdict.py` + 原有相邻测试。
- `python scripts/aiqe/check_release_audit.py` 必须保持 0 error（生成型文档若变化，用生成器重写）。
- 不新增 lint/类型问题：`ruff check <改动的 py 文件>` 通过（仓库根可执行）。

## 完成后回复格式

- 改动文件清单（绝对/相对路径）
- 每个 FIX 的完成状态：VERIFIED / PARTIAL / BLOCKED（附原因）
- 运行的测试命令与结果（pass/fail 数量）
- 仍未完成项与下一步
