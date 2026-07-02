"""Jira Cloud sync provider — REST API v3."""
from __future__ import annotations

import json
from base64 import b64encode

from app.services.sync.base import BaseSyncProvider


class JiraSyncProvider(BaseSyncProvider):
    """Sync provider for Jira Cloud (REST API v3)."""

    DEFAULT_SEVERITY_MAP = {"P0": "Highest", "P1": "High", "P2": "Medium", "P3": "Low"}
    DEFAULT_SEVERITY_REVERSE = {"Highest": "P0", "High": "P1", "Medium": "P2", "Low": "P3"}
    DEFAULT_STATUS_MAP = {
        "open": "To Do", "confirmed": "In Progress", "fixing": "In Progress",
        "pending_review": "In Review", "closed": "Done", "rejected": "Won't Do",
    }
    DEFAULT_STATUS_REVERSE = {
        "To Do": "open", "In Progress": "fixing", "In Review": "pending_review",
        "Done": "closed", "Won't Do": "rejected",
    }

    def _auth_header(self) -> dict:
        email = self.auth.get("email", "")
        api_token = self.auth.get("api_token", "")
        raw = f"{email}:{api_token}".encode("utf-8")
        return {"Authorization": f"Basic {b64encode(raw).decode('utf-8')}"}

    async def test_connection(self) -> tuple[bool, str]:
        try:
            resp = await self._request("GET", "/rest/api/3/myself", headers={**self._auth_header(), "Accept": "application/json"})
            data = resp.json()
            name = data.get("displayName", data.get("name", "unknown"))
            return True, f"Connected to Jira as {name}"
        except Exception as e:
            return False, str(e)

    async def push_defect(self, defect: dict) -> tuple[bool, str, str]:
        """Create a new Jira issue from a CamelTv defect."""
        try:
            project_key = self.auth.get("project_key", "")
            if not project_key:
                return False, "", "Missing project_key in auth config"

            severity = self.map_severity_to_external(defect.get("severity", "P2"))
            status_name = self.map_status_to_external(defect.get("status", "open"))

            payload = {
                "fields": {
                    "project": {"key": project_key},
                    "summary": defect.get("title", ""),
                    "description": {
                        "type": "doc", "version": 1,
                        "content": [{"type": "paragraph", "content": [{"type": "text", "text": defect.get("description", "")}]}]
                    },
                    "issuetype": {"name": "Bug"},
                    "priority": {"name": severity},
                }
            }

            headers = {**self._auth_header(), "Content-Type": "application/json", "Accept": "application/json"}
            resp = await self._request("POST", "/rest/api/3/issue", json=payload, headers=headers)
            data = resp.json()

            issue_key = data.get("key", "")
            issue_url = f"{self.base_url}/browse/{issue_key}" if issue_key else ""
            return True, issue_key, issue_url
        except Exception as e:
            return False, "", str(e)

    async def pull_defect(self, external_id: str) -> tuple[bool, dict | None, str]:
        """Fetch a Jira issue by key."""
        try:
            headers = {**self._auth_header(), "Accept": "application/json"}
            resp = await self._request("GET", f"/rest/api/3/issue/{external_id}", headers=headers)
            data = resp.json()

            fields = data.get("fields", {})
            priority_name = fields.get("priority", {}).get("name", "") if fields.get("priority") else ""
            status_name = fields.get("status", {}).get("name", "") if fields.get("status") else ""

            defect_data = {
                "title": fields.get("summary", ""),
                "description": _extract_jira_description(fields.get("description", {})),
                "severity": self.map_severity_from_external(priority_name),
                "status": self.map_status_from_external(status_name),
                "external_id": data.get("key", ""),
                "external_url": f"{self.base_url}/browse/{data.get('key', '')}",
                "updated": fields.get("updated", ""),  # for conflict resolution
            }
            return True, defect_data, ""
        except Exception as e:
            return False, None, str(e)

    async def sync_status(self, external_id: str, new_status: str) -> tuple[bool, str]:
        """Update Jira issue status via transitions."""
        try:
            jira_status = self.map_status_to_external(new_status)
            headers = {**self._auth_header(), "Accept": "application/json"}

            # Get available transitions
            resp = await self._request("GET", f"/rest/api/3/issue/{external_id}/transitions", headers=headers)
            transitions = resp.json().get("transitions", [])

            # Find transition that leads to target status
            transition_id = None
            for t in transitions:
                if t.get("to", {}).get("name", "").lower() == jira_status.lower():
                    transition_id = t.get("id")
                    break

            if not transition_id:
                # Fallback: try the first transition whose name contains target
                for t in transitions:
                    if jira_status.lower() in t.get("to", {}).get("name", "").lower():
                        transition_id = t.get("id")
                        break

            if not transition_id:
                names = [t.get("to", {}).get("name", "") for t in transitions]
                return False, f"No transition found to '{jira_status}'. Available: {names}"

            payload = {"transition": {"id": transition_id}}
            headers["Content-Type"] = "application/json"
            await self._request("POST", f"/rest/api/3/issue/{external_id}/transitions", json=payload, headers=headers)
            return True, f"Status updated to {jira_status}"
        except Exception as e:
            return False, str(e)


def _extract_jira_description(desc: dict) -> str:
    """Extract plain text from Jira ADF (Atlassian Document Format) description."""
    if not desc:
        return ""
    text_parts = []

    def _walk(node):
        if isinstance(node, dict):
            if node.get("type") == "text":
                text_parts.append(node.get("text", ""))
            for child in node.get("content", []):
                _walk(child)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(desc)
    return "".join(text_parts).strip()
