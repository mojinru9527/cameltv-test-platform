# 自动化测试

## 目录

```
automation/
├── ui/                      # UI 自动化测试
├── service/                 # 接口/服务层自动化测试
├── fixtures/                # 测试数据与夹具
├── utils/                   # 公共工具模块
├── config/                  # 运行配置
└── reports/                 # 自动化测试报告
```

## 技术选型（待确定）

| 层级    | 推荐框架            | 语言         |
| ------- | ------------------- | ------------ |
| UI      | Playwright / Selenium | TS / Python  |
| Service | pytest / Jest / Supertest | Python / TS |
| 报告    | Allure / Playwright HTML | —            |

## 分层原则

- **ui/** — 页面交互、端到端流程、视觉回归
- **service/** — API 正确性、契约验证、数据校验
- **fixtures/** — 不包含在代码中的测试数据（JSON、CSV、数据库 dump）
- **utils/** — 跨层级共享的工具函数（认证、数据工厂、断言封装）
- **config/** — 环境切换、超时、重试等配置项

## 执行策略

- 提 PR → 触发 service 层自动化（必须通过）
- 合并到 main → 触发全量回归（service + ui）
- 定时任务 → 每日凌晨执行冒烟套件
