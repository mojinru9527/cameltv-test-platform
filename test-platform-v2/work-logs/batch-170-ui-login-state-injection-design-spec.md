# Batch 170 — Design Spec
> **Design (🎨)** | Date: 2026-08-13 | Status: 就绪

## 后端行为
| 项 | 规范 |
|----|------|
| UI_STORAGE_STATE_JSON | 环境加密变量，值为 Playwright storageState JSON；decrypt 失败按原值 |
| 临时文件 | system temp，每次执行唯一名，finally 删除 |
| PLAYWRIGHT_STORAGE_STATE | subprocess env 注入；playwright.config.ts use.storageState 读取 |
| 结果透出 | storage_state: bool；auth 注入失败不阻断执行（如实 false） |

## 前端
无 UI 变更（执行弹窗已支持 UI 环境选择）。
