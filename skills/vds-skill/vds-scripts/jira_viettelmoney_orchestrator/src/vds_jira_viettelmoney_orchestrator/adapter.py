"""Jira adapter using atlassian-python-api (SDK-only)."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from atlassian import Jira
from requests import Session

from .errors import (
    VDSClientError,
    AuthError,
    ConflictError,
    NotFoundError,
    RateLimitError,
    ResponseError,
    TransportError,
)


class JiraAdapter:
    def __init__(
        self,
        *,
        url: str,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        session: Session | None = None,
        proxy_url: str | None = None,
        cloud: bool = False,
        timeout: int = 30,
    ) -> None:
        auth = {}
        if token:
            auth = {"token": token}
        elif username and password:
            auth = {"username": username, "password": password}
        else:
            raise AuthError("Provide either token or username/password")

        # Proxy injected per-request via Session (not system-wide env vars)
        if proxy_url and session is None:
            session = Session()
            session.proxies = {"http": proxy_url, "https": proxy_url}

        self._client = Jira(url=url, session=session, cloud=cloud, timeout=timeout, **auth)
        self._is_cloud = cloud or ".atlassian.net" in url.lower()

    # --- read operations ---
    def jql(self, query: str, *, limit: int = 50, fields: Iterable[str] | None = None) -> dict[str, Any]:
        try:
            return self._client.jql(query, limit=limit, fields=",".join(fields) if fields else None)
        except Exception as exc:  # map coarse errors; refine as needed
            _raise_mapped(exc)

    def get_issue(self, key: str) -> dict[str, Any]:
        try:
            issue = self._client.issue(key)
            if not issue:
                raise NotFoundError(f"Issue not found: {key}")
            return issue
        except Exception as exc:
            _raise_mapped(exc)

    def list_projects(self) -> list[dict[str, Any]]:
        try:
            projects = self._client.projects()
            return projects if isinstance(projects, list) else list(projects)
        except Exception as exc:
            _raise_mapped(exc)

    # --- write operations (guarded by CLI) ---
    def create_issue(
        self,
        *,
        project_key: str,
        summary: str,
        issuetype: str,
        description: str | None = None,
        assignee: str | None = None,
        labels: Sequence[str] | None = None,
        extra_fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        fields: dict[str, Any] = {
            "project": {"key": project_key},
            "summary": summary,
            "issuetype": {"name": issuetype},
        }
        if description:
            fields["description"] = description
        if assignee:
            # Server/DC uses username key (current behavior, not legacy)
            fields["assignee"] = {"name": assignee}
        if labels:
            fields["labels"] = list(labels)
        if extra_fields:
            fields.update(extra_fields)
        try:
            return self._client.create_issue(fields=fields)  # type: ignore[call-arg]
        except Exception as exc:
            _raise_mapped(exc)

    def update_issue_fields(self, key: str, fields: dict[str, Any]) -> dict[str, Any]:
        try:
            # atlassian-python-api: Jira.update_issue_field(issue_key, fields)
            return self._client.update_issue_field(key, fields)  # type: ignore[call-arg]
        except Exception as exc:
            _raise_mapped(exc)

    def add_comment(self, key: str, message: str) -> dict[str, Any]:
        """Add comment to issue."""
        try:
            return self._client.issue_add_comment(key, message)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def get_comments(self, key: str) -> list[dict[str, Any]]:
        """Get comments from issue."""
        try:
            result = self._client.issue_get_comments(key)  # type: ignore[attr-defined]
            if isinstance(result, dict) and "comments" in result:
                return result["comments"]
            return result if isinstance(result, list) else []
        except Exception as exc:
            _raise_mapped(exc)

    def transition_issue(self, key: str, to_status: str) -> None:
        try:
            transitions = self.get_issue_transitions(key)
            if not transitions:
                raise VDSClientError(f"No transitions available for {key}")
            match = None
            for t in transitions:
                name = str(t.get("name", ""))
                if name.lower() == to_status.lower():
                    match = t.get("id")
                    break
            if not match:
                raise VDSClientError(f"Transition '{to_status}' not found for {key}")

            transition_id = int(match)
            # Prefer official atlassian-python-api transition APIs.
            if hasattr(self._client, "set_issue_status_by_transition_id"):
                self._client.set_issue_status_by_transition_id(key, transition_id)  # type: ignore[attr-defined]
                return
            if hasattr(self._client, "set_issue_status_by_transition_name"):
                self._client.set_issue_status_by_transition_name(key, to_status)  # type: ignore[attr-defined]
                return
            if hasattr(self._client, "issue_transition"):
                self._client.issue_transition(key, to_status)  # type: ignore[attr-defined]
                return
            raise VDSClientError("Jira client does not support issue transition APIs")
        except Exception as exc:
            _raise_mapped(exc)

    def delete_issue(self, key: str) -> None:
        try:
            self._client.delete_issue(key)
        except Exception as exc:
            _raise_mapped(exc)

    # --- metadata operations ---
    def get_createmeta(
        self, project_key: str, issuetype: str | None = None, expand: str | None = None
    ) -> dict[str, Any]:
        """Get create metadata for issue creation (field definitions, allowed values).

        Prefer the newer createmeta endpoints and fall back to legacy createmeta when needed.
        """
        legacy_expand = expand or "projects.issuetypes.fields"

        if issuetype:
            try:
                return self._get_createmeta_v2(project_key, issuetype)
            except Exception as exc:
                if not self._createmeta_should_fallback(exc):
                    _raise_mapped(exc)

        try:
            return self._get_createmeta_legacy(project_key, issuetype=issuetype, expand=legacy_expand)
        except Exception:
            try:
                return self._get_createmeta_legacy_rest(project_key, issuetype=issuetype, expand=legacy_expand)
            except Exception as fallback_exc:
                _raise_mapped(fallback_exc)

        raise VDSClientError("Unexpected createmeta fallback path")  # pragma: no cover

    def _get_createmeta_v2(self, project_key: str, issuetype: str) -> dict[str, Any]:
        if not hasattr(self._client, "issue_createmeta_issuetypes") or not hasattr(
            self._client, "issue_createmeta_fieldtypes"
        ):
            raise VDSClientError("Jira client does not support createmeta v2 endpoints")

        issue_types, issuetypes_payload = self._collect_createmeta_issuetypes(project_key)
        matched = self._match_createmeta_issuetype(issue_types, issuetype)
        if not matched:
            raise VDSClientError(f"Issue type '{issuetype}' not found for project '{project_key}'")

        issue_type_id = self._extract_createmeta_issuetype_id(matched)
        if not issue_type_id:
            raise VDSClientError(f"Issue type id not available for '{issuetype}' in project '{project_key}'")

        fields_payload = self._collect_createmeta_fields(project_key, issue_type_id)
        fields = self._normalize_createmeta_fields(fields_payload)

        issue_type_entry = dict(matched)
        issue_type_entry["fields"] = fields

        project_entry: dict[str, Any] = {"key": project_key}
        project_id = None
        if isinstance(issuetypes_payload, dict):
            project_id = issuetypes_payload.get("projectId") or issuetypes_payload.get("project_id")
            if not project_id and isinstance(issuetypes_payload.get("project"), dict):
                project_id = issuetypes_payload["project"].get("id") or issuetypes_payload["project"].get("key")
        if project_id:
            project_entry["id"] = str(project_id)

        return {"projects": [{**project_entry, "issuetypes": [issue_type_entry]}]}

    def _collect_createmeta_issuetypes(self, project_key: str) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        start = 0
        limit = 100
        items: list[dict[str, Any]] = []
        last_payload: dict[str, Any] | None = None

        while True:
            payload = self._client.issue_createmeta_issuetypes(project_key, start=start, limit=limit)  # type: ignore[attr-defined]
            if isinstance(payload, dict):
                last_payload = payload

            page_items = self._createmeta_list_from_payload(payload, ("values", "issueTypes", "issuetypes"))
            if page_items:
                items.extend(page_items)
            if isinstance(payload, list):
                break

            if self._createmeta_page_is_last(payload, start=start, fetched=len(page_items), limit=limit):
                break

            if not page_items:
                break

            start = self._createmeta_next_start(payload, start=start, fetched=len(page_items), limit=limit)

        return items, last_payload

    def _collect_createmeta_fields(self, project_key: str, issue_type_id: str) -> dict[str, Any] | list[dict[str, Any]]:
        start = 0
        limit = 200
        items: list[dict[str, Any]] = []

        while True:
            payload = self._client.issue_createmeta_fieldtypes(project_key, issue_type_id, start=start, limit=limit)  # type: ignore[attr-defined]
            if isinstance(payload, dict) and isinstance(payload.get("fields"), dict):
                return payload["fields"]

            page_items = self._createmeta_list_from_payload(payload, ("fields", "values"))
            if page_items:
                items.extend(page_items)
            if isinstance(payload, list):
                break

            if self._createmeta_page_is_last(payload, start=start, fetched=len(page_items), limit=limit):
                break

            if not page_items:
                break

            start = self._createmeta_next_start(payload, start=start, fetched=len(page_items), limit=limit)

        return items

    @staticmethod
    def _normalize_createmeta_fields(fields_payload: dict[str, Any] | list[dict[str, Any]]) -> dict[str, Any]:
        if isinstance(fields_payload, dict):
            if isinstance(fields_payload.get("fields"), list):
                fields_payload = fields_payload["fields"]
            elif isinstance(fields_payload.get("values"), list):
                fields_payload = fields_payload["values"]
            else:
                return fields_payload

        fields: dict[str, Any] = {}
        for item in fields_payload:
            if not isinstance(item, dict):
                continue
            field_id = str(item.get("fieldId") or item.get("id") or item.get("key") or item.get("name") or "")
            if not field_id:
                continue
            field_info = dict(item)
            if "name" not in field_info and item.get("key"):
                field_info["name"] = str(item["key"])
            fields[field_id] = field_info

        return fields

    @staticmethod
    def _match_createmeta_issuetype(issue_types: list[dict[str, Any]], issuetype: str) -> dict[str, Any] | None:
        target = issuetype.strip().lower()
        for issue_type in issue_types:
            if not isinstance(issue_type, dict):
                continue
            type_id = str(issue_type.get("id") or issue_type.get("issueTypeId") or issue_type.get("issuetypeId") or "")
            type_name = str(issue_type.get("name") or issue_type.get("issueType") or issue_type.get("value") or "")
            if type_id and type_id == issuetype:
                return issue_type
            if type_name and type_name.lower() == target:
                return issue_type
        return None

    @staticmethod
    def _extract_createmeta_issuetype_id(issue_type: dict[str, Any]) -> str | None:
        for key in ("id", "issueTypeId", "issuetypeId"):
            value = issue_type.get(key)
            if value:
                return str(value)
        return None

    @staticmethod
    def _createmeta_list_from_payload(payload: Any, keys: Sequence[str]) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if not isinstance(payload, dict):
            return []
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return []

    @staticmethod
    def _createmeta_page_is_last(payload: Any, start: int, fetched: int, limit: int) -> bool:
        if isinstance(payload, dict):
            if payload.get("isLast") is True or payload.get("last") is True:
                return True
            total = payload.get("total")
            if total is not None:
                start_at = JiraAdapter._coerce_int(payload.get("startAt", payload.get("start", start)), start)
                size = JiraAdapter._coerce_int(payload.get("maxResults", payload.get("size", limit)), limit)
                if fetched:
                    size = fetched
                return start_at + size >= JiraAdapter._coerce_int(total, 0)
        return fetched < limit

    @staticmethod
    def _createmeta_next_start(payload: Any, start: int, fetched: int, limit: int) -> int:
        if isinstance(payload, dict):
            start_at = JiraAdapter._coerce_int(payload.get("startAt", payload.get("start", start)), start)
            size = JiraAdapter._coerce_int(payload.get("maxResults", payload.get("size", limit)), limit)
            if fetched:
                size = fetched
            return start_at + size
        return start + (fetched or limit)

    @staticmethod
    def _coerce_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _coerce_list_items(payload: Any, preferred_keys: tuple[str, ...] = ("values",)) -> list[dict[str, Any]]:
        """Normalize Jira SDK responses that may be list or paginated dict payloads."""
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            for key in preferred_keys:
                value = payload.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
            for fallback_key in ("values", "issues", "epics", "sprints", "versions", "dashboards", "properties"):
                value = payload.get(fallback_key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
        return []

    @staticmethod
    def _createmeta_should_fallback(exc: Exception) -> bool:
        response = getattr(exc, "response", None)
        if response is not None:
            try:
                if int(getattr(response, "status_code", 0)) in (404, 405, 410):
                    return True
            except (TypeError, ValueError):
                pass
        text = str(exc).lower()
        return any(
            token in text
            for token in (
                "404",
                "405",
                "not found",
                "unknown resource",
                "not supported",
                "does not support",
                "not support",
            )
        )

    def _get_createmeta_legacy(
        self, project_key: str, *, issuetype: str | None = None, expand: str | None = None
    ) -> dict[str, Any]:
        kwargs = {}
        if expand:
            kwargs["expand"] = expand
        payload = self._client.issue_createmeta(project_key, **kwargs)
        if issuetype:
            payload = self._filter_createmeta_payload(payload, project_key=project_key, issuetype=issuetype)
        return payload

    def _get_createmeta_legacy_rest(
        self, project_key: str, *, issuetype: str | None = None, expand: str | None = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"projectKeys": project_key}
        if issuetype:
            param_name = "issuetypeIds" if issuetype.isdigit() else "issuetypeNames"
            params[param_name] = issuetype
        if expand:
            params["expand"] = expand

        base_url = self._client.resource_url("issue")  # type: ignore[attr-defined]
        url = f"{base_url}/createmeta"
        return self._client.get(url, params=params)  # type: ignore[attr-defined]

    @staticmethod
    def _filter_createmeta_payload(payload: dict[str, Any], *, project_key: str, issuetype: str) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return payload
        projects = payload.get("projects")
        if not isinstance(projects, list):
            return payload

        filtered_projects: list[dict[str, Any]] = []
        for project in projects:
            if not isinstance(project, dict):
                continue
            project_key_match = str(project.get("key", "")).lower() == project_key.lower()
            project_id_match = str(project.get("id", "")) == project_key
            if not (project_key_match or project_id_match):
                continue

            issuetypes = project.get("issuetypes", [])
            if isinstance(issuetypes, list):
                filtered_types = []
                for issue_type in issuetypes:
                    if not isinstance(issue_type, dict):
                        continue
                    name = str(issue_type.get("name", "")).lower()
                    type_id = str(issue_type.get("id", ""))
                    if name == issuetype.lower() or type_id == issuetype:
                        filtered_types.append(issue_type)
                if filtered_types:
                    project_copy = dict(project)
                    project_copy["issuetypes"] = filtered_types
                    filtered_projects.append(project_copy)

        if filtered_projects:
            payload_copy = dict(payload)
            payload_copy["projects"] = filtered_projects
            return payload_copy

        return payload

    def get_editmeta(self, issue_key: str) -> dict[str, Any]:
        """Get edit metadata for issue updates (field definitions, allowed values)."""
        try:
            if hasattr(self._client, "issue_editmeta"):
                return self._client.issue_editmeta(issue_key)  # type: ignore[attr-defined]

            get_fn = getattr(self._client, "get", None)
            if not get_fn:
                raise VDSClientError("Jira client does not support editmeta lookup")

            resource_url = getattr(self._client, "resource_url", None)
            if callable(resource_url):
                base_url = resource_url("issue")
                url = f"{base_url}/{issue_key}/editmeta"
                return get_fn(url)

            return get_fn(f"issue/{issue_key}/editmeta")
        except Exception as exc:
            _raise_mapped(exc)

    # --- issue utilities ---
    def issue_exists(self, key: str) -> bool:
        """Check if issue exists."""
        try:
            return self._client.issue_exists(key)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def issue_deleted(self, key: str) -> bool:
        """Check if issue is deleted."""
        try:
            return self._client.issue_deleted(key)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def match_jql(self, issue_ids: list[str], jqls: list[str]) -> dict[str, Any]:
        """Check issues against JQL queries."""
        try:
            return self._client.match_jql(issue_ids, jqls)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def get_issue_field_value(self, key: str, field: str) -> Any:
        """Get issue field value."""
        try:
            return self._client.issue_field_value(key, field)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def append_issue_field_value(self, key: str, field: str, value: Any, notify_users: bool = True) -> dict[str, Any]:
        """Append value to issue field (e.g., for multi-select fields)."""
        try:
            return self._client.issue_field_value_append(key, field, value, notify_users=notify_users)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    # --- attachment operations ---
    def add_attachment(self, key: str, filename: str) -> dict[str, Any]:
        """Add attachment to issue."""
        try:
            return self._client.add_attachment(key, filename)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def get_attachments(self, key: str) -> list[dict[str, Any]]:
        """Get list of attachments for issue."""
        try:
            issue = self.get_issue(key)
            return issue.get("fields", {}).get("attachment", [])
        except Exception as exc:
            _raise_mapped(exc)

    def download_attachments(self, key: str, path: str | None = None, cloud: bool = False) -> list[str]:
        """Download attachments from issue."""
        try:
            issue = self.get_issue(key)
            return self._client.download_attachments_from_issue(issue, path=path, cloud=cloud)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    # --- project operations ---
    def get_project(self, key: str, expand: str | None = None) -> dict[str, Any]:
        """Get project details."""
        try:
            return self._client.project(key, expand=expand)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def get_project_components(self, key: str) -> list[dict[str, Any]]:
        """Get project components."""
        try:
            return self._client.get_project_components(key)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def get_project_versions(self, key: str, expand: str | None = None) -> list[dict[str, Any]]:
        """Get project versions."""
        try:
            return self._client.get_project_versions(key, expand=expand)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def add_version(
        self,
        key: str,
        project_id: str,
        version: str,
        is_archived: bool = False,
        is_released: bool = False,
    ) -> dict[str, Any]:
        """Add version to project."""
        try:
            return self._client.add_version(key, project_id, version, is_archived=is_archived, is_released=is_released)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def update_version(
        self,
        version: str,
        name: str | None = None,
        description: str | None = None,
        is_archived: bool | None = None,
        is_released: bool | None = None,
        start_date: str | None = None,
        release_date: str | None = None,
    ) -> dict[str, Any]:
        """Update version."""
        try:
            return self._client.update_version(  # type: ignore[attr-defined]
                version,
                name=name,
                description=description,
                is_archived=is_archived,
                is_released=is_released,
                start_date=start_date,
                release_date=release_date,
            )
        except Exception as exc:
            _raise_mapped(exc)

    # --- component operations ---
    def get_component(self, component_id: str) -> dict[str, Any]:
        """Get component details."""
        try:
            return self._client.component(component_id)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def create_component(self, component: dict[str, Any]) -> dict[str, Any]:
        """Create component."""
        try:
            return self._client.create_component(component)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def update_component(self, component: dict[str, Any], component_id: str) -> dict[str, Any]:
        """Update component."""
        try:
            return self._client.update_component(component, component_id)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def delete_component(self, component_id: str) -> None:
        """Delete component."""
        try:
            self._client.delete_component(component_id)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    # --- user operations ---
    def get_myself(self) -> dict[str, Any]:
        """Get current user info."""
        try:
            return self._client.myself()  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def get_user(self, account_id: str) -> dict[str, Any]:
        """Get user by account ID."""
        try:
            return self._client.user(account_id)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def find_users(
        self, query: str, start: int = 0, limit: int = 50, include_inactive: bool = False
    ) -> list[dict[str, Any]]:
        """Find users by email/display name (Cloud) or username (Server/DC)."""
        try:
            return self._client.user_find_by_user_string(  # type: ignore[attr-defined]
                query=query, start=start, limit=limit, include_inactive_users=include_inactive
            )
        except Exception as exc:
            _raise_mapped(exc)

    # --- bulk operations ---
    def bulk_update_issue_field(self, key_list: list[str], fields: str = "*all") -> dict[str, Any]:
        """Bulk update issue fields."""
        try:
            return self._client.bulk_update_issue_field(key_list, fields=fields)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def issue_field_value_append(
        self, issue_id_or_key: str, field: str, value: dict[str, Any], notify_users: bool = True
    ) -> dict[str, Any]:
        """Append value to issue field (for multi-select fields)."""
        try:
            return self._client.issue_field_value_append(issue_id_or_key, field, value, notify_users=notify_users)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def issue_archive(self, issue_id_or_key: str) -> None:
        """Archive an issue."""
        try:
            self._client.issue_archive(issue_id_or_key)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def issue_restore(self, issue_id_or_key: str) -> None:
        """Restore an archived issue."""
        try:
            self._client.issue_restore(issue_id_or_key)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def get_attachments_ids_from_issue(self, key: str) -> list[str]:
        """Get list of attachment IDs from issue."""
        try:
            return self._client.get_attachments_ids_from_issue(key)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    # --- enhanced project operations ---
    def get_all_projects(
        self, included_archived: bool | None = None, expand: str | None = None
    ) -> list[dict[str, Any]]:
        """Get all projects (alternative call)."""
        try:
            projects = self._client.get_all_projects(included_archived=included_archived, expand=expand)  # type: ignore[attr-defined]
            return projects if isinstance(projects, list) else list(projects)
        except Exception as exc:
            _raise_mapped(exc)

    def get_project_issues_count(self, project_key: str) -> int:
        """Get project issues count."""
        try:
            return self._client.get_project_issues_count(project_key)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def get_all_project_issues(
        self, project_key: str, fields: str = "*all", start: int = 0, limit: int = 500
    ) -> list[dict[str, Any]]:
        """Get all project issues."""
        try:
            return self._client.get_all_project_issues(project_key, fields=fields, start=start, limit=limit)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def get_all_assignable_users_for_project(
        self, project_key: str, start: int = 0, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get all assignable users for project."""
        try:
            return self._client.get_all_assignable_users_for_project(project_key, start=start, limit=limit)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def get_project_issuekey_last(self, project_key: str) -> str | None:
        """Get last project issue key."""
        try:
            return self._client.get_project_issuekey_last(project_key)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def get_project_issuekey_all(self, project_key: str) -> list[str]:
        """Get all project issue keys."""
        try:
            return self._client.get_project_issuekey_all(project_key)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def update_project(
        self, project_key: str, data: dict[str, Any], expand: str = "lead,description"
    ) -> dict[str, Any]:
        """Update a project."""
        try:
            return self._client.update_project(project_key, data, expand=expand)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def delete_project(self, project_key: str) -> None:
        """Delete project."""
        try:
            self._client.delete_project(project_key)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def archive_project(self, project_key: str) -> None:
        """Archive project."""
        try:
            self._client.archive_project(project_key)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def get_project_versions_paginated(
        self,
        project_key: str,
        start: int | None = None,
        limit: int | None = None,
        order_by: str | None = None,
        expand: str | None = None,
        query: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """Get project versions (paginated)."""
        try:
            return self._client.get_project_versions_paginated(  # type: ignore[attr-defined]
                project_key, start=start, limit=limit, order_by=order_by, expand=expand, query=query, status=status
            )
        except Exception as exc:
            _raise_mapped(exc)

    def get_project_permission_scheme(self, project_id_or_key: str, expand: str | None = None) -> dict[str, Any]:
        """Get project permission scheme."""
        try:
            return self._client.get_project_permission_scheme(project_id_or_key, expand=expand)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def get_project_issue_security_scheme(self, project_id_or_key: str, only_levels: bool = False) -> dict[str, Any]:
        """Get project issue security scheme."""
        try:
            return self._client.get_project_issue_security_scheme(project_id_or_key, only_levels=only_levels)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def get_priority_scheme_of_project(self, project_key_or_id: str, expand: str | None = None) -> dict[str, Any]:
        """Get priority scheme of project."""
        try:
            return self._client.get_priority_scheme_of_project(project_key_or_id, expand=expand)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def get_users_with_browse_permission_to_a_project(
        self,
        username: str,
        issue_key: str | None = None,
        project_key: str | None = None,
        start: int = 0,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get users with browse permission to a project."""
        try:
            return self._client.get_users_with_browse_permission_to_a_project(  # type: ignore[attr-defined]
                username, issue_key=issue_key, project_key=project_key, start=start, limit=limit
            )
        except Exception as exc:
            _raise_mapped(exc)

    # --- custom fields ---
    def get_custom_fields(self, search: str | None = None, start: int = 1, limit: int = 50) -> list[dict[str, Any]]:
        """Get existing custom fields or find by filter."""
        try:
            return self._client.get_custom_fields(search=search, start=start, limit=limit)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    # --- user management ---
    def remove_user(self, username: str) -> None:
        """Remove user."""
        try:
            self._client.user_remove(username)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def deactivate_user(self, username: str) -> None:
        """Deactivate user (works from Jira 8.3.0+)."""
        try:
            self._client.user_deactivate(username)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def get_user_groups(self, account_id: str) -> list[dict[str, Any]]:
        """Get groups of a user (Cloud only)."""
        if not self._is_cloud:
            raise VDSClientError(
                "get_user_groups is only available in Jira Cloud mode",
                context={"url": "unknown"},
            )
        try:
            return self._client.get_user_groups(account_id)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    # --- group management ---
    def create_group(self, name: str) -> dict[str, Any]:
        """Create a group."""
        try:
            return self._client.create_group(name)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def remove_group(self, name: str, swap_group: str | None = None) -> None:
        """Delete a group."""
        try:
            self._client.remove_group(name, swap_group=swap_group)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def get_all_users_from_group(
        self, group: str, include_inactive_users: bool = False, start: int = 0, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get all users from group."""
        try:
            return self._client.get_all_users_from_group(  # type: ignore[attr-defined]
                group, include_inactive_users=include_inactive_users, start=start, limit=limit
            )
        except Exception as exc:
            _raise_mapped(exc)

    def add_user_to_group(
        self, username: str | None = None, group_name: str | None = None, account_id: str | None = None
    ) -> None:
        """Add given user to a group."""
        try:
            self._client.add_user_to_group(username=username, group_name=group_name, account_id=account_id)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def remove_user_from_group(
        self, username: str | None = None, group_name: str | None = None, account_id: str | None = None
    ) -> None:
        """Remove given user from a group."""
        try:
            self._client.remove_user_from_group(username=username, group_name=group_name, account_id=account_id)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    # --- permissions ---
    def get_permissions(
        self,
        permissions: list[str] | None = None,
        project_id: str | None = None,
        project_key: str | None = None,
        issue_id: str | None = None,
        issue_key: str | None = None,
    ) -> dict[str, Any]:
        """Get permissions."""
        try:
            permissions_value = ",".join(permissions) if permissions else ""
            if hasattr(self._client, "get_permissions"):
                return self._client.get_permissions(  # type: ignore[attr-defined]
                    permissions=permissions_value,
                    project_id=project_id,
                    project_key=project_key,
                    issue_id=issue_id,
                    issue_key=issue_key,
                )
            raise VDSClientError("Jira client does not support permissions lookup")
        except Exception as exc:
            _raise_mapped(exc)

    def get_all_permissions(self) -> list[dict[str, Any]]:
        """Get all permissions."""
        try:
            return self._client.get_all_permissions()  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    # --- application properties ---
    def get_property(
        self,
        key: str | None = None,
        permission_level: str | None = None,
        key_filter: str | None = None,
    ) -> dict[str, Any]:
        """Get an application property."""
        try:
            return self._client.get_property(key=key, permission_level=permission_level, key_filter=key_filter)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def set_property(self, property_id: str, value: Any) -> None:
        """Set an application property."""
        try:
            self._client.set_property(property_id, value)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def get_advanced_settings(self) -> dict[str, Any]:
        """Get advanced settings."""
        try:
            return self._client.get_advanced_settings()  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    # --- issue links ---
    def create_issue_link(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create an issue-to-issue link."""
        try:
            return self._client.create_issue_link(payload)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def remove_issue_link(self, issue_link_id: str | int) -> None:
        """Remove an issue-to-issue link by ID."""
        try:
            self._client.remove_issue_link(issue_link_id)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    # --- issue link types ---
    def get_issue_link_types(self) -> list[dict[str, Any]]:
        """Get issue link types."""
        try:
            return self._client.get_issue_link_types()  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def create_issue_link_type(self, data: dict[str, str]) -> dict[str, Any]:
        """Create issue link type."""
        try:
            return self._client.create_issue_link_type(data)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def get_issue_link_type(self, issue_link_type_id: str) -> dict[str, Any]:
        """Get issue link type by ID."""
        try:
            return self._client.get_issue_link_type(issue_link_type_id)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def delete_issue_link_type(self, issue_link_type_id: str) -> None:
        """Delete issue link type."""
        try:
            self._client.delete_issue_link_type(issue_link_type_id)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def update_issue_link_type(self, issue_link_type_id: str, data: dict[str, str]) -> dict[str, Any]:
        """Update issue link type."""
        try:
            return self._client.update_issue_link_type(issue_link_type_id, data)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    # --- issue remote links ---
    def get_issue_remote_links(self, issue_key: str) -> list[dict[str, Any]]:
        """List remote links for an issue."""
        try:
            result = self._client.get_issue_remote_links(issue_key)  # type: ignore[attr-defined]
            if isinstance(result, list):
                return result
            return result or []
        except Exception as exc:
            _raise_mapped(exc)

    def create_or_update_issue_remote_link(self, issue_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Create or update a remote link for an issue."""
        try:
            return self._client.create_or_update_issue_remote_links(issue_key, payload)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def get_issue_remote_link_by_id(self, issue_key: str, remote_link_id: str | int) -> dict[str, Any]:
        """Get a remote link by ID."""
        try:
            return self._client.get_issue_remote_link_by_id(issue_key, remote_link_id)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def update_issue_remote_link_by_id(
        self,
        issue_key: str,
        remote_link_id: str | int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a remote link by ID."""
        try:
            return self._client.update_issue_remote_link_by_id(issue_key, remote_link_id, payload)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def delete_issue_remote_link_by_id(self, issue_key: str, remote_link_id: str | int) -> None:
        """Delete a remote link by ID."""
        try:
            self._client.delete_issue_remote_link_by_id(issue_key, remote_link_id)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    # --- issue properties ---
    def get_issue_property_keys(self, issue_key: str) -> dict[str, Any]:
        """Get issue property keys."""
        try:
            return self._client.get_issue_property_keys(issue_key)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def set_issue_property(self, issue_key: str, property_key: str, payload: dict[str, Any]) -> None:
        """Create or update an issue property."""
        try:
            self._client.set_issue_property(issue_key, property_key, payload)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def get_issue_property(self, issue_key: str, property_key: str) -> dict[str, Any]:
        """Get an issue property."""
        try:
            return self._client.get_issue_property(issue_key, property_key)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def delete_issue_property(self, issue_key: str, property_key: str) -> None:
        """Delete an issue property."""
        try:
            self._client.delete_issue_property(issue_key, property_key)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    # --- issue watchers ---
    def issue_get_watchers(self, issue_key: str) -> dict[str, Any]:
        """List watchers for an issue."""
        try:
            return self._client.issue_get_watchers(issue_key)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def issue_add_watcher(self, issue_key: str, username_or_account_id: str) -> None:
        """Add a watcher to an issue."""
        try:
            self._client.issue_add_watcher(issue_key, username_or_account_id)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def issue_delete_watcher(self, issue_key: str, username_or_account_id: str) -> None:
        """Remove a watcher from an issue."""
        try:
            self._client.issue_delete_watcher(issue_key, username_or_account_id)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    # --- issue security schemes ---
    def get_issue_security_schemes(self) -> list[dict[str, Any]]:
        """Get all security schemes."""
        try:
            return self._client.get_issue_security_schemes()  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def get_issue_security_scheme(self, scheme_id: str, only_levels: bool = False) -> dict[str, Any]:
        """Get issue security scheme."""
        try:
            return self._client.get_issue_security_scheme(scheme_id, only_levels=only_levels)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    # --- agile board operations ---
    def get_agile_board_by_filter_id(self, filter_id: int) -> dict[str, Any]:
        """Get agile board by filter ID."""
        try:
            return self._client.get_agile_board_by_filter_id(filter_id)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def create_agile_board(
        self, name: str, board_type: str, filter_id: int, location: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create a new agile board."""
        try:
            return self._client.create_agile_board(name, board_type, filter_id, location=location)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def get_all_agile_boards(
        self,
        board_name: str | None = None,
        project_key: str | None = None,
        board_type: str | None = None,
        start: int = 0,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get all agile boards."""
        try:
            result = self._client.get_all_agile_boards(
                board_name=board_name, project_key=project_key, board_type=board_type, start=start, limit=limit
            )  # type: ignore[attr-defined]
            return self._coerce_list_items(result, ("values",))
        except Exception as exc:
            _raise_mapped(exc)

    def delete_agile_board(self, board_id: int) -> None:
        """Delete agile board by ID."""
        try:
            self._client.delete_agile_board(board_id)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def get_agile_board(self, board_id: int) -> dict[str, Any]:
        """Get agile board by ID."""
        try:
            return self._client.get_agile_board(board_id)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def get_issues_for_board(
        self,
        board_id: int,
        jql: str | None = None,
        fields: str = "*all",
        start: int = 0,
        limit: int | None = None,
        expand: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get issues for board."""
        try:
            result = self._client.get_issues_for_board(
                board_id, jql=jql, fields=fields, start=start, limit=limit, expand=expand
            )  # type: ignore[attr-defined]
            return self._coerce_list_items(result, ("issues", "values"))
        except Exception as exc:
            _raise_mapped(exc)

    def get_agile_board_configuration(self, board_id: int) -> dict[str, Any]:
        """Get agile board configuration by board ID."""
        try:
            return self._client.get_agile_board_configuration(board_id)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    # component management is implemented above in "component operations"

    # --- agile board properties ---
    def get_agile_board_properties(self, board_id: int) -> list[dict[str, Any]]:
        """Get all board properties."""
        try:
            result = self._client.get_agile_board_properties(board_id)  # type: ignore[attr-defined]
            return self._coerce_list_items(result, ("values", "properties"))
        except Exception as exc:
            _raise_mapped(exc)

    def set_agile_board_property(self, board_id: int, property_key: str) -> None:
        """Set the value of the specified board's property."""
        try:
            self._client.set_agile_board_property(board_id, property_key)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def get_agile_board_property(self, board_id: int, property_key: str) -> dict[str, Any]:
        """Get agile board property."""
        try:
            return self._client.get_agile_board_property(board_id, property_key)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def delete_agile_board_property(self, board_id: int, property_key: str) -> None:
        """Delete agile board property."""
        try:
            self._client.delete_agile_board_property(board_id, property_key)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    # --- agile board velocity ---
    def get_agile_board_refined_velocity(self, board_id: int) -> dict[str, Any]:
        """Get agile board refined velocity."""
        try:
            return self._client.get_agile_board_refined_velocity(board_id)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def set_agile_board_refined_velocity(self, board_id: int, refined_velocity: dict[str, Any]) -> None:
        """Set agile board refined velocity."""
        try:
            self._client.set_agile_board_refined_velocity(board_id, refined_velocity)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    # --- epic operations ---
    def epic_issues(self, epic_key: str) -> list[dict[str, Any]]:
        """Get issues within an epic."""
        try:
            result = self._client.epic_issues(epic_key)  # type: ignore[attr-defined]
            return self._coerce_list_items(result, ("issues", "values"))
        except Exception as exc:
            _raise_mapped(exc)

    def get_epics(self, board_id: int, done: bool = False, start: int = 0, limit: int = 50) -> list[dict[str, Any]]:
        """Get all epics from board."""
        try:
            result = self._client.get_epics(board_id, done=done, start=start, limit=limit)  # type: ignore[attr-defined]
            return self._coerce_list_items(result, ("values", "epics"))
        except Exception as exc:
            _raise_mapped(exc)

    def get_issues_for_epic(
        self,
        board_id: int,
        epic_id: int,
        jql: str = "",
        validate_query: str = "",
        fields: str = "*all",
        expand: str = "",
        start: int = 0,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get all issues that belong to an epic on the board."""
        try:
            result = self._client.get_issues_for_epic(
                board_id,
                epic_id,
                jql=jql,
                validate_query=validate_query,
                fields=fields,
                expand=expand,
                start=start,
                limit=limit,
            )  # type: ignore[attr-defined]
            return self._coerce_list_items(result, ("issues", "values"))
        except Exception as exc:
            _raise_mapped(exc)

    # --- sprint operations ---
    def get_all_sprints_from_board(
        self, board_id: int, state: str | None = None, start: int = 0, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get all sprints from board."""
        try:
            result = self._client.get_all_sprints_from_board(board_id, state=state, start=start, limit=limit)  # type: ignore[attr-defined]
            return self._coerce_list_items(result, ("values", "sprints"))
        except Exception as exc:
            _raise_mapped(exc)

    def get_all_issues_for_sprint_in_board(
        self, board_id: int, state: str | None = None, start: int = 0, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get all issues for sprint in board."""
        try:
            result = self._client.get_all_issues_for_sprint_in_board(board_id, state=state, start=start, limit=limit)  # type: ignore[attr-defined]
            return self._coerce_list_items(result, ("issues", "values"))
        except Exception as exc:
            _raise_mapped(exc)

    def get_all_versions_from_board(
        self, board_id: int, released: str = "true", start: int = 0, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get all versions for sprint in board."""
        try:
            result = self._client.get_all_versions_from_board(board_id, released=released, start=start, limit=limit)  # type: ignore[attr-defined]
            return self._coerce_list_items(result, ("values", "versions"))
        except Exception as exc:
            _raise_mapped(exc)

    def create_sprint(
        self,
        sprint_name: str,
        origin_board_id: int,
        start_datetime: str | None = None,
        end_datetime: str | None = None,
        goal: str | None = None,
    ) -> dict[str, Any]:
        """Create sprint."""
        try:
            return self._client.create_sprint(sprint_name, origin_board_id, start_datetime, end_datetime, goal)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def rename_sprint(
        self, sprint_id: int, name: str | None = None, start_date: str | None = None, end_date: str | None = None
    ) -> dict[str, Any]:
        """Rename sprint."""
        try:
            return self._client.rename_sprint(sprint_id, name, start_date, end_date)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def add_issues_to_sprint(self, sprint_id: int, issues_list: list[str]) -> None:
        """Add/Move issues to sprint."""
        try:
            self._client.add_issues_to_sprint(sprint_id, issues_list)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    # --- backlog operations ---
    def move_issues_to_backlog(self, issue_keys: list[str]) -> None:
        """Move issues to backlog."""
        try:
            self._client.move_issues_to_backlog(issue_keys)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def add_issues_to_backlog(self, issue_keys: list[str]) -> None:
        """Add issues to backlog."""
        try:
            self._client.add_issues_to_backlog(issue_keys)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    # --- worklog operations ---
    def get_worklogs(self, issue_key: str) -> dict[str, Any]:
        """Get worklogs for an issue."""
        try:
            return self._client.issue_get_worklog(issue_key)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def issue_add_worklog(
        self,
        issue_key: str,
        time_spent: str,
        comment: str | None = None,
        started: str | None = None,
        time_sec: int | None = None,
    ) -> dict[str, Any]:
        """Add worklog entry to an issue.

        Args:
            issue_key: Issue key (e.g., 'PROJ-123')
            time_spent: Time spent string (e.g., '2h 30m')
            comment: Optional comment
            started: Optional start datetime (ISO format)
            time_sec: Optional time in seconds (alternative to time_spent)
        """
        try:
            if started and time_sec is not None:
                # Use simple worklog method if we have started and time_sec
                return self._client.issue_worklog(issue_key, started, time_sec, comment)  # type: ignore[attr-defined]
            else:
                # Use JSON worklog method for more flexibility
                worklog: dict[str, Any] = {"timeSpent": time_spent}
                if comment:
                    worklog["comment"] = comment
                if started:
                    worklog["started"] = started
                return self._client.issue_add_json_worklog(issue_key, worklog)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def get_updated_worklogs(self, since: str, expand: str | None = None) -> dict[str, Any]:
        """Get worklogs updated since timestamp.

        Args:
            since: Timestamp in format 'YYYY-MM-DD HH:mm' or ISO format
            expand: Optional expand parameter
        """
        try:
            return self._client.get_updated_worklogs(since, expand=expand)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def get_deleted_worklogs(self, since: str) -> dict[str, Any]:
        """Get deleted worklogs since timestamp.

        Args:
            since: Timestamp in format 'YYYY-MM-DD HH:mm' or ISO format
        """
        try:
            return self._client.get_deleted_worklogs(since)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    # --- transitions and changelog operations ---
    def get_issue_transitions(self, issue_key: str) -> list[dict[str, Any]]:
        """Get available transitions for an issue."""
        try:
            if hasattr(self._client, "get_issue_transitions"):
                transitions = self._client.get_issue_transitions(issue_key)  # type: ignore[attr-defined]
                if isinstance(transitions, list):
                    return transitions
            if hasattr(self._client, "get_issue_transitions_full"):
                payload = self._client.get_issue_transitions_full(issue_key)  # type: ignore[attr-defined]
                if isinstance(payload, dict) and isinstance(payload.get("transitions"), list):
                    return payload["transitions"]
            raise VDSClientError("Jira client does not support transitions lookup")
        except Exception as exc:
            _raise_mapped(exc)

    def get_issue_changelog(self, issue_key: str, start: int | None = None, limit: int | None = None) -> dict[str, Any]:
        """Get complete change history for an issue.

        Args:
            issue_key: Issue key (e.g., 'PROJ-123')
            start: Optional start index for pagination
            limit: Optional limit for pagination
        """
        try:
            return self._client.get_issue_changelog(issue_key, start=start, limit=limit)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def get_issue_status_changelog(self, issue_key: str) -> dict[str, Any]:
        """Get status change history for an issue.

        Args:
            issue_key: Issue key (e.g., 'PROJ-123')
        """
        try:
            return self._client.get_issue_status_changelog(issue_key)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    # --- dashboard operations ---
    def get_dashboard(self, dashboard_id: str | int) -> dict[str, Any]:
        """Get dashboard by ID.

        Args:
            dashboard_id: Dashboard ID (string or integer)
        """
        try:
            result = self._client.get_dashboard(dashboard_id)  # type: ignore[attr-defined]
            if not result:
                raise NotFoundError(f"Dashboard not found: {dashboard_id}")
            return result
        except Exception as exc:
            _raise_mapped(exc)

    def get_dashboards(self, filter: str = "", start: int = 0, limit: int = 10) -> dict[str, Any]:
        """List dashboards with optional filter.

        Args:
            filter: Optional filter string
            start: Start index for pagination
            limit: Maximum number of results
        """
        try:
            result = self._client.get_dashboards(filter=filter, start=start, limit=limit)  # type: ignore[attr-defined]
            return result if result else {}
        except Exception as exc:
            _raise_mapped(exc)

    # --- reindex operations ---
    def reindex(self) -> dict[str, Any]:
        """Trigger reindex."""
        try:
            return self._client.reindex()  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def reindex_status(self) -> dict[str, Any]:
        """Get reindex status."""
        try:
            return self._client.reindex_status()  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def reindex_with_type(self, reindex_type: str) -> dict[str, Any]:
        """Reindex with type."""
        try:
            return self._client.reindex_with_type(reindex_type)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    # --- filter operations ---
    def get_filters(self, owner: str | None = None) -> list[dict[str, Any]]:
        """Get list of filters, optionally filtered by owner.

        Args:
            owner: Optional username to filter by owner
        """
        try:
            # SDK doesn't have get_filters, use REST API directly
            # Endpoint: /rest/api/2/filter/search
            params: dict[str, Any] = {}
            if owner:
                params["username"] = owner

            # Use SDK's get method with resource URL
            base_url = self._client.resource_url("filter")  # type: ignore[attr-defined]
            url = f"{base_url}/search"
            result = self._client.get(url, params=params)  # type: ignore[attr-defined]
            return (
                result.get("values", []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
            )
        except Exception as exc:
            _raise_mapped(exc)

    def get_filter(self, filter_id: int) -> dict[str, Any]:
        """Get filter by ID.

        Args:
            filter_id: Filter ID
        """
        try:
            result = self._client.get_filter(filter_id)  # type: ignore[attr-defined]
            if not result:
                raise NotFoundError(f"Filter not found: {filter_id}")
            return result
        except Exception as exc:
            _raise_mapped(exc)

    def create_filter(
        self, name: str, jql: str, description: str | None = None, favourite: bool = False
    ) -> dict[str, Any]:
        """Create a new filter.

        Args:
            name: Filter name
            jql: JQL query string
            description: Optional description
            favourite: Whether to mark as favourite (default: False)
        """
        try:
            return self._client.create_filter(name=name, jql=jql, description=description, favourite=favourite)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def update_filter(
        self,
        filter_id: int,
        name: str | None = None,
        jql: str | None = None,
        description: str | None = None,
        favourite: bool | None = None,
    ) -> dict[str, Any]:
        """Update an existing filter.

        Args:
            filter_id: Filter ID
            name: Optional new name
            jql: Optional new JQL query (required if not updating other fields)
            description: Optional new description
            favourite: Optional favourite status
        """
        try:
            # SDK's update_filter requires jql, but we allow partial updates
            # If jql is not provided, we need to get the current filter first
            if jql is None:
                # Get current filter to preserve existing JQL
                current = self.get_filter(filter_id)
                jql = current.get("jql", "")

            kwargs: dict[str, Any] = {}
            if name is not None:
                kwargs["name"] = name
            if description is not None:
                kwargs["description"] = description
            if favourite is not None:
                kwargs["favourite"] = favourite

            return self._client.update_filter(filter_id, jql=jql, **kwargs)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def delete_filter(self, filter_id: int) -> None:
        """Delete a filter.

        Args:
            filter_id: Filter ID
        """
        try:
            self._client.delete_filter(filter_id)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    # --- advanced search operations ---
    def search_issues_advanced(
        self,
        jql: str,
        *,
        start: int = 0,
        limit: int = 50,
        fields: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        """Advanced JQL search with pagination support.

        Args:
            jql: JQL query string
            start: Start index for pagination (default: 0)
            limit: Maximum number of results (default: 50)
            fields: Optional list of fields to return (default: *all)
        """
        try:
            fields_str = ",".join(fields) if fields else "*all"
            return self._client.jql(jql, fields=fields_str, start=start, limit=limit)  # type: ignore[attr-defined]
        except Exception as exc:
            _raise_mapped(exc)

    def search_issues_by_filter(
        self,
        filter_id: int,
        *,
        start: int = 0,
        limit: int = 50,
        fields: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        """Search issues using a saved filter.

        Args:
            filter_id: Filter ID
            start: Start index for pagination (default: 0)
            limit: Maximum number of results (default: 50)
            fields: Optional list of fields to return (default: *all)
        """
        try:
            # Get the filter to extract its JQL
            filter_data = self.get_filter(filter_id)
            jql = filter_data.get("jql", "")
            if not jql:
                raise VDSClientError(f"Filter {filter_id} does not have a JQL query")

            # Use the filter's JQL for search
            return self.search_issues_advanced(jql, start=start, limit=limit, fields=fields)
        except Exception as exc:
            _raise_mapped(exc)


def _raise_mapped(exc: Exception) -> None:
    text = str(exc).lower()
    if "401" in text or "403" in text or "unauthorized" in text:
        raise AuthError(str(exc)) from exc
    if "404" in text or "not found" in text:
        raise NotFoundError(str(exc)) from exc
    if "429" in text or "rate limit" in text:
        raise RateLimitError(str(exc)) from exc
    if "409" in text or "conflict" in text:
        raise ConflictError(str(exc)) from exc
    if "500" in text or "server error" in text:
        raise ResponseError(str(exc)) from exc
    if "connection" in text or "network" in text or "timeout" in text:
        raise TransportError(str(exc)) from exc
    raise VDSClientError(str(exc)) from exc
