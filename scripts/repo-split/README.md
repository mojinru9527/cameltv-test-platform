# 仓库边界校验（Repo Boundary Validator）

## 用途

`repo-boundaries.json` 是 CamelTv 三仓分离（前端 / 后端 / 运维平台）的**路径归属事实源**
（Batch 64 架构基线，见 [ADR-0016](../../docs/adr/0016-three-repository-separation.md)）。
校验器确保：

- 仓库内每一个**已跟踪**路径都有明确归属（不允许出现「无主路径」）；
- 归属采用**最长前缀优先**：更具体的路径可以覆盖父目录归属；
- 跨仓库不允许同一路径被精确声明两次；
- schema 或路径引用非法时立即失败（退出码 2）。

## 使用

```powershell
# 校验当前仓库（默认自动定位仓库根）
python scripts/repo-split/validate_repo_boundaries.py --check

# 运行内置自测（7 个场景，不依赖真实仓库）
python scripts/repo-split/validate_repo_boundaries.py --selftest

# 显式指定仓库根与清单
python scripts/repo-split/validate_repo_boundaries.py --check `
  --repo-root F:\CamelTv-worktrees\codex-batch-64-arch-baseline `
  --manifest repo-boundaries.json
```

退出码：`0` = 通过；`1` = 存在归属违规；`2` = 清单本身非法。

## 集成建议

- 每个**拆仓批次**合入前必须运行 `--check`，并把退出码写入 QA 报告。
- 新增顶层目录/文件时，先在此清单声明归属，再提交代码。
- CI（`ai-delivery-policy.yml` 或拆仓专用 workflow）可把它作为 preflight 步骤，失败即阻断。

## 维护

- 修改归属时同步更新 `docs/architecture/batch-64-architecture-analysis.md` §5（目标仓库职责）。
- 删除死资产（如 `pective pipeline ...` 两个误提交文件）走独立审计批次，删除后同步移除清单条目。
