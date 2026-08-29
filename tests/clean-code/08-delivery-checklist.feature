# language: zh-CN
# 名称：交付与自检清单 · 对应 clean-code-standards.md §10（并与 AGENTS.md §3 对齐）
Feature: 交付与自检清单
  # 每次 git push 前对照本 Feature 逐条自查；任一条 [强制] 不满足即 Block PR。

  Background:
    Given 一次即将 git push 的代码提交

  Scenario: 后端命名合规
    Given 后端变更
    When 自检命名
    Then 遵循 PEP 8 + 意图命名，无 data/tmp/val 类命名

  Scenario: 后端函数合规
    Given 后端变更
    When 自检函数
    Then 函数 ≤ 30 行、单一职责、无魔法数字、常量已提取

  Scenario: 后端路由/错误/事务合规
    Given 后端变更
    When 自检分层与错误处理
    Then 路由层不触 ORM、不写业务逻辑；错误用 APIException 体系
    And 事务用 transaction(db) 或显式 commit/rollback；无裸 except: pass

  Scenario: 后端状态与删除语义合规
    Given 后端变更
    When 自检状态与删除
    Then 状态/删除语义走规范词表与 is_deleted；无 == False
    And 新队列走 task_queue.py 原语，锁列/失联回收齐全

  Scenario: 后端门禁通过
    Given 后端变更
    When 执行本地自检
    Then ruff check app/ --select F821 通过
    And 相关 pytest 通过，全量回归说明失败集合

  Scenario: 前端组件/命名合规
    Given 前端变更
    When 自检组件与命名
    Then 组件薄、命名表意；any 仅在边界的 TODO 注释处使用

  Scenario: 前端副作用合规
    Given 前端变更
    When 自检副作用
    Then useEffect 有 cleanup；useCallback 无循环依赖；无 N+1；TabsContent 用 forceMount（docs/engineering-standards.md §4）

  Scenario: 前端 API 与错误合规
    Given 前端变更
    When 自检 API 与错误
    Then API 调用走 api/ 层与 useApi；错误在前端内联；AbortError 已处理

  Scenario: 前端依赖与状态合规
    Given 前端变更
    When 自检依赖与状态
    Then 依赖单向；Store 不做 API 调用；复杂逻辑在 hooks/纯函数

  Scenario: 前端门禁通过
    Given 前端变更
    When 执行本地自检
    Then npm run typecheck && npm run build 通过
    And 相关 Vitest 通过

  Scenario: 通用交付红线
    Given 本次变更
    When 自检通用项
    Then 无调试遗留、无硬编码凭据、无备份/DB/IDE 临时文件（AGENTS.md §3.5）
    And 生成代码已补用途注释并通过硬门禁
    And 改动涉及的模块/状态/分层已同步 backend/CLAUDE.md、frontend/CLAUDE.md 或相应 PRD（文档保鲜）
