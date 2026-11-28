"""V1.6.2 FIX-009 凭据扫描（只读发现与分级，不自动修改）。

扫描范围
--------
- 全部 tracked 文件 **加** 工作区新增/修改/未跟踪文件（`git status --porcelain`），
  不再只扫旧文件；可选扫描近期 git 历史 diff；
- 覆盖 Playwright ``.fill("...")`` / ``.type("...")``、``send_keys``、赋值型
  ``password/passwd/secret/token/api_key``（py/js/yaml/json/md）、
  ``Authorization/Bearer/Cookie``、URL basic auth、带密码 DSN、私钥与云凭据；
- Markdown 中的明文口令同样扫描（旧扫描器把 ``docs/`` 整体排除，导致文档明文漏检）。

分级与阻断策略
--------------
- ``potential-secret`` / ``weak-default`` > 0 → ``status=BLOCK`` 且退出码非 0；
  不得再把 weak-default 报成 CLEAN；
- ``known-test-secret``：tests/fixtures/examples 中的测试夹具，单独计数、默认不阻断；
- ``approved-exception``：必须来自治理例外清单（owner/reason/scope/expires_at/reviewer），
  缺失或过期不算已批准；
- 所有 finding 只输出脱敏值（``***`` + 长度），绝不写入原始秘密。

输出字段
--------
``potential_secret_count``、``weak_default_count``、``known_test_secret_count``、
``approved_exception_count``、``placeholder_count``、``scan_commit_sha``（=当前 git HEAD
40 位）、``scan_started_at`` / ``scan_finished_at``、``scanned_paths``、
``excluded_paths``（含理由）、``findings``（脱敏）、``history_findings``。

用法
----
    python scripts/aiqe/scan_credentials.py --output docs/aiqe/v1.6/evidence/credential-scan.json
    python scripts/aiqe/scan_credentials.py --report-only     # 只出证据，不阻断
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from validators.common import is_sha, parse_time  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "docs/aiqe/v1.6/evidence/credential-scan.json"
DEFAULT_EXCEPTIONS = ROOT / "docs/aiqe/v1.6/governance/credential-exceptions.json"
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_FINDINGS = 500
WEAK_DEFAULTS = {
    "admin",
    "admin123",
    "admin123456",
    "123456",
    "12345678",
    "111111",
    "000000",
    "password",
    "password1",
    "passwd",
    "qwerty",
    "root",
    "postgres",
    "test",
    "test123",
    "changeme",
    "cameltv",
    "cameltv_test",
}
WEAK_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "postgres", "mysql", "db", "database", "redis", "host"}
PLACEHOLDERS = (
    "***",
    "${",
    "{{",
    "<",
    "your_",
    "your-",
    "example",
    "changeme",
    "change-me",
    "change_me",
    "redacted",
    "placeholder",
    "dummy",
    "fake",
    "probe",
    "invalid",
    "not-real",
    "not_real",
    "self-test",
    "xxx",
    "...",
    "******",
)
BOOLEAN_VALUES = {"true", "false", "none", "null", "yes", "no", "on", "off", "enabled", "disabled"}
TYPE_VALUES = {
    "string",
    "str",
    "int",
    "float",
    "bool",
    "boolean",
    "dict",
    "list",
    "bytes",
    "number",
    "object",
    "array",
    "any",
    "optional",
    "secretstr",
    "apitoken",
    "passwordstr",
}
#: 凭据扫描器/自测脚本自身的模式与样例，不是仓库秘密。
SCANNER_SELF_PATHS = (
    "scripts/aiqe/scan_credentials.py",
    "scripts/git/scan-common-bugs.ps1",
    "scripts/git/test-secret-scan.sh",
)
EXAMPLE_DSN_USERS = {"user", "username", "myuser", "ro_user", "root_user"}
EXAMPLE_DSN_PASSWORDS = {"pass", "password", "pwd", "mypass", "secret", "change-me", "changeme"}
EXAMPLE_DSN_HOSTS = {"host", "my-pg-host", "db.example", "example.com", "dbname", "your-host"}

#: 排除项必须带理由，报告里会原样输出。
EXCLUDED_PREFIXES: tuple[tuple[str, str], ...] = (
    (".git/", "git 内部对象，不是工作树源码"),
    ("node_modules/", "第三方依赖目录，不属于本仓库代码"),
    (".venv/", "Python 虚拟环境"),
    ("venv/", "Python 虚拟环境"),
    ("__pycache__/", "Python 字节码缓存"),
    ("test-platform-v2/frontend/dist/", "前端构建产物"),
    ("test-platform-v2/frontend/build/", "前端构建产物"),
    ("dist/", "构建产物"),
    ("build/", "构建产物"),
    ("htmlcov/", "覆盖率报告产物"),
)
EXCLUDED_SUFFIXES: tuple[tuple[str, str], ...] = (
    (".png", "二进制图片"),
    (".jpg", "二进制图片"),
    (".jpeg", "二进制图片"),
    (".gif", "二进制图片"),
    (".webp", "二进制图片"),
    (".ico", "二进制图标"),
    (".pdf", "二进制文档"),
    (".woff", "字体文件"),
    (".woff2", "字体文件"),
    (".ttf", "字体文件"),
    (".otf", "字体文件"),
    (".zip", "二进制压缩包"),
    (".gz", "二进制压缩包"),
    (".tar", "二进制压缩包"),
    (".whl", "二进制产物"),
    (".pyc", "Python 字节码"),
    (".pyo", "Python 字节码"),
    (".so", "二进制库"),
    (".dll", "二进制库"),
    (".exe", "二进制可执行文件"),
    (".db", "本地数据库文件"),
    (".sqlite", "本地数据库文件"),
    (".sqlite3", "本地数据库文件"),
    (".mp4", "二进制视频"),
    (".jar", "二进制归档"),
    (".class", "编译产物"),
    (".min.js", "压缩后的前端产物"),
    (".map", "sourcemap 生成物"),
    (".lock", "依赖锁文件（生成物）"),
    ("-lock.json", "依赖锁文件（生成物）"),
    ("pnpm-lock.yaml", "依赖锁文件（生成物）"),
    ("package-lock.json", "依赖锁文件（生成物）"),
    ("yarn.lock", "依赖锁文件（生成物）"),
)
EXCLUDED_NAMES: tuple[tuple[str, str], ...] = (
    ("credential-scan.json", "本扫描器自身的输出，避免把脱敏记录再当命中"),
)
MARKDOWN_SUFFIXES = (".md", ".mdx", ".rst", ".txt")

HIGH_CONFIDENCE: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA |PGP |ENCRYPTED )?PRIVATE KEY-----")),
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("azure_storage_key", re.compile(r"(?i)\bAccountKey=[A-Za-z0-9+/=]{20,}")),
    ("gcp_private_key_id", re.compile(r'"private_key_id"\s*:\s*"[0-9a-f]{20,}"')),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("npm_token", re.compile(r"\bnpm_[A-Za-z0-9]{36}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("llm_api_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("jwt_token", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
)
DSN = re.compile(
    r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp|mssql)://[^:\s/@]+:[^@\s]{3,}@[^/\s\"'<>]+"
)
URL_BASIC_AUTH = re.compile(r"\bhttps?://[^/\s:@]{1,64}:(?!\$\{|\{\{|<)[^/\s:@]{3,128}@[^/\s\"'<>]+")
ASSIGNED = re.compile(
    r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|apikey|access[_-]?key|client[_-]?secret|private[_-]?key)\b"
    r"\s*[:=]\s*[\"']([A-Za-z0-9_./+=\-]{4,256})[\"']"
)
YAML_ASSIGNED = re.compile(
    r"(?im)^\s*(password|passwd|pwd|secret|token|api[_-]?key)\s*:\s*([A-Za-z0-9_./+=\-]{4,256})\s*$"
)
ENV_ASSIGNED = re.compile(
    r"(?m)^\s*(?:export\s+)?([A-Z][A-Z0-9_]*(?:PASSWORD|PASSWD|SECRET|TOKEN|API[_-]?KEY|ACCESS[_-]?KEY)[A-Z0-9_]*)"
    r"\s*=\s*([^\s\"'#]{6,256})"
)
AUTH_HEADER = re.compile(
    r"(?i)\b(?:authorization|proxy-authorization)\b[\"']?\s*[:=]\s*[\"']?(?:Bearer|Basic|Token)\s+"
    r"([A-Za-z0-9\-._~+/=]{8,})"
)
BEARER = re.compile(r"(?i)\bBearer\s+([A-Za-z0-9\-._~+/=]{20,})")
COOKIE = re.compile(r"(?i)\b(?:set-)?cookie\b\s*[:=]\s*[\"']([^\"'\n]{8,300})[\"']")
FORM_FILL_VALUE = re.compile(
    r"\.(?:fill|type)\(\s*[\"'][^\"'\n]{1,256}[\"']\s*,\s*[\"']([^\"'\n]{2,256})[\"']"
)
FORM_FILL_SINGLE = re.compile(r"\.(?:fill|type)\(\s*[\"']([^\"'\n]{2,256})[\"']\s*\)")
SEND_KEYS = re.compile(r"\.(?:send_keys|sendKeys)\(\s*[\"']([^\"'\n]{2,256})[\"']")
MD_SECRET = re.compile(
    r"(?:密码|口令|password|passwd|pwd)\s*(?:[:：=]|\s)\s*[`'\"“]?([A-Za-z0-9!@#$%^&*._+\-]{4,64})"
)
CREDENTIAL_CONTEXT = (
    "password",
    "passwd",
    "pwd",
    "密码",
    "口令",
    "token",
    "secret",
    "api_key",
    "apikey",
    "username",
    "user_name",
    "用户名",
    "账号",
    "账户",
    "手机号",
    "account",
)
NON_CREDENTIAL_CONTEXT = ("captcha", "验证码", "ocr", "search", "keyword")
DOC_LIKE_MARKERS = (
    "re.compile",
    "pattern",
    "redact",
    "canary",
    "示例",
    "模板",
    "[A-Z0-9",
    "…",
    "sk-[A-Za-z0-9]",
    "PRIVATE KEY-\\n",
)
EXCEPTION_REQUIRED = ("path", "owner", "reason", "scope", "expires_at", "reviewer")


def _now() -> datetime:
    return datetime.now(UTC)


def is_config_file(path: str) -> bool:
    """向后兼容：配置类文件（.env/yml/yaml/deploy json）。"""
    name = path.rsplit("/", 1)[-1]
    if name.startswith(".env"):
        return True
    if name.endswith((".yml", ".yaml")):
        return True
    return path.startswith("deploy/") and name.endswith(".json")


def exclusion_reason(path: str) -> str:
    """返回排除理由；未排除返回空串（报告用的唯一判定入口）。"""
    normalized = path.replace("\\", "/")
    name = normalized.rsplit("/", 1)[-1]
    for prefix, reason in EXCLUDED_PREFIXES:
        if normalized.startswith(prefix) or f"/{prefix}" in normalized:
            return reason
    for suffix, reason in EXCLUDED_SUFFIXES:
        if normalized.endswith(suffix):
            return reason
    for excluded_name, reason in EXCLUDED_NAMES:
        if name == excluded_name:
            return reason
    return ""


def skip_path(path: str) -> bool:
    """向后兼容：该路径是否不参与内容扫描。"""
    return bool(exclusion_reason(path))


def _is_test_path(path: str) -> bool:
    normalized = f"/{path.replace(chr(92), '/')}"
    name = normalized.rsplit("/", 1)[-1]
    return (
        "/tests/" in normalized
        or "/test/" in normalized
        or "/__tests__/" in normalized
        or "/fixtures/" in normalized
        or "/examples/" in normalized
        or name.startswith("test_")
        or name.startswith("test-")
        or ".test." in name
        or ".spec." in name
        or name == "conftest.py"
    )


def mask_value(value: str) -> str:
    """脱敏：短值只保留长度，长值首尾各两位。"""
    length = len(value)
    if length <= 8:
        return f"*** (len={length})"
    return f"{value[:2]}***{value[-2:]}(len={length})"


def _dsn_parts(value: str) -> tuple[str, str, str]:
    try:
        parts = urlsplit(value)
    except ValueError:
        return "", "", ""
    return (
        unquote(parts.username or ""),
        unquote(parts.password or ""),
        (parts.hostname or "").lower(),
    )


def _is_doc_like(line: str) -> bool:
    return any(marker in line for marker in DOC_LIKE_MARKERS)


def _looks_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    if not lowered:
        return True
    return any(token in lowered for token in PLACEHOLDERS)


def _looks_weak(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered in WEAK_DEFAULTS:
        return True
    return bool(re.fullmatch(r"\d{4,8}", lowered))


def _is_scanner_self(path: str) -> bool:
    return path.replace("\\", "/") in SCANNER_SELF_PATHS


def _is_example_path(path: str) -> bool:
    lowered = f"/{path.replace(chr(92), '/')}".lower()
    return any(marker in lowered for marker in (".example", ".sample", ".template"))


def _looks_like_type(value: str, line: str) -> bool:
    """类型注解 / 常量名不是秘密（如 token: "ApiToken"、SECRET = "SECRET"）。"""
    lowered = value.strip().lower()
    if lowered in TYPE_VALUES or lowered in BOOLEAN_VALUES:
        return True
    if re.fullmatch(r"[A-Z][A-Za-z0-9]{0,40}", value) and value.isalnum():
        return True
    key = re.split(r"[:=]", line, maxsplit=1)[0].strip().strip('"\'').upper()
    return bool(key) and key == value.strip().upper()


def _looks_like_code_expression(value: str) -> bool:
    """赋值右侧是函数/命令调用时不是字面量秘密（如 New-RandomProfileSecret）。"""
    text = value.strip()
    if any(token in text for token in ("(", ")", "$", "`", "::", "New-", "Get-", "Read-")):
        return True
    return bool(re.fullmatch(r"[A-Z][A-Za-z]+(?:-[A-Za-z]+)+", text)) and not any(
        char.isdigit() for char in text
    )


def _looks_like_selector(value: str) -> bool:
    text = value.strip()
    return text.startswith(("#", ".", "[", "//", "xpath=", "role=", "text=")) or text in {
        "input",
        "textarea",
        "button",
    }


def classify(kind: str, value: str, path: str, line: str) -> str:
    """分级：placeholder / known-test-secret / weak-default / potential-secret。"""
    lowered = value.strip().lower()
    if _is_scanner_self(path) or _is_example_path(path):
        return "placeholder"
    if (
        _looks_placeholder(value)
        or _is_doc_like(line)
        or _looks_like_type(value, line)
        or _looks_like_code_expression(value)
    ):
        return "placeholder"
    if kind in {"dsn_with_password", "url_basic_auth"}:
        user, password, host = _dsn_parts(value)
        if _is_test_path(path):
            return "known-test-secret"
        if not user or not password:
            return "placeholder"
        if (
            user.lower() in EXAMPLE_DSN_USERS
            or password.lower() in EXAMPLE_DSN_PASSWORDS
            or host in EXAMPLE_DSN_HOSTS
        ):
            return "placeholder"
        if host in WEAK_HOSTS or _looks_weak(password):
            return "weak-default"
        return "potential-secret"
    if _is_test_path(path):
        return "known-test-secret"
    if _looks_weak(value):
        return "weak-default"
    if kind not in {"private_key"} and any(
        token in lowered for token in ("test", "dummy", "fake", "sample", "mock")
    ):
        return "known-test-secret"
    return "potential-secret"


def _match_exception(path: str, kind: str, exceptions: list[dict]) -> dict | None:
    for entry in exceptions:
        pattern = str(entry.get("path") or "")
        if not pattern or not fnmatch.fnmatch(path, pattern):
            continue
        allowed_kinds = entry.get("kinds") or entry.get("kind") or "*"
        if isinstance(allowed_kinds, str):
            allowed = [item.strip() for item in allowed_kinds.split(",")]
        else:
            allowed = [str(item) for item in allowed_kinds]
        if "*" in allowed or kind in allowed:
            return entry
    return None


def _finding(
    path: str,
    line_number: int,
    kind: str,
    matched: str,
    value: str,
    source: str,
    exceptions: list[dict] | None = None,
) -> dict:
    classification = classify(kind, value, path, source)
    approved = _match_exception(path, kind, exceptions or []) if classification in {
        "potential-secret",
        "weak-default",
    } else None
    if approved is not None:
        classification = "approved-exception"
    finding = {
        "file": path,
        "line": line_number,
        "kind": kind,
        "classification": classification,
        "masked": mask_value(matched),
        "length": len(matched),
    }
    if approved is not None:
        finding["exception_owner"] = str(approved.get("owner") or "")
        finding["exception_expires_at"] = str(approved.get("expires_at") or "")
    return finding


def _fill_kind(line: str) -> tuple[str, bool]:
    """判断 .fill/.send_keys 的上下文是否与凭据相关。"""
    lowered = line.lower()
    if any(token in lowered for token in NON_CREDENTIAL_CONTEXT) and not any(
        token in lowered for token in ("password", "passwd", "pwd", "密码", "token", "secret")
    ):
        return "form_input", False
    if any(token in lowered for token in ("password", "passwd", "pwd", "密码", "口令")):
        return "hardcoded_password", True
    if any(token in lowered for token in ("username", "user_name", "用户名", "账号", "账户", "手机号")):
        return "hardcoded_account", True
    if any(token in lowered for token in CREDENTIAL_CONTEXT):
        return "hardcoded_credential", True
    return "form_input", False


def _spans_overlap(span: tuple[int, int], spans: list[tuple[int, int]]) -> bool:
    return any(not (span[1] <= start or span[0] >= end) for start, end in spans)


def scan_text(
    text: str,
    *,
    path: str = "",
    config_only: bool = False,
    exceptions: list[dict] | None = None,
) -> list[dict]:
    """扫描一段文本，返回脱敏后的 findings（不返回原始值）。"""
    if skip_path(path):
        return []
    findings: list[dict] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if _is_doc_like(line):
            continue
        covered: list[tuple[int, int]] = []
        for kind, pattern in HIGH_CONFIDENCE:
            for match in pattern.finditer(line):
                covered.append(match.span())
                findings.append(
                    _finding(
                        path,
                        line_number,
                        kind,
                        match.group(0),
                        match.group(0),
                        line,
                        exceptions,
                    )
                )
        for match in DSN.finditer(line):
            covered.append(match.span())
            findings.append(
                _finding(
                    path,
                    line_number,
                    "dsn_with_password",
                    match.group(0),
                    match.group(0),
                    line,
                    exceptions,
                )
            )
        for match in URL_BASIC_AUTH.finditer(line):
            if _spans_overlap(match.span(), covered):
                continue
            covered.append(match.span())
            findings.append(
                _finding(
                    path,
                    line_number,
                    "url_basic_auth",
                    match.group(0),
                    match.group(0),
                    line,
                    exceptions,
                )
            )
        for match in ASSIGNED.finditer(line):
            covered.append(match.span())
            findings.append(
                _finding(
                    path,
                    line_number,
                    "assigned_secret",
                    match.group(0),
                    match.group(2),
                    line,
                    exceptions,
                )
            )
        for match in YAML_ASSIGNED.finditer(line):
            if _spans_overlap(match.span(), covered):
                continue
            covered.append(match.span())
            findings.append(
                _finding(
                    path,
                    line_number,
                    "yaml_secret",
                    match.group(0),
                    match.group(2),
                    line,
                    exceptions,
                )
            )
        for match in ENV_ASSIGNED.finditer(line):
            if _spans_overlap(match.span(), covered):
                continue
            covered.append(match.span())
            findings.append(
                _finding(
                    path,
                    line_number,
                    "env_secret",
                    match.group(0),
                    match.group(2),
                    line,
                    exceptions,
                )
            )
        for match in AUTH_HEADER.finditer(line):
            covered.append(match.span())
            findings.append(
                _finding(
                    path,
                    line_number,
                    "authorization_header",
                    match.group(0),
                    match.group(1),
                    line,
                    exceptions,
                )
            )
        for match in BEARER.finditer(line):
            if _spans_overlap(match.span(), covered):
                continue
            covered.append(match.span())
            findings.append(
                _finding(
                    path,
                    line_number,
                    "bearer_token",
                    match.group(0),
                    match.group(1),
                    line,
                    exceptions,
                )
            )
        for match in COOKIE.finditer(line):
            covered.append(match.span())
            findings.append(
                _finding(
                    path,
                    line_number,
                    "cookie",
                    match.group(0),
                    match.group(1),
                    line,
                    exceptions,
                )
            )
        for pattern in (FORM_FILL_VALUE, FORM_FILL_SINGLE, SEND_KEYS):
            for match in pattern.finditer(line):
                if pattern is FORM_FILL_SINGLE and _looks_like_selector(match.group(1)):
                    continue
                kind, credential = _fill_kind(line)
                if not credential:
                    continue
                findings.append(
                    _finding(
                        path,
                        line_number,
                        kind,
                        match.group(0),
                        match.group(1),
                        line,
                        exceptions,
                    )
                )
        if not path or path.endswith(MARKDOWN_SUFFIXES):
            for match in MD_SECRET.finditer(line):
                if _spans_overlap(match.span(), covered):
                    continue
                candidate = match.group(1)
                if candidate.lower() in {"is", "was", "not"}:
                    continue
                # 明文口令通常含数字；纯英文单词多为文档用词，避免把说明文字当秘密。
                if not re.search(r"\d", candidate) and candidate.lower() not in WEAK_DEFAULTS:
                    continue
                findings.append(
                    _finding(
                        path,
                        line_number,
                        "markdown_plaintext_password",
                        match.group(0),
                        candidate,
                        line,
                        exceptions,
                    )
                )
    return findings


def _git(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, check=False
        )
    except OSError:  # pragma: no cover - git 不可用
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.decode("utf-8", errors="replace")


def scan_commit_sha() -> str:
    """当前扫描 SHA：必须等于被扫描分支的 git HEAD（40 位小写）。"""
    sha = _git("rev-parse", "HEAD").strip().lower()
    return sha if is_sha(sha) else ""


def _tracked_paths() -> list[str]:
    raw = _git("ls-files", "-z")
    return [name for name in raw.split("\0") if name]


def _dirty_paths() -> list[str]:
    """工作区新增/修改/未跟踪文件（不能只扫已提交的旧文件）。"""
    raw = _git("status", "--porcelain", "-z", "--untracked-files=all")
    tokens = raw.split("\0")
    paths: list[str] = []
    index = 0
    while index < len(tokens):
        entry = tokens[index]
        index += 1
        if not entry:
            continue
        status = entry[:2]
        path = entry[3:] if len(entry) > 3 else ""
        if status[:1] in {"R", "C"} or status[1:2] in {"R", "C"}:
            index += 1  # 下一个 token 是 rename 前的旧路径
        if path and path not in paths:
            paths.append(path)
    return paths


def _candidate_paths() -> tuple[list[str], list[str]]:
    tracked = _tracked_paths()
    dirty = _dirty_paths()
    extra = [path for path in dirty if path not in tracked]
    return sorted(set(tracked) | set(dirty)), extra


def scan_worktree(exceptions: list[dict] | None = None) -> dict:
    files, untracked = _candidate_paths()
    aggregated: dict[tuple[str, str, str, str], dict] = {}
    scanned: list[str] = []
    for rel in files:
        normalized = rel.replace("\\", "/")
        if skip_path(normalized):
            continue
        path = ROOT / rel
        try:
            if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
                continue
            raw = path.read_bytes()
            if b"\x00" in raw[:4096]:
                continue
            text = raw.decode("utf-8", errors="replace")
        except OSError:
            continue
        scanned.append(normalized)
        for finding in scan_text(text, path=normalized, exceptions=exceptions):
            key = (
                finding["file"],
                finding["kind"],
                finding["masked"],
                finding["classification"],
            )
            if key in aggregated:
                aggregated[key]["occurrences"] += 1
                continue
            item = dict(finding)
            item["occurrences"] = 1
            aggregated[key] = item
    return {
        "findings": list(aggregated.values()),
        "scanned_paths": scanned,
        "untracked_or_modified": sorted(untracked),
    }


def scan_history(limit: int, exceptions: list[dict] | None = None) -> list[dict]:
    if limit <= 0:
        return []
    raw = _git(
        "log",
        "-p",
        "--all",
        f"-n{limit}",
        "--format=commit %H",
        "--unified=0",
    )
    findings: list[dict] = []
    commit = ""
    current_path = ""
    for line in raw.splitlines():
        if line.startswith("commit "):
            commit = line.split(" ", 1)[1].strip()
            continue
        if line.startswith("+++ "):
            current_path = line[4:].strip()
            if current_path.startswith("b/"):
                current_path = current_path[2:]
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        body = line[1:]
        if _is_doc_like(body):
            continue
        for kind, pattern in HIGH_CONFIDENCE:
            for match in pattern.finditer(body):
                item = _finding(
                    current_path or "<history>",
                    0,
                    kind,
                    match.group(0),
                    match.group(0),
                    body,
                    exceptions,
                )
                if item["classification"] == "placeholder":
                    continue
                item["commit"] = commit
                item["in_history"] = True
                findings.append(item)
    return findings


def load_exceptions(path: str | Path | None = None) -> tuple[list[dict], list[str]]:
    """读取治理例外清单；缺文件=无例外，非法/过期条目不算已批准。"""
    target = Path(path) if path else DEFAULT_EXCEPTIONS
    if not target.exists():
        return [], []
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [], [f"例外清单不可读: {exc}"]
    entries = payload.get("exceptions") if isinstance(payload, dict) else payload
    if not isinstance(entries, list):
        return [], ["例外清单必须是 {exceptions: [...]} 或数组"]
    valid: list[dict] = []
    errors: list[str] = []
    now = _now()
    for index, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            errors.append(f"第 {index} 条例外不是 object")
            continue
        missing = [field for field in EXCEPTION_REQUIRED if not str(entry.get(field) or "").strip()]
        if missing:
            errors.append(f"第 {index} 条例外缺少 {', '.join(missing)}（不得算已批准）")
            continue
        expires = parse_time(entry.get("expires_at"))
        if expires is None:
            errors.append(f"第 {index} 条例外 expires_at 不是合法时间")
            continue
        if expires < now:
            errors.append(f"第 {index} 条例外已过期（{entry.get('expires_at')}）")
            continue
        valid.append(entry)
    return valid, errors


def summarize(findings: list[dict]) -> dict:
    counts = {
        "potential_secret_count": 0,
        "weak_default_count": 0,
        "known_test_secret_count": 0,
        "approved_exception_count": 0,
        "placeholder_count": 0,
    }
    mapping = {
        "potential-secret": "potential_secret_count",
        "weak-default": "weak_default_count",
        "known-test-secret": "known_test_secret_count",
        "approved-exception": "approved_exception_count",
        "placeholder": "placeholder_count",
    }
    for item in findings:
        key = mapping.get(str(item.get("classification")))
        if key:
            counts[key] += 1
    return counts


def _status_of(counts: dict, history_counts: dict) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if counts["potential_secret_count"]:
        reasons.append(f"potential_secret_count={counts['potential_secret_count']}（必须轮换/移除）")
    if counts["weak_default_count"]:
        reasons.append(
            f"weak_default_count={counts['weak_default_count']}（弱默认值阻断合并，需修复或治理例外）"
        )
    if history_counts["potential_secret_count"]:
        reasons.append(
            f"history potential_secret_count={history_counts['potential_secret_count']}"
        )
    return ("BLOCK" if reasons else "CLEAN"), reasons


def build_report(
    *,
    output: Path = DEFAULT_OUTPUT,
    history_limit: int = 200,
    exceptions_path: str | Path | None = None,
) -> dict:
    started = _now()
    exceptions, exception_errors = load_exceptions(exceptions_path)
    worktree = scan_worktree(exceptions)
    history = scan_history(history_limit, exceptions)
    finished = _now()
    counts = summarize(worktree["findings"])
    history_counts = summarize(history)
    status, reasons = _status_of(counts, history_counts)
    excluded = [{"path": path, "reason": reason} for path, reason in EXCLUDED_PREFIXES]
    excluded += [{"path": f"*{suffix}", "reason": reason} for suffix, reason in EXCLUDED_SUFFIXES]
    excluded += [{"path": f"*{name}", "reason": reason} for name, reason in EXCLUDED_NAMES]
    findings = [
        item for item in worktree["findings"] if item["classification"] != "placeholder"
    ]
    commit_sha = scan_commit_sha()
    if not commit_sha:
        status = "BLOCK"
        reasons.append("无法获取 git HEAD，scan_commit_sha 为空（不能证明扫描的是当前 SHA）")
    return {
        "schema_version": "2.0",
        "artifact_kind": "credential-scan",
        "generated_at": finished.isoformat(),
        "scan_commit_sha": commit_sha,
        "scan_started_at": started.isoformat(),
        "scan_finished_at": finished.isoformat(),
        "status": status,
        "status_reasons": reasons,
        "policy": {
            "blocking_counts": ["potential_secret_count", "weak_default_count"],
            "history_blocking": "history potential-secret",
            "known_test_secrets_blocking": False,
            "note": "默认 potential/weak > 0 或历史命中即 BLOCK；weak-default 不得混入 CLEAN。",
        },
        "potential_secret_count": counts["potential_secret_count"],
        "weak_default_count": counts["weak_default_count"],
        "known_test_secret_count": counts["known_test_secret_count"],
        "approved_exception_count": counts["approved_exception_count"],
        "placeholder_count": counts["placeholder_count"],
        "history_potential_secret_count": history_counts["potential_secret_count"],
        "summary": counts,
        "history_summary": history_counts,
        "scope": {
            "scanned_file_count": len(worktree["scanned_paths"]),
            "scanned_paths": worktree["scanned_paths"],
            "untracked_or_modified_paths": worktree["untracked_or_modified"],
            "excluded_paths": excluded,
            "max_file_bytes": MAX_FILE_BYTES,
            "history_commits_limited": history_limit,
            "includes_worktree_changes": True,
        },
        "exceptions": {
            "path": str(exceptions_path or DEFAULT_EXCEPTIONS),
            "valid_count": len(exceptions),
            "errors": exception_errors,
        },
        "findings": findings[:MAX_FINDINGS],
        "findings_truncated": len(findings) > MAX_FINDINGS,
        "history_findings": history[:MAX_FINDINGS],
        "output": str(output),
        "note": (
            "只读扫描；finding 仅记录脱敏值与长度，绝不记录原始秘密。"
            "potential-secret 需轮换，weak-default 需修复或走治理例外；"
            "本文件不替代生产轮换证据。"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):  # pragma: no cover
            pass
    parser = argparse.ArgumentParser(description="V1.6.2 仓库/工作区/历史凭据扫描（只读）")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--history-limit", type=int, default=200)
    parser.add_argument("--exceptions", default=str(DEFAULT_EXCEPTIONS))
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="只生成证据，退出码恒为 0（CI 门禁不得使用该开关）",
    )
    args = parser.parse_args(argv)

    target = Path(args.output)
    report = build_report(
        output=target,
        history_limit=args.history_limit,
        exceptions_path=args.exceptions,
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "scan_commit_sha": report["scan_commit_sha"],
                "potential_secret_count": report["potential_secret_count"],
                "weak_default_count": report["weak_default_count"],
                "known_test_secret_count": report["known_test_secret_count"],
                "approved_exception_count": report["approved_exception_count"],
                "scanned_file_count": report["scope"]["scanned_file_count"],
                "status_reasons": report["status_reasons"],
            },
            ensure_ascii=False,
        )
    )
    if args.report_only:
        return 0
    return 0 if report["status"] == "CLEAN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
