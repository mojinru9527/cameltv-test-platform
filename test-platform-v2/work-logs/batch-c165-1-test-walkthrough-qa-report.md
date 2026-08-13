# Batch c165-1-test-walkthrough — QA 报告
> **QA (🔍)** | Date: 2026-08-13 | Verdict: PASS

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 6 | 6 | 0 | 0 |

## 可执行门禁
本批为 test 环境部署后验收 + 证据回写，无源码变更；CI 范围分类为 docs/evidence，前后端构建/全量回归将按 `main-quality-gate.yml` 分类器跳过。QA 以 Playwright 浏览器实测 + 后端 API 实测作为执行证据，不以下文件存在代替执行。

| 门禁 | 执行 | 结果 |
|------|------|------|
| test 前端可达 | Playwright 打开 Vercel 首页 / 登录 / 模块页 | ✅ 200，登录成功 |
| test 后端健康 | `GET /api/v1/open/health` | ✅ 200 `status=ok` |
| 后端菜单隐藏 | `GET /api/v1/system/menus`（test 账号 token） | ✅ 22 项，无 `menu:special` / `menu:perftest` |
| 接口资产分页 | `GET /api/v1/apitest/endpoints?page=1&page_size=20`（X-Project-Id=9） | ✅ total=899 / page_size=20 / items=20 |
| UI 走查 | Playwright 截图 + DOM 断言 | ✅ 证据目录 10 图 + 3 JSON |

## 逐条件验证
### C1: 菜单/命令面板/访客目录隐藏
| 检查项 | 结果 |
|--------|------|
| 登录后侧边栏无「专项测试」「性能监控」 | ✅ DOM 文本无命中，截图 `c165-1-1-menu-hidden.png` |
| Command Palette（Ctrl+K）搜索「专项」「性能」无结果 | ✅ 截图 `c165-1-1-command-palette.png` |
| 未登录游客目录无「专项测试」「性能监控」 | ✅ 截图 `c165-1-1-guest-catalog.png` |

### C2: 知识中心 12 tab 1024/1280 可切换且不裁切
| 检查项 | 结果 |
|--------|------|
| tab 数量 | ✅ 12（概览/项目知识/平台研发/检索/知识源/AI 审核台/图谱/实体/迭代/Wiki 知识库/知识差异对比/Skills） |
| 1024/1280 下 tablist 高度与裁切 | ✅ 高度 67px，clippedCount=0 |
| 逐 tab 点击切换 | ✅ 除默认「概览」外 11 个 tab URL 均出现 `?tab=`；DOM 结果见 `c165-1-results-part1.json` |

### C3: 接口资产 899 条时第 1 页 20 行
| 检查项 | 结果 |
|--------|------|
| 项目接口资产总数 | ✅ total=899（导入 test5-contracts 7 份真实契约） |
| 第 1 页行数 | ✅ 20 行（DOM 计数） |
| 分页 | ✅ 第 1/45 页 |
| 行内容含服务名/方法/路径/说明 | ✅ 首行 `camel-service | GET | /ee/activity/stream/admin_get | activity-stream-controller` |
| 截图 | ✅ `c165-1-3-apitest-assets-20-per-page.png` |

### C4: 接口用例可编辑参数/断言
| 检查项 | 结果 |
|--------|------|
| 接口用例 Tab 有可展开分组 | ✅ 展开后出现「编辑用例」按钮 |
| 点击编辑打开 CaseDrawer | ✅ 标题「编辑用例」 |
| 抽屉含 HTTP 方法 / 接口路径 / 请求参数 | ✅ |
| 抽屉含结构化断言规则 | ✅ 断言规则（status_code / response_time 等） |
| 截图 | ✅ `c165-1-4-apitest-case-edit-drawer.png` |

### C5: UI 自动化「用例/脚本」页签可用
| 检查项 | 结果 |
|--------|------|
| 页面级 Tab「任务 (0)」「用例 / 脚本」 | ✅ 两者均存在 |
| 「用例 / 脚本」区块 | ✅ 显示「UI 自动化用例」+「脚本资产（Playwright spec）」 |
| 截图 | ✅ `c165-1-5-uitest-cases-scripts-tab.png` |

### C6: 测试计划环境选择入口 + 纯人工计划提示
| 检查项 | 结果 |
|--------|------|
| 自动化计划（含 5 条 API 用例）头部显示「执行环境」 | ✅ |
| 自动化计划「执行」弹窗含「执行环境」 | ✅ 截图 `c165-1-6a-plan-env-selector-auto.png` |
| 纯人工计划（含 1 条 manual 用例）头部不显示「执行环境」 | ✅ |
| 纯人工计划「执行」弹窗显示「本计划仅含人工用例…标记为跳过」提示 | ✅ 截图 `c165-1-6b-plan-env-selector-manual.png` |

## 缺陷列表
| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 无 | - | 本批未发现新增缺陷 | - | - |

## 发布建议
状态: **READY** | 必修复: 0 | 建议修复: 0

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 1.5h vs 实际 2h | 0/0/0/0 | 1（studio-service 首次导入 502，重试成功） | 环境/大数据导入 | 大契约导入失败先重试，不要立即改代码 |

**技能使用**: playwright-skill → 浏览器走查与截图；vision → 关键截图复核；cameltv-agent-team → 轻量批次 QA 模板。
