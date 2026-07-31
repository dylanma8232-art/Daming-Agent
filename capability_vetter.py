"""Source-agnostic static gate for externally acquired agent capabilities."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class CapabilityVetter:
    HIGH = (r"\beval\s*\(", r"\bexec\s*\(", r"base64\.b64decode", r"curl\s+.*\|\s*(?:sh|bash)", r"rm\s+-rf", r"os\.environ\[.*(?:KEY|TOKEN|SECRET)", r"(?:^|\s)(?:sh|bash|zsh|cmd)(?:\s|$)", r"(?:;|&&|\|\|)")
    MEDIUM = (r"subprocess", r"requests\.", r"httpx\.", r"socket\.", r"git\s+clone", r"npm\s+install", r"pip\s+install", r"\bnpx\b", r"\bnpm\b", r"\bpip\b")

    def scan(self, root: Path) -> dict[str, Any]:
        findings: list[dict[str, str]] = []
        files = [p for p in root.rglob("*") if p.is_file()]
        for path in files:
            if path.stat().st_size > 2_000_000:
                findings.append({"severity": "medium", "file": str(path.relative_to(root)), "rule": "oversized_file"}); continue
            try: text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError: continue
            for severity, rules in (("high", self.HIGH), ("medium", self.MEDIUM)):
                for rule in rules:
                    if re.search(rule, text, re.I): findings.append({"severity": severity, "file": str(path.relative_to(root)), "rule": rule})
        risk = "high" if any(x["severity"] == "high" for x in findings) else "medium" if findings else "low"
        return {"risk": risk, "files": len(files), "findings": findings, "install_allowed": risk == "low"}

    def scan_mcp_manifest(self, manifest: dict[str, Any]) -> dict[str, Any]:
        """Vet a declarative MCP launch specification before it is enabled."""
        command = str(manifest.get("command", ""))
        args = " ".join(str(item) for item in manifest.get("args", []))
        text = f"{command} {args}"
        findings = []
        for rule in self.HIGH:
            if re.search(rule, text, re.I): findings.append({"severity": "high", "rule": rule})
        for rule in self.MEDIUM:
            if re.search(rule, text, re.I): findings.append({"severity": "medium", "rule": rule})
        risk = "high" if any(item["severity"] == "high" for item in findings) else "medium" if findings else "low"
        return {"risk": risk, "findings": findings, "install_allowed": risk == "low"}
