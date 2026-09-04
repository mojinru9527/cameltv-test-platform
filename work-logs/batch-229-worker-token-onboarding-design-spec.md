# Batch 229 — Worker Token Onboarding Design Spec
> **Design** | Date: 2026-09-04 | Status: Ready

## 0. 技术体系确认

shadcn/ui + Radix + Tailwind + CVA；颜色使用 `border`、`bg-muted`、`text-muted-foreground`、`text-muted-hc` 等语义类，不引入裸色阶。

## 1. 信息架构

```text
Durable Runtime / Worker
  -> 接入 Worker 提示带
     -> 有 token:manage：生成 Worker Token
     -> 无 token:manage：联系管理员生成
  -> /system?tab=tokens&purpose=worker
     -> API Token 列表
     -> 新建 Token（用途预选 Worker 执行节点）
     -> 创建成功：一次性 Token + Worker 启动配置 + 管理旧 Token
```

## 2. 组件规格表

| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|-----------|----------|--------|
| Worker 接入提示带 | `border-y py-4`、文字与按钮 `gap-3` | 默认背景、边框语义色 | 按钮 `min-h-11`，无权限时不渲染 |
| 用途 Select | `h-9`，完整 label | 默认表单 Token | CI/CD / Worker 两项，键盘可选 |
| 一次性秘密区 | `rounded border p-3`，`code break-all` | `bg-muted` + 高对比正文 | 复制按钮有已复制/失败反馈 |
| Worker 配置区 | `pre whitespace-pre-wrap break-all` | `bg-muted` | 整体复制，关闭即清空 |
| Token 状态 | Switch + 中文 scope Badge | 既有语义 Token | 无 `token:manage` 时禁用 |

## 3. 布局与响应式

| 断点 | 布局 |
|------|------|
| 1440x900 | 接入说明与主操作同一行；表格完整展示 |
| 768x1024 | 提示带允许换行；弹窗宽度受 viewport 约束 |
| 390x844 | 操作按钮占可用宽度；Token/配置自动折行，不产生横向溢出 |

## 4. 状态设计

| 状态 | 反馈 |
|------|------|
| Token 列表加载 | 既有 `AsyncState` loading |
| Token 列表错误 | 既有 `AsyncState` error + 重试 |
| 无 Token | “暂无 API Token”空态 |
| 创建中 | 提交按钮禁用并显示加载状态，防重复创建 |
| 创建失败 | toast 显示后端 `detail/msg/message` 提取结果，弹窗保留 |
| 创建成功 | 明文和配置仅当前弹窗可见；关闭后清空内存状态 |
| 复制失败 | toast 明确提示手动选择复制 |
| 无创建权限 | Runtime 显示“联系拥有 API Token 管理权限的管理员” |

## 5. 安全与无障碍

- Token 明文只来自创建响应，不写 localStorage/sessionStorage/URL/日志。
- 证据截图不得在成功弹窗打开时采集；测试仅使用明确的虚构 `tpat_test_only`。
- 表单 `label/htmlFor`、Select `aria-label`、图标 `aria-hidden`；按钮名称完整可读。
- heartbeat 专用 Token 只授权 `workers:register`；不能用于 Worker 列表、drain、disable 或开放 API 其它能力。
- 轮换顺序：先创建新 Token并替换 Worker，再观察新心跳，最后停用/删除旧 Token，避免中断。

## 6. 设计 QA 预检

- P1：Runtime 指引不得只写“查看 Runbook”，必须落到实际前端入口。
- P1：创建用途不能让用户手填 raw scope，避免生成不可用 Token。
- P1：不得把 Token 写入页面 URL、审计 detail、截图或测试证据。
- P2：移动端 code/pre 必须折行；按钮触控高度至少 44px。

## 7. 设计签核

结论：通过。实现必须以 TDD 固定鉴权、深链、权限态、一次展示和空 Token fail-fast。

## 8. 设计 QA 补充验收

| 发现 | 修复锚点 | 验收结果 |
|------|----------|----------|
| 复制出的 Bash 配置仅赋值但未导出，子进程无法继承环境变量 | `test-platform-v2/frontend/src/pages/system/tokenPurposes.ts:31` | 改为 `export BACKEND_URL` 与 `export API_TOKEN`；单元测试及真实浏览器复制结果通过 |
| 系统管理多标签在 390px/768px 视口发生裁切和内容重叠 | `test-platform-v2/frontend/src/pages/system/index.tsx:59` | 标签列表允许换行并保持 44px 触控目标；两种视口截图与盒模型检查通过 |
| 768px 全局页头的项目名与操作文字互相遮挡 | `test-platform-v2/frontend/src/layouts/MainLayout.tsx:281`、`test-platform-v2/frontend/src/components/foolproof/AskAiButton.tsx:38` | `lg` 以下保留图标与无障碍名称、隐藏可见文字；768px 截图无重叠 |

补充签核：上述 P1/P2 设计问题均已关闭；桌面、平板和移动端关键路径通过，未发现新的阻断项。
