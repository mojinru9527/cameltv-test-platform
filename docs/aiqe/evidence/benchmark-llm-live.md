# AIQE Benchmark 真实 LLM 执行证据

- 时间：2026-11-19（Asia/Shanghai）
- 运行环境：本地现有环境 `http://127.0.0.1:7778` + SQLite（project 1）
- Provider：DeepSeek OpenAI-compatible `https://api.deepseek.com/v1`，模型 `deepseek-flash`
- 数据集：`ad66041d-3a3b-4eef-b2fe-d75e64cfa0b2`（30 样本，label_space=UI_OVERLAY|NETWORK，FROZEN，gate_eligible=true）
- BenchmarkRun：`08eed69e-6944-47c4-a491-e44d193c441f`，agent `A6`，状态 `COMPLETED` / `PASS_GATE`
- 指标：Precision **1.0**、Recall **1.0**、F1 **1.0**，样本 30，Unknown rate 0.0
- token：{"input": 5475, "output": 3036}

## 说明

- 30 个样本逐条真实调用 LLM，labels 由模型输出、后端与 golden labels 比对后计算指标；
- 未使用任何调用方自报指标；结果 JSON 含逐样本预测与输出 hash；
- 上述 Provider 仅写入本地证据库（加密存储），不包含在代码或提交中。

完整结果：`benchmark-llm-live.json`。
