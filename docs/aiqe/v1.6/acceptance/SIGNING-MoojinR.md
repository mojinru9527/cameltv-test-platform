# 70 条验收签署指南（MoojinR）

## 清单在哪里
- 人工清单：`docs/aiqe/v1.6/acceptance/REVIEW-CHECKLIST-MoojinR.md`
- 机器清单：`docs/aiqe/v1.6/acceptance/MoojinR-review-manifest.json`
- 正式记录目录：`docs/aiqe/v1.6/acceptance/records/`（签署后生成 JSON）

## 怎么签
1. MoojinR 逐条阅读清单中的证据/测试链接；
2. 确认后运行（每条一次）：

```powershell
python scripts/aiqe/record_acceptance.py --requirement V16-001-R1 `
  --reviewer MoojinR --reviewed-at 2026-11-27 `
  --artifact "docs/aiqe/v1.6/acceptance/records/V16-001-R1.json" `
  --decision REVIEWED
```

3. 全部 70 条完成后，在仓库根运行：
```powershell
python scripts/aiqe/check_traceability.py --strict-warnings --check-baseline
python scripts/aiqe/release_verdict.py --write
```
`accepted` 应为 70，Gate G acceptance 才会变成 REVIEWED。

> 不能由实现者代签；record 必须由 reviewer 本人确认后生成。
