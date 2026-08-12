# Batch 156 — Design Spec（P3 打磨项收口）

> **Design (🎨)** | Date: 2026-08-12 | Status: 就绪

## 0. 技术体系确认
shadcn/ui + Radix + Tailwind；后端 FastAPI。

## 1. 组件规格表
| 组件 | 规格 |
|------|------|
| NotFound 页 | 居中 404 + 文案「页面不存在或已被移动」+ 返回工作台按钮（primary） |
| 脑图容器 | tabIndex=0 + role="region" + aria-label「用例脑图（支持键盘缩放/平移）」+ 提示条「可用 Ctrl+滚轮 缩放、方向键平移」 |
| Playground 提示条 | 检测 spec 含「未识别步骤」→ Badge/Alert「存在未识别步骤，需人工补充」 |
| 用例搜索提示 | 筛选生效时 `text-xs text-muted-foreground`「当前搜索在已选域/模块内生效」 |

## 2. 状态核对
| 组件 | 默认 | 未启用 |
|------|------|--------|
| theme-lab | 可访问 | 统一说明页（非「建设中」），注明全局主题切换不受影响 |

## 3. 无障碍
- NotFound/脑图/提示均含 aria；焦点可见（全局 focus ring）。

## 4. 设计签核
结论：通过
