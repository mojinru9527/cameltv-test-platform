"""Application settings loaded from environment variables.

Security: ALL sensitive values (secret_key, passwords, API keys) MUST be
provided via environment variables or .env file in production.
Default empty values will cause a startup validation error in production mode.
"""
from __future__ import annotations

import secrets
from functools import cached_property

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── App identity ──
    app_name: str = "CamelTv Test Platform API"
    app_version: str = "2.1.0"
    environment: str = "development"          # "development" | "production"

    # ── Security (sensitive — no hardcoded defaults) ──
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # ── Auth cookie (P1-1: JWT via httpOnly cookie, XSS-hardened) ──
    cookie_name: str = "cameltv_token"
    cookie_secure: bool = False               # production: true (requires HTTPS)
    cookie_samesite: str = "lax"              # "strict" | "lax" | "none"
    cookie_domain: str = ""                    # empty = host-only cookie
    cookie_path: str = "/api"

    # ── CSRF protection (P1-1/S1d) ──
    csrf_enabled: bool = True
    csrf_allowed_origins: str = ""             # comma-separated; empty = use allowed_origins

    # ── Login rate limit (C70-3) ──
    login_rate_limit_max: int = 10             # 生产安全默认：10 次 / 窗口
    login_rate_limit_window_seconds: int = 900

    # ── 外放轻量模式（Batch 104）：注册 / 邀请码 / 自助项目 ──
    # 默认开放普通用户注册；受控环境可显式关闭注册或强制平台邀请码。
    registration_enabled: bool = True
    invite_code_required: bool = False         # 可选：开启后注册必须凭平台邀请码
    default_registration_role: str = "tester"  # 注册用户的默认全局角色
    max_projects_per_user: int = 5             # 普通用户可拥有的启用项目上限
    max_team_organizations_per_user: int = 5   # Batch 105：团队组织上限（个人组织不计入）
    register_rate_limit_max: int = 5           # 注册限流：5 次 / 窗口
    register_rate_limit_window_seconds: int = 900
    # 前端正式域名（Batch 109）：可分享链接（项目邀请等）使用的地址；空=回退请求域名
    frontend_url: str = ""

    # ── 模块可见性开关（P1a）──
    # 逗号分隔的菜单 code，软下线对应入口（侧边栏 + 访客目录；页面路由保留可直达）。
    # 默认隐藏通知配置与集成配置：两者缺真实 SMTP/Webhook/Jira/ELK 端点，属 fail-closed
    # 占位配置页。恢复方法：DISABLED_MENUS= 置空或按需删减 code。
    disabled_menus: str = "menu:notify,menu:integration"

    @property
    def effective_login_rate_limit(self) -> tuple[int, int]:
        """生产保持安全默认；开发/测试环境放宽以支持自动化验收（非安全降级）。"""
        if self.environment in ("development", "test"):
            return max(self.login_rate_limit_max, 100), self.login_rate_limit_window_seconds
        return self.login_rate_limit_max, self.login_rate_limit_window_seconds

    @property
    def effective_registration_enabled(self) -> bool:
        """注册总开关：development/test 始终开放，其他环境服从显式配置。"""
        if self.environment in ("development", "test"):
            return True
        return self.registration_enabled

    @property
    def effective_register_rate_limit(self) -> tuple[int, int]:
        """注册限流：生产保持安全默认；开发/测试放宽（同 C70-3 口径）。"""
        if self.environment in ("development", "test"):
            return max(self.register_rate_limit_max, 100), self.register_rate_limit_window_seconds
        return self.register_rate_limit_max, self.register_rate_limit_window_seconds

    # ── CSP (P1-2/S2c) ──
    csp_enabled: bool = True
    csp_header: str = "script-src 'self' cdn.jsdelivr.net; object-src 'none'; base-uri 'self'"

    # ── Security headers (C3) ──
    security_headers_enabled: bool = True

    # ── Database ──
    database_url: str = "sqlite:///./data/platform.db"
    # Independent, executor-owned release-control SQLite store. Empty keeps
    # the operations API fail-closed instead of creating an application-owned
    # parallel release fact store.
    release_control_database_path: str = ""
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    auto_create_tables: bool = True


    # ── PostgreSQL connection pooling (V2.6) ──
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # ── Default admin ──
    admin_username: str = "admin"
    # Required in production; generated in development only for initial creation.
    admin_password: str = ""

    # ── Seed users ──
    # Required in production; generated in development only for initial creation.
    tester_password: str = ""
    tester_username: str = "tester"
    # 运营只读账号（C31-3）：viewer 角色，仅查看
    viewer_username: str = "viewer"
    viewer_password: str = ""
    # 是否创建内置演示账号（tester/viewer）。生产外放后建议 false，
    # 避免每次部署启动时重建演示账号（Batch 109，配合生产验收数据清理）
    seed_demo_users: bool = True

    # ── ELK ──
    elk_base_url: str = ""
    elk_index: str = "*"

    # ── AI / LLM ──
    ai_enabled: bool = True
    ai_api_base_url: str = "https://api.deepseek.com"
    ai_api_key: str = ""                       # production: required
    ai_model: str = "deepseek-v4-pro"
    ai_max_tokens: int = 16384                 # requested maximum output per sub-call
    ai_temperature: float = 0.3
    ai_split_calls: bool = True                # split generation into functional + API parallel calls to avoid truncation

    # ── DeepSeek Harness (dsh) — Batch 172 ──
    dsh_enabled: bool = False                    # 总开关：启用 dsh 执行能力（A/B/C 共用）
    dsh_runtime: str = "node"                    # node | python-sdk；Windows 本地开发用 node，生产 Linux 用 python-sdk
    dsh_model: str = "deepseek-v4-flash"         # harness 使用模型
    dsh_base_url: str = ""                       # 空 = 复用 ai_api_base_url（DeepSeek 兼容端点）
    dsh_api_key: str = ""                        # 空 = 复用 ai_api_key
    dsh_session_root: str = ""                   # 会话 JSONL 目录；空 = backend/storage/dsh-sessions
    dsh_harness_path: str = ""                   # node runtime 的 dsh CLI 入口（如 F:\deepseek-harness\apps\cli\lib\bin.js）
    dsh_cordis_config: str = ""                  # python-sdk runtime 的 cordis 组合配置；空 = 内置 minimal 配置
    dsh_timeout_seconds: float = 600.0           # 单任务超时（秒）
    dsh_max_output_chars: int = 20000            # 输出截断上限
    dsh_workspace: str = ""                      # agent workspace 根；空 = 每次任务在 session_root 下建隔离工作区
    # ── Batch 184（C172-1）沙箱加固配置 ──
    dsh_max_concurrent: int = 1                  # 全局并发 DSH 任务上限（安全优先默认串行；node/python-sdk 均受控）
    dsh_max_task_chars: int = 20000              # 单任务文本长度上限（超限直接拒绝）
    # ── Batch 191：AgentTeams 团队模式配置 ──
    dsh_team_timeout_seconds: float = 1800.0     # 团队任务超时（覆盖单任务 600s；R-4）
    dsh_team_poll_seconds: float = 3.0           # 团队进度轮询间隔（PRD 成功指标引用）
    dsh_team_heartbeat_seconds: float = 60.0     # 团队执行心跳间隔（locked_at 续期，防 stale 误回收；R-1 冒烟暴露）
    dsh_team_profile: str = "agent-team"         # node runtime 团队 profile 名（CLI 从 $DSH_HOME/profiles/ 解析）
    dsh_team_cordis_config: str = ""             # python-sdk runtime 团队 cordis 路径；空 = 内置 team.cordis.yml
    dsh_team_harness_path: str = ""              # 团队 profile 的 DSH_HOME 覆盖；空 = CLI 默认 $DSH_HOME（自动探测）
    # ── DSH 测试 Agent 框架：模型池（阶段 3 产品化）──
    # 逗号分隔可用模型清单（如 "deepseek-v4-flash,deepseek-v4-pro"）；空 = 不限（仅校验非空串）。
    # 平台侧设置页据此渲染模型下拉，任务经 params.model 按任务指定，runner 注入 DSH_MODEL。
    dsh_model_pool: str = ""
    # ── 存储保留期清理（生产磁盘防护）──
    # 生产 Railway 卷曾被 ui-runs/dsh-sessions 累积写满导致 DSH 任务 ENOSPC；
    # 按 mtime 清理超期旧产物（ui-runs 运行目录 + ws-* 工作区 + 会话 jsonl）。
    storage_retention_enabled: bool = False          # 总开关；生产建议开启
    storage_retention_days: int = 7                  # 超过 N 天的旧产物删除
    storage_retention_hour: int = 2                  # 每日执行时刻（Asia/Shanghai）
    storage_retention_minute: int = 30
    storage_retention_root: str = ""                 # 清理根目录；空 = 复用 dsh_session_root 父目录（生产 /app/storage）
    storage_retention_include_plan_sync: bool = False  # 是否一并清理 plan-sync 过期子目录（与计划执行历史关联，默认关）

    # ── AI 降级 / 超时（DeepSeek 分类器不可用时的本地降级提取）──
    ai_timeout_seconds: float = 180.0          # 单次 AI 调用超时（秒）
    ai_retry_attempts: int = 2                 # 瞬时失败（超时/网络）总尝试次数，最小 1
    ai_fallback_on_failure: bool = True        # 瞬时失败时降级到本地模块提取，返回可复核草稿而非硬失败
    # ── batch-167: 需求 URL 适配器 ──
    requirement_url_timeout_seconds: float = 30.0   # 需求 URL 抓取超时
    ui_run_timeout_seconds: float = 90.0            # batch-169: 单条 UI 用例执行超时（env UI_RUN_TIMEOUT_SECONDS）
    ui_runner_timeout_seconds: float = 900.0        # Batch 187: UI Runner 整任务超时（env UI_RUNNER_TIMEOUT_SECONDS；默认 15min，覆盖 10 条用例多 spec 回归）
    ui_test_runner_dir: str = ""                    # C-UI-PROD-001: Playwright 运行根目录（空=默认 backend/tests/playwright；可配 tests/automation/ui 跑体育 E2E）
    # ── 性能采集（Batch 185 / C99-1）──
    perf_cpu_report_mode: str = "raw"            # raw=聚合可>100%（多核如实）| per_core=除以核数归一（0-100%）
    pingcode_api_base_url: str = ""                 # PingCode 开放 API 根地址
    pingcode_api_token: str = ""                    # PingCode 访问令牌（环境变量注入）
    confluence_api_base_url: str = ""               # Confluence REST API 根地址
    confluence_api_token: str = ""                  # Confluence 访问令牌（环境变量注入）

    # ── File paths (configurable for portability) ──
    workspace_root: str = ""      # empty = auto-detect from app/services/__file__
    skill_dir: str = ""           # test-case-design skill directory
    lanhu_mcp_dir: str = ""       # lanhu-mcp module directory
    data_dir: str = ""            # extracted data cache directory

    # ── OpenVPN Connect preflight（仅 test 类型环境；默认关闭）──
    openvpn_auto_connect_enabled: bool = False
    openvpn_connect_executable: str = "%ProgramFiles%/OpenVPN Connect/OpenVPNConnect.exe"
    openvpn_profile_directory: str = "%APPDATA%/OpenVPN Connect/profiles"
    openvpn_connect_timeout_seconds: float = 30.0
    openvpn_probe_timeout_seconds: float = 2.0
    openvpn_doh_timeout_seconds: float = 3.0
    openvpn_doh_resolver_url: str = "https://dns.google/resolve"

    # ── SMTP (optional, for email notifications) ──
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True
    smtp_verify_cert: bool = True       # P1-S5b: SMTP TLS 证书验证开关
    smtp_ca_bundle: str = ""             # P1-S5b: 自定义 CA 证书包路径

    # ── External Integration Sync (V2.6) ──
    sync_enabled: bool = True
    sync_retry_attempts: int = 2
    sync_timeout_seconds: int = 30

    # ── Knowledge Center / RAG / Agent (M0 治理开关) ──
    # 安全默认：全部 OFF。知识入库为写路径的后台副作用，须由运维在评审脱敏与容量后
    # 显式开启（避免合入即在共享/测试环境自动激活对全量写操作的入库）。
    knowledge_ingest_enabled: bool = False       # M1 知识源入库总开关（默认关，显式开启）
    rag_enabled: bool = True                     # 是否启用 RAG 检索（M2）
    knowledge_graph_enabled: bool = True         # 是否启用知识图谱（M3）
    ai_artifact_allow_batch_import: bool = False # AI 产物是否允许批量导入正式库
    knowledge_ingest_production_data: bool = False  # 生产环境执行结果是否允许进入知识库

    # ── M2 向量化 / 混合检索（RAG）──
    # 本地 fastembed(onnx) 嵌入，离线不外传（见 ADR-0010）。仅在 rag_enabled 时激活嵌入管线。
    embedding_model: str = "BAAI/bge-small-zh-v1.5"  # 中文小模型，512 维
    embedding_dim: int = 512
    embedding_batch_size: int = 32               # 批量嵌入/回填批大小
    embedding_cache_dir: str = ""                # 空=fastembed 默认（~/.cache/fastembed）
    # bge 检索建议对 query 加前缀以对齐训练目标；passage 侧不加
    embedding_query_prefix: str = "为这个句子生成表示以用于检索相关文章："

    # ── LLM-Wiki 知识库 / 差异对比（VNext-1..5 治理开关）──
    # 安全默认全部 OFF：Wiki 编译与差异对比会调用 LLM（成本），须由运维显式开启。
    # external_llm_wiki_enabled 控制 VNext-5 外部连接器。
    wiki_enabled: bool = False                   # 平台内 Wiki 知识库总开关（导入/编译/页面）
    wiki_auto_ingest_enabled: bool = False       # 导入 raw source 后是否自动触发 Wiki 编译
    wiki_diff_enabled: bool = False              # 是否启用知识库差异对比
    wiki_auto_create_artifact: bool = False      # 差异是否自动生成待审 AI 产物
    lanhu_mcp_enabled: bool = True               # 是否启用蓝湖 MCP 提取
    external_llm_wiki_enabled: bool = False      # 是否启用外部 LLM-Wiki 连接器（默认关）
    wiki_lint_enabled: bool = False              # 是否启用 Wiki 健康体检（默认关）
    embedding_health_required: bool = False      # 是否要求 embedding 健康检查通过后才允许搜索

    # ── Lanhu Evidence Pack / OCR ──（默认关，采集+OCR 成本高）
    lanhu_evidence_enabled: bool = True
    lanhu_evidence_worker_enabled: bool = True
    lanhu_evidence_max_concurrent: int = 1
    lanhu_evidence_stale_after_seconds: int = 600
    lanhu_evidence_storage_dir: str = ""         # 空 = backend/storage/lanhu-evidence
    lanhu_capture_viewport_width: int = 1440
    lanhu_capture_viewport_height: int = 1200
    lanhu_capture_scroll_step_ratio: float = 0.85
    lanhu_capture_max_segments_per_page: int = 30
    lanhu_capture_wait_ms: int = 600
    schedule_stale_seconds: int = 1200  # Batch 164/C163-1：调度运行失联回收阈值（秒）
    lanhu_ocr_provider: str = "local"            # local/cloud/mock
    lanhu_ocr_command: str = ""                  # 命令模板，如 paddleocr --image {image}
    lanhu_ocr_min_confidence: float = 0.60
    lanhu_evidence_word_embed_screenshots: bool = True
    lanhu_evidence_import_to_requirement: bool = True
    lanhu_evidence_import_to_knowledge: bool = True
    lanhu_evidence_import_to_wiki: bool = True

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    def get_initial_admin_password(self) -> str:
        """Return the configured password or generate one for initial admin creation."""
        if self.admin_password:
            return self.admin_password
        if self.environment == "development":
            pwd = secrets.token_urlsafe(12)
            import logging
            logging.getLogger("uvicorn").warning(
                "[security] ADMIN_PASSWORD not set — generated for "
                "initial admin creation: %s (shown once; save it now)",
                pwd,
            )
            return pwd
        return ""  # production will fail validation

    @cached_property
    def effective_secret_key(self) -> str:
        """Dev: auto-generate a random key when unconfigured (logged to console)."""
        if self.secret_key:
            return self.secret_key
        if self.environment == "development":
            key = secrets.token_hex(32)
            import logging
            logging.getLogger("uvicorn").warning(
                "[security] SECRET_KEY not set — auto-generated dev key (valid this session only)"
            )
            return key
        return ""

    @property
    def dsh_api_key_effective(self) -> str:
        """DSH 凭据：优先 dsh_api_key，回退 ai_api_key。"""
        return self.dsh_api_key or self.ai_api_key

    @property
    def dsh_base_url_effective(self) -> str:
        """DSH 端点：优先 dsh_base_url，回退 ai_api_base_url。"""
        return self.dsh_base_url or self.ai_api_base_url

    def dsh_unavailable_reason(self) -> str:
        """返回 DSH 不可用原因；空字符串 = 可用。"""
        if not self.dsh_enabled:
            return "DSH 服务未启用"
        if not self.dsh_api_key_effective:
            return "DSH_API_KEY/AI_API_KEY 未配置"
        # node runtime 的 CLI 入口检查在 dsh_runner.runtime_available() 中做
        # （支持默认入口兜底），此处只做开关与凭据检查。
        return ""

    @property
    def dsh_model_pool_list(self) -> list[str]:
        """模型池清单（DSH 测试 Agent 框架）：逗号分隔 → 去空去重列表。空池 = []。"""
        return [m.strip() for m in (self.dsh_model_pool or "").split(",") if m.strip()]

    def dsh_model_allowed(self, model: str | None) -> bool:
        """模型池准入：未配置池（不限）或模型在池内返回 True。"""
        if not model:
            return True
        pool = self.dsh_model_pool_list
        return (not pool) or (model in pool)

    def validate_security(self) -> list[str]:
        """Return a list of security misconfigurations; empty list = ok."""
        issues: list[str] = []

        if self.environment == "production":
            if not self.secret_key or self.secret_key.startswith("dev-"):
                issues.append("SECRET_KEY 未设置或仍为开发默认值，请通过环境变量/secret 管理设置强密钥")
            if not self.admin_password or self.admin_password == "admin123":
                issues.append("ADMIN_PASSWORD 未设置或仍为默认值，请设置强密码")
            if self.seed_demo_users and not self.tester_password:
                issues.append("TESTER_PASSWORD 未设置，请为种子测试用户设置强密码")
            if self.ai_enabled and not self.ai_api_key:
                issues.append("AI_API_KEY 未设置，AI 功能将不可用")
            if self.dsh_enabled and not self.dsh_api_key_effective:
                issues.append("DSH 已启用但缺少 DSH_API_KEY/AI_API_KEY，DSH 功能将不可用")
            if not self.cookie_secure:
                issues.append("生产环境 cookie_secure 必须为 True（需要 HTTPS），否则 httpOnly cookie 以明文传输")
            if self.cookie_samesite == "none" and not self.cookie_secure:
                issues.append("SameSite=None 要求 cookie_secure=True，否则浏览器将拒绝 cookie")

        if self.environment == "development":
            if self.secret_key and self.secret_key.startswith("dev-"):
                issues.append("开发模式使用弱 SECRET_KEY（仅本地可接受）")

        return issues


settings = Settings()

