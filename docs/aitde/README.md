
# CamelTV AITDE V3.0 → V4.0 详细开发实施方案包

本目录用于**直接安排版本开工**。

## 文档

| 文件 | 版本目标 |
|---|---|
| `V3.0_Detailed_Development_Implementation_Plan.md` | Mission / Source / Scope / Ambiguity / Contract / Scenario / Oracle / Functional View |
| `V3.1_Detailed_Development_Implementation_Plan.md` | Unified Execution / Assertion / Evidence / Replay |
| `V3.2_Detailed_Development_Implementation_Plan.md` | DataRequirement / Fixture / Lease / DB Runtime / Cleanup |
| `V3.3_Detailed_Development_Implementation_Plan.md` | Command IR / Browser / Hybrid / Assisted Manual / Observe |
| `V3.4_Detailed_Development_Implementation_Plan.md` | Temporal / Network Worker / Secret / Policy / mTLS |
| `V3.5_Detailed_Development_Implementation_Plan.md` | Environment Fingerprint / Continuous Acceptance / RED→GREEN |
| `V3.6_Detailed_Development_Implementation_Plan.md` | Production ReadOnly Evidence / Mask / Prod→Test Template |
| `V3.7_Detailed_Development_Implementation_Plan.md` | Lineage / ChangeSet / Impact / Smart Regression |
| `V3.8_Detailed_Development_Implementation_Plan.md` | Failure Triage / Healing / Flaky / Gap / Feedback Learning |
| `V4.0_Detailed_Development_Implementation_Plan.md` | Legacy Cutover / Enterprise Stable / Governance / DR |
| `99_Cross_Version_Validation_and_GoLive_Gates.md` | 每个版本完成后是否允许进入下一版本的总 Gate |

## 和原 4 份母文档的关系

```text
01_Overall_Upgrade_Blueprint
= 架构宪法

02_Backend_Implementation_Design
= 后端总规范

03_Frontend_UX_Implementation_Design
= 前端/Tester UX 总规范

04_Version_Roadmap_and_Migration
= 版本总路线

本目录 V3.0~V4.0
= 每个版本真正施工文件

99 Validation
= 跨版本验收总控
```

## 推荐放入仓库

```text
docs/aitde/
├ architecture/
│  ├ 01_Overall_Upgrade_Blueprint.md
│  ├ 02_Backend_Implementation_Design.md
│  ├ 03_Frontend_UX_Implementation_Design.md
│  └ 04_Version_Roadmap_and_Migration.md
│
├ versions/
│  ├ V3.0_Detailed_Development_Implementation_Plan.md
│  ├ V3.1_Detailed_Development_Implementation_Plan.md
│  ├ V3.2_Detailed_Development_Implementation_Plan.md
│  ├ V3.3_Detailed_Development_Implementation_Plan.md
│  ├ V3.4_Detailed_Development_Implementation_Plan.md
│  ├ V3.5_Detailed_Development_Implementation_Plan.md
│  ├ V3.6_Detailed_Development_Implementation_Plan.md
│  ├ V3.7_Detailed_Development_Implementation_Plan.md
│  ├ V3.8_Detailed_Development_Implementation_Plan.md
│  └ V4.0_Detailed_Development_Implementation_Plan.md
│
└ validation/
   └ 99_Cross_Version_Validation_and_GoLive_Gates.md
```

## 使用规则

开一个版本时：

```text
04 Roadmap
→ 确认版本边界

对应版本 Detailed Plan
→ 拆 DB / API / Service / Frontend / Task / PR / Test

01/02/03
→ 校验没有偏离总架构

该版本 93~95 节
+
99 Validation
→ 决定是否可以进入下一版本
```

不要把 V3.0~V4.0 全部同时开成正式施工。可以并行做 PoC，但 canonical baseline 必须逐版通过 Transition Gate。
