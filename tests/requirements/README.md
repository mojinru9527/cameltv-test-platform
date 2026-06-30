# 需求分析

## 目录

```
requirements/
├── documents/               # 需求规格说明书（PRD/FRD）
└── traceability-matrix/     # 需求-用例追溯矩阵
```

## documents/ — 需求文档
存放各版本的需求规格说明书、用户故事、原型链接、需求变更记录。

## traceability-matrix/ — 追溯矩阵
维护需求 ID 与测试用例 ID 的双向映射表，确保：
- 每条需求至少对应一条测试用例（正向追溯）
- 每条测试用例可回溯到需求来源（逆向追溯）

## 使用流程

1. 产品提交 PRD → 放入 `documents/`
2. 测试人员评审需求，标注可测性
3. 编写/更新追溯矩阵
4. 在 `test-cases/` 中编写对应用例
