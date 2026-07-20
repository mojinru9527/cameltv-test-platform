# 测试平台 v3 四套新主题设计方案

> 设计灵感来源: [namethatui.com](https://namethatui.com/?platform=web) + [learnui.qiaomu.ai](https://learnui.qiaomu.ai/?platform=web#dictionary)
> 设计日期: 2026-07-20
> 目标: 在现有 5 套主题基础上新增 4 套完全不同的视觉风格

---

## 现有主题回顾 (v2 已实现)

现有 5 个主题在 `themes.ts` 中有各自的营销标签，但 CSS 实现与标签之间存在差距：

| # | 逻辑 ID | 标签 | 声称灵感 | CSS Preset | CSS 实际效果 | 差距 |
|---|---------|------|---------|-----------|-------------|------|
| 1 | `crystal` | 晶穹 | Apple × Liquid Glass | `blue` | 标准企业蓝 | ❌ 非 Apple 极简、非真液态玻璃 |
| 2 | `xlab` | 黑域 | xAI × 轻赛博 | `dark-minimal` | 建筑单色暗黑 | ❌ 无霓虹、无赛博、无终端感 |
| 3 | `column` | 列阵 | ClickHouse 工业数据 | `warm` | 温暖琥珀金 | ❌ 非数据密集、非工业风、暖色系 |
| 4 | `clay` | 软体 | 企业黏土拟态 | `nature` | 自然绿色清新 | ❌ 无3D内阴影、非粉彩、是绿色系 |
| 5 | `liquid` | 液境 | 全景液态玻璃 | `liquid` | 蓝紫毛玻璃 | ✅ 液态玻璃实现正确 |

**结论**: 前 4 个主题的标签与实际 CSS 存在显著差距。v3 新主题需要真正实现这些设计语言。

---

## 四套新主题设计

### 主题 6: `cyberpunk` — 赛博朋克终端

**灵感来源**: Cyberpunk (learnui) + ClickHouse 数据密集风格 + Progress Ring/Text Scramble (namethatui)

**核心定位**: 暗黑终端美学 × 霓虹数据工作台。适合夜间深度工作的测试工程师。

#### 设计令牌 (Design Tokens)

```
色彩体系:
  bg:              #090b0d (深黑蓝)
  surface:         #11161a (微升表面)
  card:            #151a1f
  primary:         #00e5ff (霓虹青 cyan)
  secondary:       #b400ff (霓虹紫)
  accent:          #ff2d95 (霓虹粉)
  success:         #00ff88 (霓虹绿)
  warning:         #ffd600 (霓虹黄)
  danger:          #ff1744 (霓虹红)
  muted:           #546e7a
  border:          #1c2833
  ink:             #e0f0f8

字体:
  UI:              'Geist Variable', sans-serif
  Data/Code:       'JetBrains Mono', monospace (数据表格 + 日志 + 代码区)

形状:
  radius:          2px (几乎直角)
  radius-sm:       1px
  radius-lg:       4px

阴影 → 发光:
  shadow-card:     0 0 0 1px rgba(0,229,255,0.08)
  shadow-hover:    0 0 20px rgba(0,229,255,0.15)
  neon-glow:       0 0 8px var(--primary), 0 0 20px var(--primary)
  neon-strong:     0 0 12px var(--primary), 0 0 40px var(--primary), 0 0 60px var(--primary)

动效:
  animation-duration: 120ms (快速、精确)
  easing:           steps(8, end) (打字机风格过渡)
```

#### 组件差异化

| 组件 | Cyberpunk 行为 |
|------|---------------|
| **Progress Ring** | 霓虹青描边 + 外发光，`stroke-linecap: butt`(直角)，数值 Text Scramble 动画 |
| **Progress Bar** | 霓虹分段 + 扫描线动画，带发光尾迹 |
| **Skeleton** | 终端绿色字符闪烁 (`▌` 光标效果) 替代传统 shimmer |
| **Tabs** | 下划线 2px 霓虹青发光，active tab 文字变霓虹色 |
| **Snackbar** | 右上角终端通知风格，等宽字体，霓虹边框 |
| **表格** | ClickHouse 风格: 紧凑行高(32px)、斑马纹微弱、hover 霓虹左边框、等宽数字 |
| **侧栏** | 最深黑底 `#06090b`，active item 霓虹左边框发光 |
| **按钮** | 默认透明+霓虹边框，hover 发光脉冲动画 |
| **Backdrop** | 纯黑 + 扫描线纹理，无模糊 |
| **日志面板** | CRT 绿色终端风格 `#00ff88` on `#0a0f0a` |

#### 特殊效果

1. **Text Scramble (Decode Effect)**: 进度数字/百分比变化时触发字符乱码→解码动画
2. **Scanline Overlay**: 全局 2px 间隔的半透明扫描线 (可关闭)
3. **Neon Pulse**: 主按钮和进度环持续微弱的霓虹呼吸动画
4. **Terminal Cursor**: 日志面板末尾闪烁的光标块

---

### 主题 7: `apple` — Apple 极简

**灵感来源**: Apple (learnui) + Snackbar/Tabs (learnui) + Progress Ring (namethatui)

**核心定位**: 极致克制、大留白、SF 式字体排版。适合日间管理和报告审阅。

#### 设计令牌

```
色彩体系:
  bg:              #f5f5f7 (Apple 经典浅灰)
  surface:         #ffffff
  card:            #ffffff
  primary:         #0071e3 (Apple Blue)
  secondary:       #f5f5f7
  accent:          #86868b
  success:         #34c759 (Apple Green)
  warning:         #ff9f0a (Apple Orange)
  danger:          #ff3b30 (Apple Red)
  muted:           #86868b
  border:          #d2d2d7 (几乎不可见)
  ink:             #1d1d1f

字体:
  UI:              'Geist Variable', -apple-system, BlinkMacSystemFont, sans-serif
  标题:             font-weight 590 (Apple 特有的半粗体)

形状:
  radius:          10px (Apple 标准圆角)
  radius-sm:       8px
  radius-lg:       16px

阴影:
  shadow-card:     0 1px 3px rgba(0,0,0,0.04)
  shadow-hover:    0 8px 30px rgba(0,0,0,0.08)
  特点:             极淡、多层次、几乎不可见

动效:
  animation-duration: 300ms (从容、优雅)
  easing:           cubic-bezier(0.25, 0.1, 0.25, 1) (标准 iOS 缓动)
```

#### 组件差异化

| 组件 | Apple 行为 |
|------|-----------|
| **Progress Ring** | Apple Watch 风格: 细描边(3px)、圆端、灰色 track + 蓝色 value |
| **Progress Bar** | 极细 4px、圆角、微妙动画、无标签 |
| **Skeleton** | 极淡灰色块 `#f0f0f2`、无 shimmer 动画（仅静态形状） |
| **Tabs** | 分段控制器 (Segmented Control): 灰底 + 白色 active pill |
| **Snackbar** | 底部居中弹出、大圆角、SF 风格细字体 |
| **表格** | 极简线框、间距宽松(44px 行高)、hover 微弱灰底 |
| **侧栏** | 半透明毛玻璃 (`backdrop-filter: blur(20px) saturate(180%)`) |
| **按钮** | 圆角 pill、微妙阴影、无边框、SF 字体 |
| **Backdrop** | 轻微模糊 + 变暗 (`blur(4px) + rgba(0,0,0,0.15)`) |
| **对话框** | 大圆角 sheet、顶部滑入动画、宽留白 |

#### 特殊效果

1. **Frosted Glass Sidebar**: 侧栏半透明毛玻璃，背景色渗透
2. **Spring Animations**: 使用 `spring()` 缓动替代标准 ease
3. **Content-first**: 极少的边框和分割线，依靠留白区分层级
4. **SF Symbols 风格图标**: 统一 1.5px 描边宽度
5. **Type Scale**: 大标题 28px → 正文 13px 的明显层级跳跃

---

### 主题 8: `clay` — 黏土拟态

**灵感来源**: Claymorphism (learnui) + Skeleton/Spinner (namethatui)

**核心定位**: 柔和3D、粉彩配色、膨胀触感。适合演示和对外展示场景。

#### 设计令牌

```
色彩体系:
  bg:              #efe9f7 (淡紫灰)
  surface:         #faf7fd (接近白)
  card:            #faf7fd
  primary:         #7457cc (黏土紫)
  secondary:       #f0ebf8
  accent:          #a78bfa (浅紫)
  success:         #4ade80 (柔和绿)
  warning:         #fb923c (暖橘)
  danger:          #f87171 (柔和红)
  muted:           #8b7fa8
  border:          transparent (无可见边框)
  ink:             #332f3a (暖深紫黑)

字体:
  UI:              'Geist Variable', 'PingFang SC', rounded sans-serif
  特点:             略微增加 letter-spacing (0.01em)

形状:
  radius:          14px (大圆角 pill)
  radius-sm:       10px
  radius-lg:       20px
  buttons:         9999px (完全 pill)

阴影 (黏土核心):
  shadow-card:     0 8px 16px rgba(83,68,110,0.08), inset 0 1px 0 rgba(255,255,255,0.7)
  shadow-hover:    0 12px 24px rgba(83,68,110,0.14), inset 0 1px 0 rgba(255,255,255,0.8)
  shadow-pressed:  inset 0 3px 8px rgba(83,68,110,0.12)
  特点:             [3m外阴影 + 内高光 = 3D 膨胀感[0m

动效:
  animation-duration: 280ms
  easing:           cubic-bezier(0.34, 1.56, 0.64, 1) (弹性缓出)
```

#### 组件差异化

| 组件 | Clay 行为 |
|------|----------|
| **Progress Ring** | 粗描边(10px)、圆端、软阴影 track + 渐变 value |
| **Progress Bar** | 高 10px、大圆角、内阴影、膨胀感 |
| **Skeleton** | 柔和圆角块、微妙的呼吸动画（缩放 0.97→1）而非 shimmer |
| **Tabs** | 软 pill 切换、active tab 膨胀突出 |
| **Snackbar** | 大圆角、软阴影、弹性弹出动画 |
| **表格** | 独立圆角行、行间距 4px、hover 整行膨胀 |
| **侧栏** | 淡紫色背景、软阴影分割、菜单项 pill 形状 |
| **按钮** | 3D 膨胀外观、按下内陷效果 (`scale(0.97)`) |
| **Backdrop** | 暖色调暗色 + 轻微模糊 |
| **Badge** | 大圆角 pill、柔和色调、粗字体 |

#### 特殊效果

1. **Press-in 反馈**: 所有可点击元素按下时内缩 (`transform: scale(0.97)` + `inset shadow`)
2. **Bouncy Spring**: 弹窗/抽屉入场带弹性动画 (`cubic-bezier(0.34, 1.56, 0.64, 1)`)
3. **Inner Glow**: 卡片顶部 1px 白色内高光模拟光线反射
4. **Soft Gradients**: 主色调渐变柔和模糊，无锐利过渡
5. **Chunky Scrollbar**: 粗圆角自定义滚动条

---

### 主题 9: `xlab` — AI 实验室

**灵感来源**: xAI + 前沿 AI 实验室 (learnui) + Text Scramble/Easing (namethatui)

**核心定位**: 深色科技感、精准排版、AI 驱动感。适合 AI 功能展示和 Agent 工作台。

#### 设计令牌

```
色彩体系:
  bg:              #07090a (极致深黑)
  surface:         #101315 (微蓝黑)
  card:            #15191c
  primary:         #4fe4ff (电光青)
  secondary:       #1a242d
  accent:          #6366f1 (靛蓝)
  success:         #34d399 (翡翠绿)
  warning:         #fbbf24 (琥珀)
  danger:          #f87171 (柔和红)
  muted:           #64748b
  border:          #1e293b
  ink:             #e2e8f0

字体:
  UI:              'Geist Variable', system-ui, sans-serif
  Data/Code:       'JetBrains Mono', monospace
  特点:             标题 letter-spacing: -0.02em, 代码 font-feature-settings: "ss02"

形状:
  radius:          6px (科技感中等圆角)
  radius-sm:       4px
  radius-lg:       10px

阴影 → 微光:
  shadow-card:     0 1px 2px rgba(0,0,0,0.3)
  shadow-hover:    0 4px 16px rgba(79,228,255,0.08)
  glow-subtle:     0 0 12px rgba(79,228,255,0.12)

动效:
  animation-duration: 180ms
  easing:           cubic-bezier(0.4, 0, 0.2, 1) (Material 标准)
  special:          Text Scramble on data refresh
```

#### 组件差异化

| 组件 | xLab 行为 |
|------|----------|
| **Progress Ring** | 细线 3px、电光青、带微弱发光、Text Scramble 数值动画 |
| **Progress Bar** | 细线 4px、无圆角、微妙发光、电感扫描线 |
| **Skeleton** | 极暗灰色块 + 红外线扫描 shimmer（一条亮线从左到右） |
| **Tabs** | 代码编辑器风格下划线、等宽 tab 标题、active 电光青 |
| **Snackbar** | 底部居中、暗色、电光青边框、Text Scramble 文字变化 |
| **表格** | 科技感紧凑、数据列等宽字体、hover 微光边框 |
| **侧栏** | 深黑底、active 电光青细线指示器、图标微光 |
| **按钮** | 主按钮电光青实色+深色文字、次按钮透明微光边框 |
| **Backdrop** | 纯黑 `rgba(0,0,0,0.8)` + 无模糊（精确遮罩） |
| **对话框** | 暗色玻璃效果、电光青顶部细线、优雅滑入 |
| **代码/日志** | 深黑底 `#050708`、电光青关键字高亮、等宽字体 |

#### 特殊效果

1. **Text Scramble**: 数据更新时文字经历乱码→解码动画 (`Text Scramble / Decode Effect`)
2. **IR Scanner**: Skeleton 加载使用红外扫描线效果
3. **Subtle Glow**: 关键元素微弱的电光青外发光（非霓虹，更克制）
4. **Precision Typography**: 表格数字 `font-variant-numeric: tabular-nums`，代码区启用字体 feature
5. **Agent Pulse**: Agent 工作台区域有微弱的电光青呼吸指示器

---

## 四套主题对比矩阵

| 维度 | Cyberpunk | Apple | Clay | xLab |
|------|-----------|-------|------|------|
| **明暗** | 纯暗 | 纯亮 | 亮 (可暗) | 纯暗 |
| **色温** | 冷霓虹 | 中性 | 暖粉紫 | 冷科技 |
| **圆角** | 2px 锐利 | 10px 圆润 | 14px 膨胀 | 6px 精确 |
| **密度** | 0.85 紧凑 | 1.15 宽敞 | 1.05 舒适 | 0.9 紧凑 |
| **动画速度** | 120ms 快 | 300ms 慢 | 280ms 弹性 | 180ms 标准 |
| **边框** | 霓虹发光 | 几乎无 | 无 (用阴影) | 细线 |
| **阴影** | 发光 GLOW | 微妙阴影 | 3D 双层 | 微光 |
| **字体** | UI+等宽 | UI only | UI only | UI+等宽 |
| **玻璃** | 无 | 侧栏毛玻璃 | 无 | 对话框玻璃 |
| **特殊效果** | 扫描线+霓虹脉冲 | 弹簧动画 | 按下内陷+弹性 | Text Scramble |
| **适用场景** | 夜间深度工作 | 日间报告管理 | 演示/对外展示 | AI/Agent 工作台 |

---

## 与现有 5 个主题的 9 宫格定位

```
         亮色 ←→ 暗色
          ↑
   Apple  │  Cyberpunk
   Clay   │  xLab
   Warm   │  Dark-Minimal
   Nature │  Blue (有暗色变体)
   Blue   │  Liquid (有暗色变体)
          ↓
圆润 ←———————————→ 锐利
   Clay    Apple   xLab   Cyberpunk
   Warm    Liquid  Blue   Dark-Minimal
   Nature
```

---

## 新增组件需求

对比两个网站收录的组件，测试平台目前**缺失但需要新增**的组件：

### 高优先级 (P0)

| 组件 | 来源 | 说明 | 新主题中的角色 |
|------|------|------|--------------|
| **Progress Ring** | namethatui | 环形进度指示器 (SVG circle + dasharray) | 4个新主题全部需要 |
| **Text Scramble** | namethatui | 文字乱码解码动画 | Cyberpunk + xLab 核心效果 |
| **Snackbar 增强** | learnui | 已有 Sonner，需增强主题适配 | Apple + Clay 需要各自的 Snackbar 风格 |

### 中优先级 (P1)

| 组件 | 来源 | 说明 |
|------|------|------|
| **Easing Visualizer** | namethatui | 缓动函数可视化选择器 (开发工具) |
| **Backdrop 系统** | namethatui | 统一的遮罩层管理 (不同主题不同模糊/暗度) |
| **Skeleton 增强** | namethatui | 不同主题不同 Skeleton 风格 (shimmer/static/pulse/IR scan) |

### 低优先级 (P2)

| 组件 | 来源 | 说明 |
|------|------|------|
| **Spinner 集合** | namethatui | 多风格旋转器 (ring/dots/pulse/terminal-cursor) |

### 无需新增 (已覆盖)

| 组件 | 现有实现 |
|------|---------|
| Tabs | ✅ Radix Tabs + 主题级 `::after` 伪元素差异化 |
| Progress Bar | ✅ Radix Progress + 主题级 track/indicator |
| Skeleton | ✅ 已有组件 + 主题级 shimmer 差异化 |
| Snackbar | ✅ Sonner + 主题级 `[data-sonner-toaster]` 覆盖 |
| Spinner | ✅ 可用 Lucide `Loader2` + animate-spin |

---

## 实施优先级建议

1. **Phase 1** (MVP): 先做 `cyberpunk` + `apple` — 暗/亮两端代表
2. **Phase 2**: 补充 `clay` + `xlab` — 特殊场景主题
3. **Phase 3**: 新增 Progress Ring 组件 + Text Scramble hook
4. **Phase 4**: 增强 Backdrop/Skeleton/Spinner 主题差异化

---

## 参考资料

- [namethatui.com](https://namethatui.com/?platform=web) — 交互组件对比
- [learnui.qiaomu.ai](https://learnui.qiaomu.ai/?platform=web#dictionary) — 组件词典 + 设计风格
- 现有主题系统: [globals.css](../frontend/src/globals.css)
- Theme Lab 原型: [theme-lab.css](../frontend/src/theme-lab/theme-lab.css)
