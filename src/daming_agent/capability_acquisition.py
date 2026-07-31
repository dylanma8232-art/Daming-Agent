"""Quarantine, vet and register external Agent capabilities without executing them."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import json
import httpx
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

from capability_vetter import CapabilityVetter


class CapabilityAcquisition:
    def __init__(self, base_dir: Path, vetter: CapabilityVetter | None = None) -> None:
        self.base_dir = base_dir
        self.quarantine = base_dir / "data" / "capability-quarantine"
        self.destination = base_dir / ".agents" / "skills"
        self.mcp_destination = base_dir / "data" / "acquired-capabilities" / "mcp"
        self.tool_destination = base_dir / "tool_plugins" / "external"
        self.vetter = vetter or CapabilityVetter()
        self.quarantine.mkdir(parents=True, exist_ok=True)
        self.destination.mkdir(parents=True, exist_ok=True)
        self.mcp_destination.mkdir(parents=True, exist_ok=True)
        self.tool_destination.mkdir(parents=True, exist_ok=True)
        (self.tool_destination / "__init__.py").touch(exist_ok=True)

    def acquire_skill(self, source: str, name: str = "") -> dict[str, Any]:
        """Fetch a Git repository into quarantine, inspect it, then install low-risk SKILL.md content.

        No repository command, setup script or dependency installation is executed.
        """
        slug = name.strip() or Path(urlparse(source).path).stem or "external-skill"
        slug = "".join(char if char.isalnum() or char in "-_" else "-" for char in slug).strip("-")
        with tempfile.TemporaryDirectory(dir=self.quarantine) as temp:
            staged = Path(temp) / "source"
            if urlparse(source).netloc.endswith("lobehub.com"):
                return self._acquire_lobehub_page(source, slug, staged)
            result = subprocess.run(["git", "clone", "--depth", "1", source, str(staged)], capture_output=True, text=True, timeout=45)
            if result.returncode:
                return {"ok": False, "stage": "download", "error": result.stderr[-1000:]}
            skill_roots = [path.parent for path in staged.rglob("SKILL.md")]
            if not skill_roots:
                return {"ok": False, "stage": "inspect", "error": "未发现 SKILL.md，拒绝作为 Skill 安装"}
            report = self.vetter.scan(staged)
            if not report["install_allowed"]:
                return {"ok": False, "stage": "vet", "report": report}
            target = self.destination / slug
            if target.exists():
                shutil.rmtree(target)
            # Only copy the requested capability documentation tree; never run it.
            shutil.copytree(skill_roots[0], target)
            return {"ok": True, "stage": "installed", "path": str(target), "report": report}

    def acquire_mcp(self, manifest: dict[str, Any]) -> dict[str, Any]:
        """Register a declarative MCP launch manifest only after static review.

        This method does not install packages or run the command.  The caller may
        start it afterwards through ``MCPClientManager``; the persisted manifest
        makes the capability available again after an Agent restart.
        """
        name = self._safe_slug(str(manifest.get("name", "")))
        command = str(manifest.get("command", "")).strip()
        args = manifest.get("args", [])
        if not name or not command or not isinstance(args, list):
            return {"ok": False, "stage": "inspect", "error": "MCP 必须提供 name、command 和 args 数组"}
        normalized = {"name": name, "command": command, "args": [str(arg) for arg in args], "enabled": True}
        if isinstance(manifest.get("env"), dict):
            normalized["env"] = {str(k): str(v) for k, v in manifest["env"].items()}
        report = self.vetter.scan_mcp_manifest(normalized)
        if not report["install_allowed"]:
            return {"ok": False, "stage": "vet", "report": report}
        path = self.mcp_destination / f"{name}.json"
        path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"ok": True, "stage": "installed", "manifest": normalized, "path": str(path), "report": report}

    def acquired_mcp_manifests(self) -> list[dict[str, Any]]:
        manifests: list[dict[str, Any]] = []
        for path in sorted(self.mcp_destination.glob("*.json")):
            try:
                item = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(item, dict):
                    manifests.append(item)
            except (OSError, json.JSONDecodeError):
                continue
        return manifests

    def acquire_tool(self, source: str, name: str = "") -> dict[str, Any]:
        """Quarantine a Python Tool plugin and install only a low-risk manifest.

        Portable external Tools must expose their Python implementation under a
        ``tool_plugins/`` package and declare an executor in that namespace.
        The copied manifest is rewritten into our isolated ``external`` namespace.
        """
        slug = self._safe_slug(name or Path(urlparse(source).path).stem or "external-tool")
        with tempfile.TemporaryDirectory(dir=self.quarantine) as temp:
            staged = Path(temp) / "source"
            result = subprocess.run(["git", "clone", "--depth", "1", source, str(staged)], capture_output=True, text=True, timeout=45)
            if result.returncode:
                return {"ok": False, "stage": "download", "error": result.stderr[-1000:]}
            report = self.vetter.scan(staged)
            if not report["install_allowed"]:
                return {"ok": False, "stage": "vet", "report": report}
            manifests = list(staged.rglob("tool.yaml"))
            package = staged / "tool_plugins"
            if len(manifests) != 1 or not package.is_dir():
                return {"ok": False, "stage": "inspect", "error": "Tool 必须恰有一个 tool.yaml 和 tool_plugins/ 实现目录"}
            try:
                import yaml
                data = yaml.safe_load(manifests[0].read_text(encoding="utf-8")) or {}
                module, function = str(data["executor"]).split(":", 1)
                if not module.startswith("tool_plugins.") or not function.isidentifier():
                    raise ValueError("executor 必须是 tool_plugins.*:function")
            except Exception as error:
                return {"ok": False, "stage": "inspect", "error": f"无效 Tool manifest: {error}"}
            target = self.tool_destination / slug
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(package, target)
            (target / "__init__.py").touch(exist_ok=True)
            data["executor"] = f"tool_plugins.external.{slug}.{module.removeprefix('tool_plugins.') }:{function}"
            (target / "tool.yaml").write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
            return {"ok": True, "stage": "installed", "path": str(target), "report": report, "tool": data.get("name")}

    @staticmethod
    def _safe_slug(value: str) -> str:
        return "".join(char if char.isalnum() or char in "-_" else "-" for char in value.strip()).strip("-")

    def _acquire_lobehub_page(self, source: str, slug: str, staged: Path) -> dict[str, Any]:
        """Install a documentation-only LobeHub Skill when market credentials are absent."""
        try:
            response = httpx.get(
                source, timeout=15.0, follow_redirects=True,
                headers={"Accept": "text/markdown, text/plain;q=0.9, text/html;q=0.1", "User-Agent": "curl/8.0"},
            )
            response.raise_for_status()
        except Exception as error:
            return {"ok": False, "stage": "download", "error": str(error)}
        # LobeHub's public page is server-rendered Markdown.  Keep only the
        # Skill body and discard marketplace reviews/install shell examples.
        body = response.text
        marker = "## Install This Skill"
        if marker in body:
            body = body.split(marker, 1)[0].strip()
        if not body.startswith("#"):
            return {"ok": False, "stage": "inspect", "error": "LobeHub 页面未返回可安装的 Skill 正文"}
        staged.mkdir(parents=True, exist_ok=True)
        (staged / "SKILL.md").write_text(body + "\n", encoding="utf-8")
        report = self.vetter.scan(staged)
        if not report["install_allowed"]:
            return {"ok": False, "stage": "vet", "report": report}
        target = self.destination / slug
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(staged, target)
        return {"ok": True, "stage": "installed", "path": str(target), "report": report}
