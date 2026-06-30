# 音视频项目测试 - 快速启动指南

> **用途**: 直播音视频质量测试的完整工程，包含环境搭建、测试素材、分析脚本、自动化流程。
> **适用场景**: 直播延迟测试、弱网测试、连麦测试、音视频同步测试、帧率流畅度测试、负载压力测试。
> **规范参考**: 所有测试流程依据 [音视频测试模块文档](../音视频测试/) 中的10个模块规范。

---

## 目录结构

```
音视频项目测试/
├── README.md                    ← 本文件（快速启动指南）
├── scripts/                     ← 可执行脚本
│   ├── opencv.py               # 视频帧时间戳OCR识别
│   ├── analysis.py             # 延迟数据分析+图表生成
│   ├── frame_analysis.py       # 帧率流畅度定量分析
│   ├── generate_test_video.py  # Python生成高精度测试视频
│   ├── collect_results.py      # 批量汇总测试结果
│   ├── generate_test_videos.bat # FFmpeg快速生成测试视频（推荐新手）
│   ├── run_test.bat            # 一键测试（单场景）
│   └── batch_test.bat          # 批量测试（多场景依次执行）
├── materials/                   ← 测试素材存放
├── results/                     ← 测试结果输出
└── templates/                   ← 结果记录模板
    ├── 延迟测试结果模板.csv
    ├── 弱网测试结果模板.csv
    └── 流畅度测试结果模板.csv
```

---

## 第一次使用（跟着做，约1-2天）

### 第1步：安装环境

按照 [01-环境安装指南](../音视频测试/01-环境安装指南.md) 逐项安装：

| 工具 | 验证命令 | 状态 |
|------|----------|------|
| Python 3.7+ | `python --version` | ☐ |
| OpenCV | `python -c "import cv2; print(cv2.__version__)"` | ☐ |
| Tesseract-OCR | `tesseract -v` | ☐ |
| FFmpeg | `ffmpeg -version` | ☐ |
| 依赖库 | `pip list` 确认有 matplotlib, pandas, numpy | ☐ |

### 第2步：安装Python依赖

```cmd
pip install opencv-python opencv-contrib-python
pip install pytesseract matplotlib pandas numpy imutils
```

### 第3步：生成测试素材

**方案A（推荐新手）**：双击运行 `scripts\generate_test_videos.bat`

**方案B（高精度）**：
```cmd
python scripts\generate_test_video.py
```

生成的文件在 `materials\` 下：
- `time_delay_test.mp4` — 延迟测试用（带时间戳）
- `fluency_test_60fps.mp4` — 流畅度测试用（跑马灯）
- `av_sync_test.mp4` — 音视频同步测试用

### 第4步：执行首次延迟测试

1. 打开OBS，配置媒体源为 `materials\time_delay_test.mp4`
2. 开始推流
3. 用Bandicam录制观众端画面（60秒）
4. **双击 `scripts\run_test.bat`**
5. 输入场景名（如 `first_test`）
6. 将录制的mp4文件拖入cmd窗口 → 回车
7. 等待自动分析完成，弹出结果文件夹

### 第5步：查看结果

打开自动弹出的结果文件夹，查看：
- `recording_chart.png` — 4张分析图表
- `recording_results.txt` — 统计数据

---

## 日常测试快速命令

```cmd
# 单次测试
cd F:\CamelTv\tests\音视频项目测试\scripts
run_test.bat

# 批量测试（3个网络场景）
batch_test.bat

# 仅生成测试视频
generate_test_videos.bat

# 手动分析已有录制文件
python opencv.py "你的录制文件.mp4"
python analysis.py "你的录制文件.log"

# 汇总所有历史测试结果
python collect_results.py
```

---

## 各测试模块对照表

| 测试内容 | 参考规范 | 使用脚本 | 预计耗时 |
|----------|----------|----------|----------|
| 视频延迟 | [03-视频延迟测试](../音视频测试/03-视频延迟测试.md) | `run_test.bat` | 15分钟/场景 |
| 弱网模拟 | [04-弱网模拟测试](../音视频测试/04-弱网模拟测试.md) | `run_test.bat` + NEWT | 20分钟/配置 |
| 连麦延迟 | [05-连麦延迟测试](../音视频测试/05-连麦延迟测试.md) | `opencv.py` + `analysis.py` | 30分钟/场景 |
| 音视频同步 | [06-音视频同步测试](../音视频测试/06-音视频同步测试.md) | Audacity + `av_sync_test.mp4` | 20分钟 |
| 帧率流畅度 | [07-帧率流畅度测试](../音视频测试/07-帧率流畅度测试.md) | `frame_analysis.py` | 15分钟 |
| 负载压力 | [08-负载压力测试](../音视频测试/08-负载压力测试.md) | `run_test.bat` × N台设备 | 1小时 |
| 结果汇总 | [10-结果分析](../音视频测试/10-结果分析与问题排查.md) | `collect_results.py` | 10分钟 |

---

## 常见问题速查

| 问题 | 解决方法 |
|------|----------|
| `python` 命令找不到 | Python未安装或未加入PATH，重新运行Python安装程序并勾选"Add to PATH" |
| `import cv2` 失败 | OpenCV安装有问题，运行 `pip install opencv-python` |
| OCR识别率为0 | 调整 `opencv.py` 中ROI坐标参数，匹配实际时间戳位置 |
| 图表中文乱码 | 系统缺少中文字体，不影响数据，可在Excel中重新制图 |
| FFmpeg命令找不到 | FFmpeg未安装或bin目录未加入PATH |
| bat脚本双击闪退 | 右键→编辑查看内容，或在cmd中手动运行查看错误 |

---

## 测试通过标准（参考）

| 指标 | 标准 |
|------|------|
| WiFi正常延迟 | < 2000ms |
| 移动网络延迟 | < 5000ms |
| 音画同步偏差 | < 200ms |
| 流畅帧占比 | ≥ 95% |
| 弱网轻度 | 不影响观看 |
| 弱网重度 | 不断流或能自动恢复 |
| 连麦成功率 | ≥ 90% |

---

**项目创建日期**: 2026-05-25
