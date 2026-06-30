# 测试体系

## 目录结构

```
tests/
├── README.md                          # 本文件 — 测试体系总览与规范
├── requirements/                      # 需求分析
│   ├── documents/                     # 需求规格说明书（PRD/FRD）
│   └── traceability-matrix/           # 需求-用例追溯矩阵
├── test-cases/                        # 测试用例
│   ├── functional/                    # 功能测试用例
│   ├── integration/                   # 集成测试用例
│   ├── performance/                   # 性能测试用例
│   └── security/                      # 安全测试用例
├── api-testing/                       # 接口测试
│   ├── collections/                   # 接口集合（Postman / Bruno 等）
│   ├── environments/                  # 环境变量配置
│   └── reports/                       # 测试报告
└── automation/                        # 自动化测试
    ├── ui/                            # UI 自动化
    ├── service/                       # 接口/服务层自动化
    ├── fixtures/                      # 测试数据与夹具
    ├── utils/                         # 公共工具模块
    ├── config/                        # 运行配置
    └── reports/                       # 自动化报告
```

## 模块职责

### requirements/ — 需求分析
存放需求文档、评审记录和需求-用例的双向追溯矩阵，确保每条需求都有对应的测试覆盖。

### test-cases/ — 测试用例
按类型划分：功能、集成、性能、安全。用例采用统一模板（ID、前置条件、步骤、预期结果、优先级）。

### api-testing/ — 接口测试
手工/半自动接口测试资产：请求集合、环境变量、一次性的测试报告。可复用的自动化脚本应放入 `automation/service/`。

### automation/ — 自动化测试
可重复执行的自动化代码。UI 和 Service 层分离，公共逻辑抽取到 utils/，测试数据集中管理在 fixtures/。

## 命名规范

| 类型       | 格式                                        | 示例                                     |
| ---------- | ------------------------------------------- | ---------------------------------------- |
| 测试用例   | `TC-{模块}-{编号}.md`                       | `TC-login-001.md`                        |
| 需求文档   | `{系统}-{版本}-需求规格说明书.md`           | `CamelTv-v1.0-需求规格说明书.md`          |
| 接口集合   | `{服务名}-{环境}.json`                      | `user-service-dev.json`                  |
| 自动化脚本 | `test_{模块}.py` / `test_{module}.ts`       | `test_login.py`                          |
| 测试数据   | `{实体}_{场景}.json`                        | `user_invalid.json`                      |

## 用例优先级

- **P0** — 核心路径，阻塞性问题，每个版本必测
- **P1** — 常用功能，严重影响用户使用
- **P2** — 一般功能，边界/异常场景
- **P3** — 次要功能，UI/文案类
