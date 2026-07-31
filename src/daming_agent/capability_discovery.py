"""External capability discovery; discovery is read-only, installation is separate."""
from __future__ import annotations

import httpx
import re
from typing import Any


class ExternalCapabilityDiscovery:
    def __init__(self, sources: list[dict[str, Any]] | None = None) -> None:
        self.sources = [item for item in (sources or []) if isinstance(item, dict) and item.get("enabled", True)]

    def search(self, query: str, kinds: list[str] | None = None, limit: int = 10) -> list[dict[str, Any]]:
        """Query configured read-only catalogs; never download or execute code."""
        results: list[dict[str, Any]] = []
        for source in self.sources:
            if source.get("type") == "github":
                results.extend(self._search_github(source, query, kinds))
                continue
            if source.get("type") == "lobehub":
                results.extend(self._search_lobehub(source, query, kinds))
                continue
            if source.get("type") != "http_json" or not source.get("url"):
                continue
            try:
                response = httpx.get(str(source["url"]), params={"q": query, "kinds": ",".join(kinds or [])}, timeout=8.0)
                response.raise_for_status()
                payload = response.json()
                rows = payload.get("items", payload) if isinstance(payload, dict) else payload
                for row in rows if isinstance(rows, list) else []:
                    if not isinstance(row, dict):
                        continue
                    kind = str(row.get("kind", "skill"))
                    if kinds and kind not in kinds:
                        continue
                    results.append({
                        "name": str(row.get("name", "unnamed")), "kind": kind,
                        "description": str(row.get("description", "")),
                        "source": str(source.get("name", source["url"])),
                        "version": str(row.get("version", "unknown")),
                        "install": row.get("install"), "permissions": row.get("permissions", []),
                    })
            except Exception:
                continue
        return results[:max(1, min(limit, 20))]

    @staticmethod
    def _search_github(source: dict[str, Any], query: str, kinds: list[str] | None) -> list[dict[str, Any]]:
        if kinds and not any(kind in {"skill", "tool", "mcp"} for kind in kinds):
            return []
        try:
            requested = [kind for kind in (kinds or ["skill", "mcp", "tool"]) if kind in {"skill", "mcp", "tool"}]
            rows: list[dict[str, Any]] = []
            terms = {"skill": "agent skill", "mcp": "mcp server", "tool": "agent tool plugin"}
            for kind in requested:
                response = httpx.get("https://api.github.com/search/repositories", params={"q": f"{query} {terms[kind]}", "per_page": 10}, headers={"Accept": "application/vnd.github+json"}, timeout=8.0)
                response.raise_for_status()
                rows.extend({"name": item["full_name"], "kind": kind, "description": item.get("description") or "", "source": source.get("name", "GitHub"), "version": item.get("default_branch", "main"), "install": {"type": "git", "source": item["clone_url"]}, "permissions": []} for item in response.json().get("items", []) if not item.get("archived"))
            return rows
        except Exception:
            return []

    @staticmethod
    def _search_lobehub(source: dict[str, Any], query: str, kinds: list[str] | None) -> list[dict[str, Any]]:
        if kinds and "skill" not in kinds:
            return []
        try:
            response = httpx.get("https://lobehub.com/zh/skills", params={"q": query}, timeout=8.0)
            response.raise_for_status()
            slugs = sorted(set(re.findall(r"/zh/skills/([a-z0-9][a-z0-9-]+)", response.text, re.I)))
            return [{"name": slug, "kind": "skill", "description": "LobeHub Skill 候选", "source": source.get("name", "LobeHub"), "version": "marketplace", "install": {"type": "lobehub", "identifier": slug}, "permissions": []} for slug in slugs[:10]]
        except Exception:
            return []
