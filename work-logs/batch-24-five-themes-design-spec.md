# Batch 24 Design Spec — 五套主题设计令牌

> Design Department | 2026-07-20
> 来源: `test-platform-v2/docs/theme-mockup-v3.html`

## 映射策略

Mockup 使用自定义 CSS 变量名（`--bg`, `--surf`, `--p`, `--mu` 等），平台使用 shadcn/ui 标准变量名（`--background`, `--foreground`, `--primary`, `--muted` 等）。需要做语义映射：

| Mockup Var | Platform Var | 说明 |
|-----------|-------------|------|
| `--bg` | `--background` | 页面背景 |
| `--surf` | `--card` / `--popover` | 表面/卡片背景 |
| `--card` | (card interior) | 卡片内部 (平台用 --card) |
| `--sbar` | `--sidebar-background` | 侧栏背景 |
| `--p` | `--primary` | 主色 |
| `--ph` | (hover state) | 主色 hover |
| `--pi` | `--primary-foreground` | 主色上的文字 |
| `--s2` | `--secondary` | 次要色 |
| `--ac` | `--accent` | 强调色 |
| `--ok` | `--chart-2` (green) | 成功绿 |
| `--warn` | `--chart-4` (yellow) | 警告黄 |
| `--err` | `--destructive` | 错误红 |
| `--mu` | `--muted` | 弱化色 |
| `--ink` | `--foreground` | 正文色 |
| `--dim` | `--muted-foreground` | 弱化文字 |
| `--bdr` | `--border` | 边框色 |
| `--bdr2` | `--input` | 输入框边框 |
| `--r` | `--radius` | 圆角 |
| `--sh` | `--shadow-card` | 卡片阴影 |
| `--shh` | `--shadow-card-hover` | 卡片 hover 阴影 |
| `--dur` | `--animation-duration` | 动画时长 |
| `--ease` | (CSS transition) | 缓动函数 |
| `--mono` | (font override) | 等宽字体 |

## Theme 1: Cyberpunk `[data-theme="cyberpunk"]`

### 设计令牌
```
--background: #090b0d           (oklch 0.08 0.005 220) 深黑蓝
--foreground: #d0e0ed           (oklch 0.88 0.015 230)
--card: #11161a                 (oklch 0.13 0.005 220)
--primary: #00e5ff              (oklch 0.72 0.15 205) 霓虹青
--primary-foreground: #090b0d
--secondary: #1c2833            (oklch 0.2 0.01 220)
--secondary-foreground: #d0e0ed
--muted: #1c2833
--muted-foreground: #546e7a     (oklch 0.45 0.02 230)
--accent: #b400ff               (oklch 0.45 0.25 300) 霓虹紫
--accent-foreground: #d0e0ed
--destructive: #ff1744           (oklch 0.57 0.25 20) 霓虹红
--destructive-foreground: #fff
--border: #1c2833
--input: #152028
--ring: #00e5ff
--radius: 0.125rem (2px)
--radius-sm: 0.0625rem (1px)
--radius-lg: 0.25rem (4px)
--sidebar-background: #06090b
--sidebar-foreground: #7a8fa0
--sidebar-primary: #00e5ff
--sidebar-accent: rgba(0,229,255,0.06)
--shadow-card: 0 0 0 1px rgba(0,229,255,0.06)
--shadow-card-hover: 0 0 20px rgba(0,229,255,0.12)
--animation-duration: 120ms
--density: 0.85
--glass-bg: rgba(9,11,13,0.85)
--card-radius: 2px
--neon-glow: rgba(0,229,255,0.45)
```

### 组件差异化
- 卡片: 1px 霓虹边框，顶部 1px 青线渐变，hover 边框变亮
- 侧栏: 最深黑底，active item 左边框 2px 霓虹青发光，dot 指示器
- 按钮: 主按钮霓虹青实色+辉光，hover 辉光增强，active scale(0.97)
- 标签页: 底部 2px 霓虹青下划线，等宽字体
- 弹窗: 纯黑遮罩(0.85)，霓虹青边框，顶部发光渐变线
- Toast: 右上角，霓虹青边框，闪烁 dot
- 进度环: 直角 stroke-linecap:butt，霓虹青发光 drop-shadow
- 进度条: 5px 高，无圆角，青色渐变 fill+白色尾迹
- 骨架屏: 暗色块+绿色字符闪烁(`▌`光标效果)
- 表格: 等宽字体，hover 微青背景，选中行左边框发光
- Badge: 直角，霓虹边框+半透明底

## Theme 2: Apple `[data-theme="apple"]`

### 设计令牌
```
--background: #f5f5f7           (oklch 0.97 0.001 260)
--foreground: #1d1d1f           (oklch 0.18 0.001 260)
--card: #ffffff
--primary: #0071e3              (oklch 0.52 0.18 255) Apple Blue
--primary-foreground: #fff
--secondary: #f5f5f7
--secondary-foreground: #1d1d1f
--muted: #f5f5f7
--muted-foreground: #86868b     (oklch 0.58 0.005 260)
--accent: #f5f5f7
--accent-foreground: #0071e3
--destructive: #ff3b30           (oklch 0.55 0.25 25) Apple Red
--destructive-foreground: #fff
--border: #d2d2d7
--input: #e8e8ed
--ring: #0071e3
--radius: 0.625rem (10px)
--radius-sm: 0.5rem (8px)
--radius-lg: 1rem (16px)
--sidebar-background: rgba(245,245,247,0.78)
--sidebar-foreground: #86868b
--sidebar-primary: #0071e3
--shadow-card: 0 1px 3px rgba(0,0,0,0.04)
--shadow-card-hover: 0 8px 30px rgba(0,0,0,0.08)
--animation-duration: 300ms
--density: 1.15
--glass-bg: rgba(255,255,255,0.55)
--glass-blur: 20px
--card-radius: 16px
```

### 组件差异化
- 卡片: 白底+微妙阴影+细边框，圆角 16px
- 侧栏: 毛玻璃 blur(20px) saturate(180%)，半透明底
- 按钮: pill 形状 999px，微妙阴影，active scale(0.97)
- 标签页: 分段控制器(Segmented Control)，灰底+白色 active pill
- 弹窗: 浅遮罩+blur(4px)，大白圆角 sheet，spring 动画弹入
- Toast: 底部居中，深色背景，spring 动画
- 进度环: 细描边 4px，圆端，灰色 track+蓝色 value
- 进度条: 极细 5px，999px 圆角，蓝色 fill
- 骨架屏: 极淡灰 #f0f0f2，无动画（静态形状）
- 表格: 极简线框，44px 行高，hover 微弱灰底
- Badge: 圆角 pill，柔和色调

## Theme 3: Clay `[data-theme="clay"]`

### 设计令牌
```
--background: #efe9f7           (oklch 0.93 0.03 290)
--foreground: #332f3a           (oklch 0.24 0.02 285)
--card: #faf7fd                 (oklch 0.97 0.01 290)
--primary: #7457cc              (oklch 0.46 0.15 285) 黏土紫
--primary-foreground: #fff
--secondary: #f0ebf8
--secondary-foreground: #332f3a
--muted: #f0ebf8
--muted-foreground: #8b7fa8     (oklch 0.55 0.03 285)
--accent: #a78bfa               (oklch 0.65 0.12 285)
--accent-foreground: #332f3a
--destructive: #f87171           (oklch 0.62 0.2 20) 柔和红
--destructive-foreground: #fff
--border: transparent
--input: rgba(116,87,204,0.08)
--ring: #7457cc
--radius: 0.875rem (14px)
--radius-sm: 0.625rem (10px)
--radius-lg: 1.25rem (20px)
--sidebar-background: rgba(245,241,250,0.85)
--sidebar-foreground: #8b7fa8
--sidebar-primary: #7457cc
--shadow-card: 0 8px 16px rgba(83,68,110,0.08), inset 0 1px 0 rgba(255,255,255,0.7)
--shadow-card-hover: 0 14px 28px rgba(83,68,110,0.14), inset 0 1px 0 rgba(255,255,255,0.8)
--animation-duration: 280ms
--density: 1.05
```

### 组件差异化
- 卡片: 双层阴影(外阴影+内高光)=3D膨胀感，hover 浮起，active 内陷 scale(0.98)
- 侧栏: 淡紫背景，active item 膨胀 pill+阴影
- 按钮: 完全 pill 999px，3D膨胀外观，active scale(0.95)+内阴影
- 标签页: 软 pill 切换，active tab 膨胀 scale(1.04)+紫底白字
- 弹窗: 暖色遮罩+blur(3px)，弹性弹出 cubic-bezier(0.34,1.56,0.64,1)
- Toast: 底部居中，弹性弹入，双层阴影
- 进度环: 粗描边 7px，圆端，淡紫 track+紫 value+drop-shadow
- 进度条: 高 10px，内阴影+紫渐变 fill+外发光
- 骨架屏: 柔和圆角+呼吸动画(scale 0.97→1)
- 表格: 独立圆角行+行间距 4px，hover 整行膨胀 scale(1.01)
- Badge: 大圆角 pill，柔和色调

## Theme 4: xLab `[data-theme="xlab"]`

### 设计令牌
```
--background: #07090a           (oklch 0.06 0.005 220)
--foreground: #e2e8f0           (oklch 0.9 0.01 240)
--card: #15191c                 (oklch 0.13 0.005 220)
--primary: #4fe4ff              (oklch 0.75 0.12 210) 电光青
--primary-foreground: #07090a
--secondary: #1a242d
--secondary-foreground: #e2e8f0
--muted: #1a242d
--muted-foreground: #64748b     (oklch 0.5 0.01 240)
--accent: #6366f1               (oklch 0.5 0.22 280) 靛蓝
--accent-foreground: #e2e8f0
--destructive: #f87171
--destructive-foreground: #fff
--border: #1e293b
--input: #1a2430
--ring: #4fe4ff
--radius: 0.375rem (6px)
--radius-sm: 0.25rem (4px)
--radius-lg: 0.625rem (10px)
--sidebar-background: #080a0c
--sidebar-foreground: #94a3b8
--sidebar-primary: #4fe4ff
--shadow-card: 0 1px 2px rgba(0,0,0,0.3)
--shadow-card-hover: 0 4px 16px rgba(79,228,255,0.08)
--animation-duration: 180ms
--density: 0.9
```

### 组件差异化
- 卡片: 深色底+暗边框，hover 青色微光边框+辉光
- 侧栏: 最深黑底，active item 左侧 2px 电光青线+发光，dot 指示器
- 按钮: 主按钮电光青实色+深文字，hover 辉光，active scale(0.97)
- 标签页: 代码编辑器风格底部 2px 下划线
- 弹窗: 纯黑遮罩(0.78)，顶部青线渐变，模糊渐入
- Toast: 底部居中，暗色+青边框
- 进度环: 细描边 3px，圆端，电光青+微光 drop-shadow
- 进度条: 细线 4px，无圆角，电光青+扫描线动画
- 骨架屏: 暗色块+红外扫描线动画(亮条从左到右)
- 表格: 等宽数字列 font-variant-numeric:tabular-nums，hover 微光
- Badge: 锐利直角，细边框+暗底

## Theme 5: Liquid Glass `[data-theme="liquid-glass"]`

### 设计令牌
```
--background: #0a0a1a           (oklch 0.08 0.03 275)
--foreground: #e8e8f8           (oklch 0.9 0.01 275)
--card: rgba(24,24,60,0.42)
--primary: #7c5ce7              (oklch 0.55 0.18 280) 虹彩紫
--primary-foreground: #fff
--secondary: rgba(30,30,70,0.5)
--secondary-foreground: #e8e8f8
--muted: rgba(30,30,70,0.5)
--muted-foreground: #9090b8     (oklch 0.62 0.02 280)
--accent: #4ef0e8               (oklch 0.78 0.1 195) 电光青
--accent-foreground: #0a0a1a
--destructive: #f06080
--destructive-foreground: #fff
--border: rgba(255,255,255,0.09)
--input: rgba(255,255,255,0.05)
--ring: #7c5ce7
--radius: 0.75rem (12px)
--radius-sm: 0.5rem (8px)
--radius-lg: 1.125rem (18px)
--sidebar-background: rgba(7,7,26,0.75)
--sidebar-foreground: #9090b8
--sidebar-primary: #7c5ce7
--shadow-card: 0 8px 32px rgba(0,0,0,0.28), inset 0 1px 0 rgba(255,255,255,0.06)
--shadow-card-hover: 0 14px 44px rgba(0,0,0,0.38), inset 0 1px 0 rgba(255,255,255,0.11), 0 0 36px rgba(124,92,231,0.1)
--animation-duration: 350ms
--density: 1
--glass-bg: rgba(18,18,48,0.55)
--glass-border: rgba(255,255,255,0.09)
--glass-blur: 28px
```

### 组件差异化
- 背景: 🔥 核心特征 — 4 层径向渐变 morphing 背景(18s 周期 opacity 振荡)
- 卡片: 多层毛玻璃 blur(14px)，玻璃高光线(::after 1px 白渐变)，hover 浮起+辉光
- 侧栏: 最深玻璃 blur(28px) saturate(150%)，active item 紫底毛玻璃+辉光
- 顶栏: 玻璃 blur(20px)
- 按钮: 主按钮紫->淡紫渐变+玻璃高光，danger 磨砂玫瑰玻璃，outline 半透明玻璃
- 标签页: 玻璃 pill 栏，active tab 紫底毛玻璃+白色内高光
- 弹窗: 深层玻璃 blur(30px)+暗色遮罩 blur(12px)，顶部玻璃棱线，缩放+模糊渐入
- Toast: 底部居中玻璃 pill，紫晕 glow，弹性滑入
- 进度环: 紫光 drop-shadow，圆端
- 进度条: 玻璃管 track+紫->青渐变 fill+辉光
- 骨架屏: 暗玻璃块+虹彩 shimmer(透明→白→透明斜扫)
- 表格: 玻璃容器，选中行左侧 3px 紫线发光
- Badge: 微型磨砂玻璃 pill，各自色调玻璃边框
