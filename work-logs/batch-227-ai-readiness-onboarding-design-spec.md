# Batch 227 — Design Spec

> Design | Date: 2026-09-03 | Status: ready | Executor: Codex

## 1. 信息架构

页面标题改为“AI 全链路接入”。首屏按任务顺序排列，不使用营销式 hero：

1. “你需要填写”：六项业务输入，双栏到单栏响应式收缩。
2. “平台自动检查”：AI、Temporal、Runtime Worker 三行状态，不允许嵌套卡片。
3. “接入进度”：登记后出现四步真实动作。
4. “已接入业务”：紧凑列表，显示服务、版本、步骤和状态。

## 2. 组件与文案

- 复用 `@/ui` 的 PageShell、Card、Input、Textarea、Label、Button、Badge。
- 状态图标使用 Lucide：`CircleCheck`、`CircleAlert`、`Loader2`、`Settings`；颜色只用语义 token。
- 字段必须有 `label htmlFor`，placeholder 只放示例，不承担标签职责。
- 主按钮用明确动宾文案：“保存并开始接入”“导入接口基线”“生成 AI 验收方案”“运行真实基线”。
- 运行时说明统一为：“由平台常驻管理，无需每次手动启动”。不可向 tester 展示 shell 命令。

## 3. 状态

| 状态 | 显示 | 下一步 |
|------|------|--------|
| loading | 结构稳定的三行 skeleton/加载态 | 无 |
| ready | “已就绪” | 无 |
| unknown | “尚未验证” | 前往 AI 配置测试 |
| blocked | 简短原因 | 前往 AI 配置或 Runtime 管理 |
| API error | “自动检查失败” | 原位重试 |

`baseline_ready` 只受 AI 真实健康态约束；OpenAPI/Base URL 由当前接入动作做真实校验。`durable_ready` 额外要求 Temporal 已配置且有在线 Runtime Worker。

## 4. 响应式与无障碍

- ≥768px：字段两列，需求正文/OpenAPI/Base URL 跨两列；<768px 单列。
- 状态行使用 `flex-wrap`，长错误文案允许换行，不用固定宽度。
- 点击目标最小 44px；提交/推进期间按钮 disabled 并显示进行中动词。
- 进度使用有序列表语义；状态不只依赖颜色，必须同时显示中文文本。

## 5. 视觉方向

沿用现有安静、工作型控制台视觉：中性表面、一种强调色、语义成功/警告/错误色。遵循 Impeccable 产品界面规范与风格库的“信息优先、克制配色、清晰层级”，不新增插画、渐变、玻璃效果或装饰动效。

## 6. 设计签核标准

六字段能快速扫读；普通用户不会误认为要启动 Temporal；管理入口可达；暗色主题和三视口均无文字截断、横向溢出或状态色失真。
