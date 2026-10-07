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

    # Same-host admission; enable only with a shared local volume across runners.
    heavy_task_budget_enabled: bool = False
    worker_execution_enabled: bool = True
    runner_http_url: str = ""
    # Security boundary for user-influenced Playwright/Node execution. This is
    # defense in depth, not a substitute for a dedicated sandbox container.
    execution_sandbox_enabled: bool = True
    execution_cpu_limit_seconds: int = 300
    execution_memory_limit_mb: int = 2048
    execution_file_size_limit_mb: int = 128
    execution_open_files_limit: int = 4096
    execution_process_limit: int = 256
    # ── Batch 259 / B2-1（H1）：执行沙箱出网白名单 ──
    # 逗号分隔的主机白名单（被测系统 + 平台 API）。空 = 不注入。
    # 进程内无法做内核级网络隔离，因此该值作为**唯一事实源**下发给子进程
    # （CAMELTV_EGRESS_ALLOWLIST），由部署层的容器/网络命名空间或节点侧代理执行。
    execution_egress_allowlist: str = ""
    # Actual ASGI body cap. Content-Length is an optimisation, never the
    # enforcement point, because chunked requests can omit it.
    max_request_body_bytes: int = 100 * 1024 * 1024
    # Outbound OpenAPI/spec imports must be bounded and default-deny internal
    # networks. Keep these values conservative because imports run in-process.
    outbound_request_timeout_seconds: float = 20.0
    outbound_max_redirects: int = 5
    outbound_max_response_bytes: int = 10 * 1024 * 1024
    knowledge_embedding_schedule_enabled: bool = False
    heavy_task_budget_capacity: int = 1
    orchestration_budget_capacity: int = 1
    heavy_task_budget_dir: str = ""

    # V40-013 encryption posture knobs (operator-set; verified by
    # EncryptionVerificationService, no secret values here).
    db_encryption_enabled: bool = False
    object_storage_encryption_enabled: bool = False
    use_external_secret_store: bool = False
    https_only: bool = False
    db_connection_tls: bool = False
    # V40-009 SSO scaffolding (real IdP handshake is external; values are config
    # only, never secrets committed).
    sso_enabled: bool = False
    sso_provider: str = ""  # oidc | saml
    sso_issuer: str = ""
    sso_client_id: str = ""
    sso_client_secret: str = ""
    sso_group_mapping: str = "{}"  # external_group -> local_role

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
    # 平台简化批次：通知/集成等已硬删，默认空；仅作运营临时下线的兜底开关。
    disabled_menus: str = ""

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
    # Phase 1 exact-response cache: opt-in only; namespace + model/prompt/input/params form the key.
    ai_exact_cache_enabled: bool = False
    ai_exact_cache_ttl_seconds: int = 86400

    # ── Phase 2: 独立本地 OpenAI-compatible Runtime + Shadow Mode ──
    ai_local_runtime_enabled: bool = False
    ai_gateway_url: str = ""
    ai_gateway_token: str = ""
    ai_gateway_role: str = "embedded"  # embedded | remote | gateway
    ai_runtime_mode: str = "cloud_only"  # cloud_only | shadow | local_preferred | local_only
    # ── P1-6：平台级 AI 配额闸门（app/services/ai_guard.py）──
    # 此前平台对 LLM 调用既无速率限制也无 token 预算，任何一条自动链路失控都会
    # 无限燃烧密钥；以下三项是平台级兜底（按项目维度统计 model_usage_ledger）。
    ai_guard_enabled: bool = True               # 总开关；False = 关闭闸门（用量台账仍继续记账）
    # 每项目每分钟 AI 请求上限。默认 60 而不是 10：一次「大文档生成用例」就是合法突发——
    # ai_service 每 24000 字符抽一次（_EXTRACT_CHUNK_CHARS）、每 12 个功能点生成一块
    # （_CHUNK_FP_LIMIT）、并发 5（_CHUNK_CONCURRENCY），截断还要重试，单次操作可发出
    # 15~30 次调用；上限压到 10 会让抽取块被静默丢弃（用例缺失）而不是"更安全"。
    # 60/分钟仍能拦住失控循环，真正的花费上限是下面 24h token 预算。
    ai_rate_limit_per_minute: int = 60
    ai_daily_token_budget: int = 2000000        # 每项目 24 小时 token 预算（input_units + output_units）
    ai_local_fallback_to_cloud: bool = True
    ai_local_base_url: str = "http://127.0.0.1:11434/v1"
    ai_local_api_key: str = ""
    ai_local_model: str = ""
    ai_shadow_enabled: bool = False
    ai_shadow_sample_rate: float = 0.0
    ai_shadow_timeout_seconds: float = 60.0
    ai_shadow_max_output_chars: int = 200000

    # ── 存储保留期清理（生产磁盘防护）──
    # 生产卷曾被 ui-runs 等累积写满；按 mtime 清理超期旧产物。
    storage_retention_enabled: bool = False          # 总开关；生产建议开启
    storage_retention_days: int = 7                  # 超过 N 天的旧产物删除
    storage_retention_hour: int = 2                  # 每日执行时刻（Asia/Shanghai）
    storage_retention_minute: int = 30
    storage_retention_root: str = ""                 # 清理根目录；空 = 默认存储根（生产 /app/storage）
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
    # ── Batch 258 / B1-2：需求源信任域名白名单（凭据只发给白名单根域及其子域）──
    # 禁止子串判定：`"pingcode" in host` 会把 pingcode.attacker.tld 也判定为可信。
    # 自建实例（如内网 PingCode）把根域追加进来即可，逗号分隔。
    requirement_lanhu_domains: str = "lanhuapp.com"
    requirement_pingcode_domains: str = "pingcode.com"
    requirement_confluence_domains: str = "atlassian.net"
    # ── Batch 258 / B1-4：本地执行节点任务租约 ──
    execution_job_lease_seconds: int = 300   # 认领/心跳授予的租约时长；过期即回收为 pending
    execution_evidence_storage_dir: str = ""  # 执行证据落盘根目录；空 = backend/storage/execution-evidence

    # ── File paths (configurable for portability) ──
    workspace_root: str = ""      # empty = auto-detect from app/services/__file__
    skill_dir: str = ""           # test-case-design skill directory
    lanhu_mcp_dir: str = ""       # lanhu-mcp module directory
    data_dir: str = ""            # extracted data cache directory

    # ── SMTP (optional, for email notifications) ──
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True
    smtp_verify_cert: bool = True       # P1-S5b: SMTP TLS 证书验证开关
    smtp_ca_bundle: str = ""             # P1-S5b: 自定义 CA 证书包路径

    # ── API 执行超时（C205-2：慢接口超时配置化）──
    # 体育部分聚合接口（init_*/hot-players 等）>30s，默认 30s 会误判超时。
    # 环境变量 API_EXECUTION_TIMEOUT_SECONDS；默认 30s 保持兼容。
    api_execution_timeout_seconds: float = 30.0

    # ── Knowledge Center / RAG / Agent (M0 治理开关) ──
    # 安全默认：全部 OFF。知识入库为写路径的后台副作用，须由运维在评审脱敏与容量后
    # 显式开启（避免合入即在共享/测试环境自动激活对全量写操作的入库）。
    knowledge_ingest_enabled: bool = False       # M1 知识源入库总开关（默认关，显式开启）
    rag_enabled: bool = True                     # 是否启用 RAG 检索（M2）
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
    lanhu_capture_device_scale_factor: float = 2.0  # 截图 DPR，2x 小字更清晰（OCR 命中率）
    lanhu_capture_scroll_step_ratio: float = 0.85
    lanhu_capture_max_segments_per_page: int = 30
    lanhu_capture_wait_ms: int = 600
    schedule_stale_seconds: int = 1200  # Batch 164/C163-1：调度运行失联回收阈值（秒）
    lanhu_ocr_provider: str = "local"            # local/cloud/mock
    lanhu_ocr_command: str = '{python} -m app.services.lanhu_evidence.rapidocr_cli --image "{image}"'  # {python}/{image} 占位；默认内置 rapidocr CLI
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
    def ai_gateway_delegated(self) -> bool:
        """本进程是否把 LLM 调用委派给独立 ai-gateway。

        P0-4 凭据最小化后，`AI_GATEWAY_ROLE=remote` 的进程**不再持有**明文
        `AI_API_KEY`；判断「AI 是否可用」必须看委派链路是否配置完整，
        而不是看本地是否存有 Key（否则会误报「AI 功能将不可用」）。
        """
        return bool(
            self.ai_gateway_url
            and self.ai_gateway_token
            and self.ai_gateway_role != "gateway"
        )

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
            # P0-4 凭据最小化：remote 角色的进程不再持有明文 AI_API_KEY，
            # LLM 调用经 AI_GATEWAY_URL 委派给 ai-gateway。只有真正自己做推理的
            # 进程（embedded / gateway 角色）才要求本地 Key，否则会误报。
            if (
                self.ai_enabled
                and not self.ai_api_key
                and not self.ai_gateway_delegated
                and self.ai_gateway_role != "gateway"
            ):
                issues.append("AI_API_KEY 未设置，AI 功能将不可用")
            if not self.cookie_secure:
                issues.append("生产环境 cookie_secure 必须为 True（需要 HTTPS），否则 httpOnly cookie 以明文传输")
            if self.cookie_samesite == "none" and not self.cookie_secure:
                issues.append("SameSite=None 要求 cookie_secure=True，否则浏览器将拒绝 cookie")

        if self.environment == "development":
            if self.secret_key and self.secret_key.startswith("dev-"):
                issues.append("开发模式使用弱 SECRET_KEY（仅本地可接受）")

        return issues


settings = Settings()
