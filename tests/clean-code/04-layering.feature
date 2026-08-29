# language: zh-CN
# 名称：分层与依赖方向（SOLID / SRP + DIP）· 对应 clean-code-standards.md §6
Feature: 分层与依赖方向
  # 原则：让依赖指向抽象与稳定方向，而非具体与易变方向。

  Background:
    Given 待评审代码位于 test-platform-v2/backend 或 test-platform-v2/frontend

  Scenario: 后端分层单向依赖
    Given 一个后端调用链
    When 检查其依赖方向
    Then 应为 Router（api/v1/）→ Service（services/）→ Model（models/）
    And 不应出现 Router 直接触达 ORM 或反向依赖

  Scenario: 后端路由层禁 ORM
    Given 一个 app/api/v1/ 下的路由文件
    When 检查其 import 与查询
    Then 禁止 from app.models import ...、select(、db.query(（查询收敛到 services）
    And 仅豁免 BackgroundTasks 使用的独立 SessionLocal 会话，不含查询

  Scenario: 后端 Service 之间通过方法协作
    Given 一个跨域协作（如用例 → 执行）
    When 检查其实现
    Then 应通过显式 service 方法协作，而非透传裸 session 或写内联 SQL

  Scenario: 新队列认领走统一原语
    Given 一个需认领/回收/收尾的任务队列
    When 检查其认领实现
    Then 应走 core/task_queue.py（QueueSpec + atomic_claim* / reap_stale / finish_task）
    And 禁止自研 SELECT → 改 → commit 认领（TOCTOU）
    And 锁列统一 locked_by/locked_at，且必须有失联回收（默认 30 分钟）

  Scenario: 稳定的抽象放 core
    Given 一个后端组件
    When 判断其稳定性
    Then 相对稳定的抽象（config/db/deps/exceptions/task_queue/base_service）放 core/
    And 易变业务（services/）依赖 core，不反向

  Scenario: 前端依赖单向
    Given 一个前端调用链
    When 检查其依赖方向
    Then 应为 pages/ → hooks/ → api/ → client.ts
    And 页面不直接 fetch，统一走 api/ 层

  Scenario: 前端 Store 不做 API 调用
    Given 一个前端 Zustand store（stores/）
    When 检查其实现
    Then 只存状态，不调 API（对齐 frontend/CLAUDE.md）
    And API 调用在页面组件或 hooks 中完成

  Scenario: 前端可复用逻辑抽 hooks
    Given 一个需要数据拉取/可取消副作用的页面组件
    When 检查其实现
    Then 应用 useApi / usePaginatedList / useAbortableEffect，而非每页手写 abort/loading/error
    And 组件边界由共享 shadcn/ui 组件承担通用底座

  Scenario: 前端组件边界合理复用
    Given 一个业务组件需要通用 UI 元素（Button/Dialog）
    When 检查其实现
    Then 应使用 components/ui/ 的共享组件，不重复造轮子
    And 业务组件只做领域装配
