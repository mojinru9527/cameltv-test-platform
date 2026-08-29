# language: zh-CN
# 名称：命名规范 · 对应 clean-code-standards.md §3
Feature: 命名规范
  # 原则：名字要自解释目的，而不是藏起目的。
  # 覆盖 §3.1 通用 / §3.2 后端 / §3.3 前端 / §3.4 术语表

  Background:
    Given 待评审代码位于 test-platform-v2/backend 或 test-platform-v2/frontend
    And 代码遵循对应语言的既有目录与命名约定（backend/CLAUDE.md、frontend/CLAUDE.md）

  Scenario: 使用意图命名而非类型命名
    Given 一个函数或变量，其用途是获取某个测试用例的详情
    When 评审其命名
    Then 应使用意图名（如 case_detail），而不是类型名（如 data、temp、obj、val、list1）
    And 不得出现无信息量的通用名

  Scenario: 布尔命名使用统一前缀
    Given 一个变量是布尔类型
    When 评审其命名
    Then 应使用 is_ / has_ / can_ / should_ 前缀（如 is_deleted、can_run、has_asserts）
    And 后端软删标志必须统一为 is_deleted（对齐 backend/CLAUDE.md 删除语义）

  Scenario: 同一概念全仓库只用唯一术语
    Given 概念「测试用例」「测试计划」「执行」「缺陷」「需求」「环境」
    When 在前后端代码中检索该概念的命名
    Then 各自只出现唯一主名（test_case / test_plan / execution / defect / requirement / environment）
    And 不应同时出现新旧混用（如 case 与 test_case 并存的旧实体迁移）

  Scenario: 后端遵循 PEP 8 命名
    Given 一个 backend 的 .py 文件
    When 检查其命名风格
    Then 模块/函数/变量使用 snake_case、类使用 PascalCase、常量使用 UPPER_SNAKE_CASE
    And 函数名为「动词 + 对象」（如 fetch_case_by_id、list_paginated）

  Scenario: 后端路由处理函数与 URL 风格对齐
    Given 一个 /api/v1/{resource} 路由
    When 检查其处理函数名
    Then GET 对应 list_xxx、POST 对应 create_xxx、与 backend/CLAUDE.md 的 URL 风格一致
    And 不使用 do_it / process / handle_data 等无信息量动词

  Scenario: 前端组件命名表意
    Given 一个 frontend 的 .tsx 组件
    When 检查其命名与文件命名
    Then 文件名使用 kebab-case、组件名使用 PascalCase、hooks 使用 useXxx、工具函数使用 camelCase
    And 组件名应表意（如 CaseTable、DefectFilterBar），不使用 Page1 / Widget / Container

  Scenario: 前端接口函数与后端对应
    Given 一个 frontend/src/api/xxx.ts 接口函数
    When 检查其命名
    Then 函数名与后端资源对应（如 fetchTestCases / createTestCase）
    And 资源词与后端保持一致

  Scenario: 禁止 any 作为万能逃生舱
    Given 一个 frontend 的 .tsx / .ts 文件
    When 检查类型标注
    Then 应显式类型化或使用 src/types/ 的生成类型
    And any 仅允许出现在边界（如 client.ts 的 detail.map(d: any)）且必须贴近边界处

  Scenario: 禁止误导性缩写与双关语
    Given 一个前后端标识符
    When 检查其缩写
    Then 不使用有歧义缩写（如 front 既表前端又表前台）
    And 同一概念全仓库只由一个词表达
