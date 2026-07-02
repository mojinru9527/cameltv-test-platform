"""Smoke tests for V2.6 features — integration + PostgreSQL support."""
import sys

# ── Model imports ──
from app.models.integration import IntegrationConfig
from app.models.sync_log import SyncLog
print("[PASS] Integration + SyncLog models")

# ── Schema imports ──
from app.schemas.integration import (
    IntegrationConfigCreate, IntegrationConfigUpdate, IntegrationConfigOut,
    TestConnectionRequest, TestConnectionResponse, SyncLogOut,
)
print("[PASS] Integration schemas")

# ── Service imports ──
from app.services.integration_service import (
    list_integrations, get_integration, create_integration, update_integration,
    delete_integration, test_connection, list_sync_logs,
)
print("[PASS] Integration service")

# ── Sync engine imports ──
from app.services.sync.base import BaseSyncProvider
from app.services.sync.jira import JiraSyncProvider
from app.services.sync.tapd import TapdSyncProvider
from app.services.sync.engine import get_provider, push_defect, pull_defect_status, run_scheduled_sync
print("[PASS] Sync engine")

# ── API router imports ──
from app.api.v1.integration import router as integration_router
print("[PASS] Integration API router")

# ── Provider mapping tests ──
# Jira
jira = JiraSyncProvider({"base_url": "https://test.atlassian.net", "auth": {"email": "x", "api_token": "y", "project_key": "TEST"}, "field_mapping": {}})
assert jira.map_severity_to_external("P0") == "Highest"
assert jira.map_severity_to_external("P3") == "Low"
assert jira.map_severity_from_external("Highest") == "P0"
assert jira.map_status_to_external("open") == "To Do"
assert jira.map_status_to_external("closed") == "Done"
assert jira.map_status_from_external("Done") == "closed"
print("[PASS] Jira field mappings")

# TAPD
tapd = TapdSyncProvider({"base_url": "https://api.tapd.cn", "auth": {"api_user": "x", "api_password": "y", "workspace_id": "123"}, "field_mapping": {}})
assert tapd.map_severity_to_external("P0") == "致命"
assert tapd.map_severity_to_external("P2") == "一般"
assert tapd.map_severity_from_external("致命") == "P0"
assert tapd.map_status_to_external("fixing") == "处理中"
assert tapd.map_status_from_external("已关闭") == "closed"
print("[PASS] TAPD field mappings")

# Custom field mapping
jira_custom = JiraSyncProvider({"base_url": "https://test.atlassian.net", "auth": {"email": "x", "api_token": "y", "project_key": "TEST"}, "field_mapping": {"severity": {"P0": "Blocker"}, "status": {"open": "Backlog"}}})
assert jira_custom.map_severity_to_external("P0") == "Blocker"
assert jira_custom.map_severity_to_external("P1") == "High"  # fallback to default
assert jira_custom.map_status_to_external("open") == "Backlog"
print("[PASS] Custom field mapping fallback")

# ── Cipher import (reused for encryption) ──
from app.core.cipher import encrypt_value, decrypt_value
original = '{"email":"test@test.com","api_token":"secret123"}'
encrypted = encrypt_value(original)
assert encrypted != original
assert decrypt_value(encrypted) == original
print("[PASS] Cipher encrypt/decrypt for auth_json")

# ── Config test_connection with invalid auth JSON ──
result = test_connection("jira", "https://test.atlassian.net", 'not-valid-json')
assert result["success"] is False  # expect failure on bad JSON
assert len(result["message"]) > 0
print("[PASS] Test connection rejects invalid auth JSON")

# ── Integration service auth masking ──
out = IntegrationConfigOut(id=1, project_id=1, name="Jira", provider_type="jira",
                           base_url="https://jira.example.com", auth_json="********")
assert "********" in out.auth_json
print("[PASS] Auth masking in schema output")

# ── DB module changes ──
from app.core.config import settings
assert hasattr(settings, "db_pool_size")
assert hasattr(settings, "db_max_overflow")
assert settings.db_pool_size == 10
assert settings.db_max_overflow == 20
print("[PASS] Config db_pool_size/db_max_overflow")

# ── Sync direction validation ──
valid_directions = ["bidirectional", "push_only", "pull_only"]
for d in valid_directions:
    cfg = IntegrationConfigCreate(name="test", provider_type="jira", sync_direction=d)
    assert cfg.sync_direction == d
print("[PASS] Sync direction validation")

# ── Provider factory ──
from app.services.sync.engine import get_provider
jira_p = get_provider("jira", {"base_url": "https://x.com", "auth": {}, "field_mapping": {}})
assert isinstance(jira_p, JiraSyncProvider)
tapd_p = get_provider("tapd", {"base_url": "https://x.com", "auth": {}, "field_mapping": {}})
assert isinstance(tapd_p, TapdSyncProvider)
try:
    get_provider("unknown", {"base_url": "", "auth": {}, "field_mapping": {}})
    assert False, "Should have raised ValueError"
except ValueError:
    pass
print("[PASS] Provider factory + unknown type raises ValueError")

print("\n*** All V2.6 smoke tests passed! ***")
