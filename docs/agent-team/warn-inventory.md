# WARN 清单长期维护（C80-1）

> 事实源：`scripts/git/scan-common-bugs.ps1`（HARD/WARN 扫描）。本文件为 WARN 存量基线、分类与维护节奏。

## 1. 基线（2026-08-04，Batch 80 合入后）

| 分类 | 数量 | 判定 | 豁免理由 |
|------|-----:|------|---------|
| 运维脚本 print | 179 | WARN（复核） | `backend/scripts/*` 为 CLI 运维工具，print 是合法输出；不得引入到 app 代码 |
| HTTP 404 断言 | 41 | WARN（复核） | 隔离/权限/存在性守卫的 HTTP 404 是正确契约（不泄露存在性）；业务查不到应 200+code |
| seed 一次性凭据 | 5 | WARN（复核） | `seed.py` 生成凭据一次性显示由 `test_seed_credentials.py` 强制 |
| 注释吞异常 | 5 | WARN（复核） | 带注释的 except-pass 为有意兜底（邮件非必需、job 不存在等） |
| **合计** | **230** | | |

## 2. 长期维护规则（C80-1）

1. **节奏**：每周或每 10 个批次（先到者）运行一次审计：
   ```powershell
   pwsh scripts/git/scan-common-bugs.ps1 -RepositoryPath <root> -BaselinePath docs/agent-team/warn-baseline.json
   ```
2. **新增归因**：出现新 WARN 类别或新文件命中时，必须归因——新代码引入的要在当批处理或登记豁免；存量类别的数量变化记录在本文件"趋势"表。
3. **趋势记录**：每次审计把 `{日期, 批次, warn_total, 新增类别, 清除项}` 追加到 §4。
4. **门禁**：HARD 必须 0；新 WARN 类别不允许在无人复核的情况下合入（C76-2 延续）。
5. **基线刷新**：仅当新增类别经 Leader 复核并接受后，才重新生成基线：
   ```powershell
   pwsh scripts/git/scan-common-bugs.ps1 -RepositoryPath <root> -WriteBaseline docs/agent-team/warn-baseline.json
   ```

## 3. 基线 JSON 结构

```json
{
  "generated_at": "ISO8601",
  "hard_count": 0,
  "warn_count": 230,
  "warn_categories": { "规则名": 数量 },
  "warn_files": { "相对路径": 数量 },
  "hard_categories": {}
}
```

## 4. 趋势

| 日期 | 批次 | WARN 总数 | 新增类别 | 清除项 | 备注 |
|------|------|----------:|----------|--------|------|
| 2026-08-04 | 80 | 230 | — | cameltv-dev-key（1） | 基线建立 |
