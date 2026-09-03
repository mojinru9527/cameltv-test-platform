# Batch 228 — Design Spec

> Design | Date: 2026-09-03 | Status: ready | Executor: Codex

## 0. 技术体系确认

沿用 shadcn/ui + Radix + Tailwind + CVA。颜色只使用现有语义 token；图标复用 Lucide；不新增营销式区块、渐变或装饰动效。

## 1. 状态语义

| 位置 | 状态 | 展示 | 可执行动作 |
|------|------|------|------------|
| 新业务接入 | baseline ready / durable blocked | “业务接入基线已就绪” + “可选耐久执行尚未就绪” | 可继续普通接入；管理员可前往 Runtime |
| Worker 表 | ONLINE | 在线、能力、最后心跳 | 排空、禁用 |
| Worker 表 | OFFLINE | 离线、最后心跳、恢复说明 | 重新检查；不伪造远程启动按钮 |
| Worker 表 | DRAINING/DISABLED | 明确中文状态 | 重新检查；不展示无效操作 |
| Runtime 加载 | loading | 稳定加载态 | 刷新按钮禁用并旋转 |
| Runtime 失败 | error | 错误原因 | 原位重新检查 |
| 范围/场景 | loading/data/empty/error | 一次请求对应一次稳定状态转换 | 成功写操作后单次刷新 |

## 2. 组件规格

| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|-----------|----------|--------|
| Runtime 页头刷新 | `Button size=sm variant=outline`，图标 `size-4` | 默认 foreground/border | loading 时 disabled + `animate-spin` |
| 离线说明 | 表格上方无嵌套卡片的 `border-y py-3` 信息带 | `text-status-warning` + `text-muted-hc` | 含明确“重新检查”按钮 |
| Worker 表 | 现有 Table，长心跳允许换行 | Badge 使用现有状态 token | 在线才显示排空/禁用；其它状态显示文字原因 |
| 接入摘要 Badge | 基线 ready 用 success；可选耐久 blocked 用 warning/neutral | 不使用 destructive 误导整体失败 | 状态同时有文本，不只靠颜色 |

## 3. 文案规范

- 接入摘要：`可选耐久执行尚未就绪`。
- 边界说明：`不影响当前业务接入和同步基线；只有可恢复的 AITDE 执行才需要 Temporal 和在线 Worker。`
- Worker 离线：`Worker 已停止心跳。请管理员检查 Worker 进程、Control Plane 地址和网络连接；恢复后会自动变为在线。`
- 空列表：`尚未发现 Worker。请管理员按部署 Runbook 启动执行节点后重新检查。`
- 禁止展示要求普通 tester 执行 shell、Docker 或凭据配置的文本。

## 4. 响应式与无障碍

- 页头与离线说明在窄屏 `flex-wrap`；按钮触控目标不低于 44px。
- 表格沿用当前横向容器行为，长时间戳和恢复说明不得覆盖相邻列。
- 刷新图标设置 `aria-hidden`，按钮有可见中文名称；离线说明使用 `role=status`，错误使用 `role=alert`。
- 390×844、768×1024、1440×900 三视口必须 `scrollWidth == clientWidth`。

## 5. 设计 QA 走查发现

### P1-01 耐久状态层级误导

`frontend/src/pages/onboarding/index.tsx:300` 把 `durable_ready=false` 渲染成 danger Badge，与 `baseline_ready=true` 并列，容易被理解为业务接入失败。改为“可选耐久执行”并直接说明不影响当前接入。

### P1-02 Worker 离线时没有下一步

`frontend/src/pages/runtime/components/WorkerHealthTable.tsx:49` 只对 ONLINE 渲染操作，OFFLINE 的操作列完全空白。增加页面级恢复说明与刷新动作，保留远程进程不可由网页启动的安全边界。

### P2-01 Runtime 请求失败被静默吞掉

`frontend/src/pages/runtime/index.tsx:51` 对非取消错误直接返回但不保存错误状态，用户会看到空数据。补齐 error + retry 四态。

### P2-02 能力列呈现错误事实

`frontend/src/pages/runtime/components/WorkerHealthTable.tsx:46` 正确读取 `capabilities`，但后端列表省略字段，导致 UI 稳定显示“无”。设计不增加前端详情 N+1 请求，要求后端列表契约直接返回。

## 6. 设计签核

结论：规范就绪。实现必须通过离线态组件测试、接入文案测试和三视口浏览器走查后才可签核为通过。

风格库核对选择 `ui-screenshot-system` 的产品界面方向，仅采用其“固定层级、可读标签、明确状态与操作区”原则；配色、字体、圆角和组件继续服从仓库既有 token，不生成或引入新的视觉素材。
