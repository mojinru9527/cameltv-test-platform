# language: zh-CN
# 名称：测试与代码质量（FIRST）· 对应 clean-code-standards.md §8
Feature: 测试与代码质量
  # 原则：整洁的代码必然可测；测试是代码的说明书。遵循 FIRST。

  Background:
    Given 新功能 / 新接口 / 新组件正在交付

  Scenario: 新功能必须带对应测试
    Given 一个后端新增接口或前端新增组件
    When 检查交付
    Then 后端应带 pytest 测试（backend/tests/），前端应带 Vitest（*.test.ts(x)）
    And 相关测试通过（对齐 AGENTS.md §3.1）

  Scenario: 测试遵循 FIRST 的 Fast
    Given 一个测试用例
    When 检查其执行依赖
    Then 单测须跑得快，不依赖真实网络/外部服务
    And 外部调用用 mock，避免慢速外部依赖

  Scenario: 测试遵循 FIRST 的 Independent 与 Repeatable
    Given 一个测试套件
    When 检查其独立性
    Then 测试间无顺序依赖，不共享可变全局
    And 结果可复现，不依赖本地时间/随机/绝对路径

  Scenario: 测试遵循 FIRST 的 Self-validating
    Given 一个测试用例
    When 检查其断言
    Then 每个测试有明确断言，不做无断言的「跑通即通过」

  Scenario: 测试遵循 FIRST 的 Timely
    Given 一次代码提交
    When 检查测试的编写时机
    Then 测试应随代码一起写，不是事后补

  Scenario: 每个需求点有正负用例
    Given 一个功能点清单
    When 检查用例覆盖
    Then 每个功能点 ≥ 1 条正面用例 + ≥ 1 条负面用例

  Scenario: 覆盖错误路径与边界
    Given 一个接口或函数
    When 设计测试
    Then 应覆盖 not_found、无权限、超长、空数据、并发认领等错误/边界
    And 参考守卫测试（tests/test_dsh_sandbox.py、tests/test_route_layer_orm_ban.py）

  Scenario: 用 fixture 而非重复造数据
    Given 多个测试需要相同前置数据
    When 检查数据准备
    Then 应用 fixture 复用，且测试数据与逻辑分离（docs/engineering-standards.md §3）
    And 不把账号/密码/环境变量硬编码进测试

  Scenario: 纯函数/快照作为回归契约
    Given 一个无副作用的纯函数（如 uiRunResult.ts、caseListFormatters.ts、executionStatus.ts）
    When 检查其测试
    Then 应有单元/快照测试，因为它是回归最稳的契约
