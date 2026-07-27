"""TAPD (Tencent Agile Product Development) sync provider."""
from __future__ import annotations

from base64 import b64encode

from app.services.sync.base import BaseSyncProvider


class TapdSyncProvider(BaseSyncProvider):
    """Sync provider for TAPD REST API."""

    DEFAULT_SEVERITY_MAP = {"P0": "致命", "P1": "严重", "P2": "一般", "P3": "提示"}
    DEFAULT_SEVERITY_REVERSE = {"致命": "P0", "严重": "P1", "一般": "P2", "提示": "P3"}
    DEFAULT_STATUS_MAP = {
        "open": "新建", "confirmed": "已确认", "fixing": "处理中",
        "pending_review": "已解决", "closed": "已关闭", "rejected": "已拒绝",
    }
    DEFAULT_STATUS_REVERSE = {
        "新建": "open", "已确认": "confirmed", "处理中": "fixing",
        "已解决": "pending_review", "已关闭": "closed", "已拒绝": "rejected",
    }

    def _auth_header(self) -> dict:
        api_user = self.auth.get("api_user", "")
        api_password = self.auth.get("api_password", "")
        raw = f"{api_user}:{api_password}".encode("utf-8")
        return {"Authorization": f"Basic {b64encode(raw).decode('utf-8')}"}

    def _workspace_id(self) -> str:
        return self.auth.get("workspace_id", "")

    async def test_connection(self) -> tuple[bool, str]:
        try:
            resp = await self._request(
                "GET", "/workspaces/projects",
                headers={**self._auth_header(), "Accept": "application/json"},
            )
            data = resp.json()
            if isinstance(data, dict) and data.get("status") == 1:
                projects = data.get("data", [])
                return True, f"Connected to TAPD. Found {len(projects)} project(s)"
            return False, f"Unexpected response: {resp.text[:200]}"
        except Exception as e:
            return False, str(e)

    async def push_defect(self, defect: dict) -> tuple[bool, str, str]:
        """Create a new TAPD bug from a CamelTv defect."""
        try:
            workspace_id = self._workspace_id()
            if not workspace_id:
                return False, "", "Missing workspace_id in auth config"

            severity = self.map_severity_to_external(defect.get("severity", "P2"))
            status_name = self.map_status_to_external(defect.get("status", "open"))

            payload = {
                "workspace_id": workspace_id,
                "title": defect.get("title", ""),
                "description": defect.get("description", ""),
                "severity": severity,
                "status": status_name,
            }

            headers = {
                **self._auth_header(),
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            }

            resp = await self._request("POST", "/bugs", data=payload, headers=headers)
            data = resp.json()

            if isinstance(data, dict) and data.get("status") == 1:
                bug_data = data.get("data", {}).get("Bug", {})
                bug_id = bug_data.get("id", "")
                bug_url = f"https://www.tapd.cn/{workspace_id}/bugtrace/bugs/view/{bug_id}" if bug_id else ""
                return True, str(bug_id), bug_url
            return False, "", f"TAPD error: {resp.text[:500]}"
        except Exception as e:
            return False, "", str(e)

    async def pull_defect(self, external_id: str) -> tuple[bool, dict | None, str]:
        """Fetch a TAPD bug by ID."""
        try:
            workspace_id = self._workspace_id()
            params = {"workspace_id": workspace_id, "id": external_id}
            headers = {**self._auth_header(), "Accept": "application/json"}

            resp = await self._request("GET", "/bugs", params=params, headers=headers)
            data = resp.json()

            if isinstance(data, dict) and data.get("status") == 1:
                items = data.get("data", [])
                if not items:
                    return False, None, f"Bug {external_id} not found"
                bug = items[0].get("Bug", items[0])

                defect_data = {
                    "title": bug.get("title", ""),
                    "description": bug.get("description", ""),
                    "severity": self.map_severity_from_external(bug.get("severity", "")),
                    "status": self.map_status_from_external(bug.get("status", "")),
                    "external_id": str(bug.get("id", "")),
                    "external_url": f"https://www.tapd.cn/{workspace_id}/bugtrace/bugs/view/{bug.get('id', '')}",
                    "updated": bug.get("modified", ""),  # for conflict resolution
                }
                return True, defect_data, ""
            return False, None, f"TAPD error: {resp.text[:500]}"
        except Exception as e:
            return False, None, str(e)

    async def sync_status(self, external_id: str, new_status: str) -> tuple[bool, str]:
        """Update TAPD bug status."""
        try:
            workspace_id = self._workspace_id()
            tapd_status = self.map_status_to_external(new_status)

            payload = {
                "workspace_id": workspace_id,
                "id": external_id,
                "status": tapd_status,
            }
            headers = {
                **self._auth_header(),
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            }

            resp = await self._request("POST", "/bugs", data=payload, headers=headers)
            data = resp.json()

            if isinstance(data, dict) and data.get("status") == 1:
                return True, f"Status updated to {tapd_status}"
            return False, f"TAPD error: {resp.text[:500]}"
        except Exception as e:
            return False, str(e)
