# language: zh-CN
# 名称：与 AI 生成代码的适配 · 对应 clean-code-standards.md §7
Feature: AI 生成代码适配
  # 本平台大量代码由 LLM/DSH Agent 生成；规范需 adapt 成机器可执行的确定性检查。

  Background:
    Given 一段即将交付的由 LLM / DSH Agent 生成的代码

  Scenario: 生成代码落地前跑硬门禁
    Given 一段自动生成的代码
    When 准备提交
    Then 后端须过 ruff check app/ --select F821，前端须过 npm run typecheck && npm run build
    And 生成代码也必须通过这些门禁（对齐 AGENTS.md §3.1）

  Scenario: 生成代码必须补用途注释
    Given 一段自动生成的业务代码
    When 检查其注释
    Then 必须补齐用途注释才能交付
    And 禁止「只解释语法」的低价值注释

  Scenario: 生成代码禁止硬编码凭据与环境值
    Given 一段自动生成的代码
    When 检查其中的配置/凭据
    Then 禁止硬编码账号、密码、Token、API Key、私有密钥、X-Project-Id
    And 应走 env / core/config.py / environment / dataset 模块注入

  Scenario: 生成代码走版本的 persona 约束
    Given 一个 DSH/Agent 生成任务
    When 检查其 persona（tester_team_persona.py / agent_team_persona.py）
    Then persona 应把规范要点（命名、分层、禁 ORM、状态词表）写入提示词
    And 使生成型 Agent 产出与全仓一致的风格

  Scenario: 生成断言/测试同样适用规范
    Given 一段自动生成的断言或测试
    When 检查其质量
    Then 应遵循 docs/engineering-standards.md §2 的测试注释要求
    And 用例需遵守 test-case-design skill 自检清单

  Scenario: 三桶过滤
    Given 一段 AI 生成的代码
    When 检查其流向
    Then 应经过 AI 生成 → 人工/评审 Review → CI/Chat 检查三桶
    And 评审不是可选项，不能直接跳过

  Scenario: 生成代码不产生污染交付物
    Given 一段由 LLM 生成的用例/需求/代码
    When 检查其合规性
    Then 不应污染整个交付物，须满足本条规范
    And 不引入无关文件或夹带变更（AGENTS.md §3.5）
