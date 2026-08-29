# language: zh-CN
# 名称：错误处理 · 对应 clean-code-standards.md §5
Feature: 错误处理
  # 原则：错误处理也是程序的一部分；用异常/领域对象表达预期失败，不让失败污染主流程。

  Background:
    Given 待评审代码位于 test-platform-v2/backend 或 test-platform-v2/frontend

  Scenario: 后端使用统一异常体系
    Given 一个后端业务错误
    When 检查其抛出方式
    Then 应抛 APIException（core/exceptions.py）并由全局处理器统一转 {code, msg, data}
    And 不得在路由里到处 return {"code":1,"msg":...} 散落拼响应

  Scenario: 后端预期业务失败使用显式异常
    Given 一个业务失败场景（资源不存在 / 无权限 / 未登录）
    When 检查其表达方式
    Then 应使用 not_found() / forbidden() / unauthorized()
    And 并外部/历史状态经 canonical_exec_status() 规范化后再落库

  Scenario: 后端区分预期错误与系统异常
    Given 一个可能失败的调用
    When 检查其错误分类
    Then 预期业务失败用领域异常（如 AIProviderUnconfiguredError），系统异常只在边界捕获记日志
    And 不吞掉异常，不 return 裸布尔值表达业务语义

  Scenario: 禁止裸 except 吞掉异常
    Given 一个后端 try/except 块
    When 检查 except 内容
    Then 禁止 except Exception: pass
    And 若确需兜底，须注释「为什么容忍、失败后的行为」

  Scenario: 前端 Axios 统一拆 envelope 与错误处理
    Given 一个 frontend 的 API 请求经过 src/api/client.ts
    When 响应 code !== 0
    Then 应抛业务 Error 并附带 .code/.data，供调用方识别业务 404 等场景
    And 401 应统一登出、清缓存、跳转登录

  Scenario: 前端组件已知错误先本地呈现
    Given 一个前端页面调用 useApi 且失败
    When 检查错误呈现
    Then 应在 onError 回调做内联 UI 提示（useApi.ts 的 onError）
    And 不逐页重复打 toast

  Scenario: 前端放行 AbortError
    Given 一个请求因路由切换/被取消而中断
    When 检查 client.ts 与 useApi.ts 的错误分支
    Then 应对 ERR_CANCELED / AbortError 单独放行，不当作用户可见失败
    And 不 toast、不污染页面错误态

  Scenario: 前端用 ErrorBoundary 兜 UI 崩溃
    Given 一个前端组件在渲染期抛错
    When 检查上层保护
    Then 应有 ErrorBoundary（components/ErrorBoundary.tsx）兜底，避免整页白屏

  Scenario: 错误信息可被安全渲染
    Given 一个来自后端的错误 detail（如 FastAPI 422 的数组）
    When 检查其转字符串逻辑
    Then 应转成可读字符串（字段名 + 原因）
    And 不得把对象数组直接当 React child 渲染导致崩溃
