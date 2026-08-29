# language: zh-CN
# 名称：注释规范 · 对应 clean-code-standards.md §9（并与 docs/engineering-standards.md §1 一致）
Feature: 注释规范
  # 原则：好注释回答「为什么」，坏注释复述「是什么」。

  Background:
    Given 待评审代码位于 test-platform-v2/backend 或 test-platform-v2/frontend

  Scenario: 不写复述语法的注释
    Given 一个注释
    When 检查其内容
    Then 禁止「定义变量」「调用函数」「返回结果」类注释
    And 注释应回答「这段代码干嘛用的 / 为什么需要这样做」

  Scenario: 关键场景必须写注释
    Given 一段业务规则 / 权限判断 / 状态流转 / 异常兜底 / 数据迁移 / 定时任务 / 外部系统对接 / AI 调用 / 缓存策略
    When 检查是否有注释
    Then 应写注释说明用途与原因
    And 公共方法、服务类、复杂组件、CLI/CI 脚本须在入口写职责

  Scenario: 自动生成代码也须补用途注释
    Given 一段由 LLM/AI 生成的代码
    When 检查其注释
    Then 必须补齐用途注释，且须通过硬门禁后交付

  Scenario: 注释解释意图与约束
    Given 一段涉及异常处理的代码
    When 检查其注释
    Then 应解释「为什么这样处理」与后果
    And 例如 client.ts 里对 FastAPI 422 detail 转字符串的注释即为好注释

  Scenario: 公共方法带 docstring/JSDoc
    Given 一个后端公共方法或前端公共 hook
    When 检查其文档
    Then 后端用 docstring、前端用 JSDoc 标注职责与示例（参考 useApi.ts）
    And 应说明参数、返回与边界

  Scenario: 无调试遗留
    Given 提交前的代码
    When 检查遗留调试语句
    Then 禁止 print / console.log / breakpoint / debugger（对齐 AGENTS.md §3.1）
    And 无临时打印与未清理的调试断点
