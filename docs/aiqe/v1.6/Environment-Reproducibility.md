# V1.6 测试环境可复现性与分层（V16-022）

> 目标：空白机器按本文一次性安装后可复现 AIQE 后端测试；CI 与本地使用同一锁定版本与同一分层命令。
> 最后核对：2026-11-19（V1.6 开发分支）

## 1. 固定版本

| 组件 | 版本 | 来源 |
|---|---|---|
| Python | **3.12.10** | `python --version`；CI `PYTHON_VERSION=3.12` |
| Node.js | **>= 22.22.0**（CI 22.x；本地 24.15.0 兼容） | `test-platform-v2/frontend/package.json` `engines` |
| pnpm | **11.21.0** | `pnpm --version`（仓库 `packageManager` 约束） |
| Playwright | **1.61.0** | `requirements.txt` / `requirements.lock` |
| Chromium | **149.0.7827.55** | Playwright 1.61 自带；`playwright install chromium` |
| pytest | **9.1.1**（lock 固定） | `requirements.lock` |
| bcrypt | **5.0.0**（lock 固定） | `requirements.lock`（历史报告缺失导致 conftest 加载失败，已修复） |

## 2. 一次性安装（空白环境）

```powershell
# 1) Python 依赖：优先用锁文件（含 hash），不使用全局包
cd test-platform-v2/backend
python -m pip install --upgrade pip
python -m pip install -r requirements.lock
python -m pip install -r requirements-quality.txt

# 2) 浏览器（真实 Chromium，V16-002 需要）
python -m playwright install chromium

# 3) 前端（仅前端改动需要）
cd ../frontend
pnpm install --frozen-lockfile
```

CI 使用同一份 `requirements.lock`；任何依赖安装失败即 Gate 失败，**不得**把安装失败计为测试通过。

## 3. 测试分层

`pytest.ini` 声明 `unit / integration / api / service / worker / browser / device / e2e / security / migration` 标记；
执行器 `scripts/ci/run_aiqe_layer.py` 把层映射到具体测试集合并输出 JUnit：

```powershell
python scripts/ci/run_aiqe_layer.py --list
python scripts/ci/run_aiqe_layer.py unit  --junit work-logs/evidence/aiqe-v16/junit-unit.xml
python scripts/ci/run_aiqe_layer.py security --junit work-logs/evidence/aiqe-v16/junit-security.xml
python scripts/ci/run_aiqe_layer.py browser --junit work-logs/evidence/aiqe-v16/junit-browser.xml
python scripts/ci/run_aiqe_layer.py device  --junit work-logs/evidence/aiqe-v16/junit-device.xml
python scripts/ci/run_aiqe_layer.py integration --junit work-logs/evidence/aiqe-v16/junit-integration.xml
```

迁移门禁（非 pytest）：

```powershell
python scripts/ci/check_aiqe_v16_migrations.py
python -m alembic upgrade head
python -m alembic downgrade -1
python -m alembic upgrade head
```

## 4. CI 产物

- `junit-*.xml`（每层一份）
- `coverage.xml`（`--cov=app/aiqe --cov-report=xml`）
- Playwright Trace / 截图（browser 层，失败时上传）
- `evidence-index.json`（V16-023 生成器，含 commit SHA / CI Run / Run/Job/Assertion/Artifact ID）

产物保留 90 天；证据索引与 JUnit 缺失时不得宣称 E2E 通过。

## 5. 已知边界

- 真实设备（Android/iOS/小程序）需要设备池/Runner；本地无设备时相关层结果为 **BLOCKED**，不得 SKIP 后计入 PASS。
- Windows 本地 SQLite 与 CI Linux 均为测试环境；生产 PostgreSQL 迁移由迁移 Job 单独验证。
- 浏览器版本随 Playwright 升级而升级，升级需同步本表与 `requirements.lock`。
