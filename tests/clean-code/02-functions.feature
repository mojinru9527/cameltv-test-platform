# language: zh-CN
# 名称：函数规范 · 对应 clean-code-standards.md §4
Feature: 函数规范
  # 原则：函数要小、要做一件事、只做一件事、使用抽象层级（SLAP）。

  Background:
    Given 待评审函数位于 test-platform-v2/backend 或 test-platform-v2/frontend

  Scenario: 单函数尽量不超过 30 行
    Given 一个后端函数
    When 统计其行数
    Then 应尽量 ≤ 30 行
    And 超长时应有拆分的函数/子步骤，而非让长函数继续膨胀

  Scenario: 函数遵循单一职责（SRP）
    Given 一个后端函数
    When 检查它是「渲染响应」「组装查询」「编排流程」中的哪一种
    Then 一个函数应只承担其中之一，不混用
    And 反例是「一个函数既查库、又拼 SQL、又算统计、又组装响应」

  Scenario: 使用抽象层级（SLAP）
    Given 一个后端函数体
    When 检查其内部语句层级
    Then 高层函数调用高层语义（fetch_case / build_tree / persist），不直接写原生 SQL
    And 低层查询语句（select(...).where(...)）只出现在低层函数

  Scenario: 路由层副作用收敛
    Given 一个 test-platform-v2/backend/app/api/v1 下的路由文件
    When 检查其职责
    Then 只做参数校验、权限、调用 Service、组装响应、db.commit()
    And 不包含业务逻辑与 ORM 查询（对齐 backend/CLAUDE.md 路由禁 ORM 强制项）

  Scenario: 事务使用上下文管理器包裹
    Given 一个后端需要多步写入的函数
    When 检查其事务处理
    Then 使用 with transaction(db): 包裹（core/base_service.py）
    And 异常时统一 rollback，避免手写 try/except 漏掉 commit

  Scenario: 禁止魔法数字
    Given 一个后端函数中出现的数字字面量
    When 判断其是否代表业务语义
    Then 应提取为常量或 settings 配置（如 page_size=20、超时 30 分钟、保留期 7 天）
    And 不得散落无解释的数字

  Scenario: 前端组件保持「薄」
    Given 一个 frontend 的页面组件
    When 检查其复杂度
    Then 组件应只是「数据 + 渲染」的装配层
    And 复杂逻辑应抽到 hooks/ 或纯工具函数（utils/、lib/）

  Scenario: 前端不在组件内编排复杂异步流程
    Given 一个 frontend 组件包含多个 useEffect
    When 检查其耦合
    Then 复杂编排应拆为子组件 + 自定义 hook + 纯函数
    And 避免单个组件内含 5 个 useEffect 的巨型实现

  Scenario: 前端纯函数与副作用分离
    Given 一个状态迁移逻辑（如执行状态、用例格式化、UI 运行结果）
    When 检查其实现位置
    Then 应写成可单测的纯函数（utils/executionStatus.ts、caseListFormatters.ts、uiRunResult.ts）
    And 副作用（fetch / 订阅）交给 useApi / useAbortableEffect

  Scenario: 避免巨型条件分支
    Given 一个包含大量 if/else 或平铺 schema 的函数
    When 检查其结构
    Then 应改用跳表/映射对象（如执行状态双值映射）
    And 不出现难以维护的超长条件链
