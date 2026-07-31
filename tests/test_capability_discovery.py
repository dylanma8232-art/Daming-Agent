from unittest.mock import Mock, patch

from capability_discovery import ExternalCapabilityDiscovery
from capability_acquisition import CapabilityAcquisition


def test_github_discovery_returns_install_metadata():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"items": [{"full_name": "org/demo", "description": "demo", "default_branch": "main", "clone_url": "https://github.com/org/demo.git", "archived": False}]}
    with patch("capability_discovery.httpx.get", return_value=response):
        rows = ExternalCapabilityDiscovery([{"type": "github"}]).search("security")
    assert rows[0]["install"] == {"type": "git", "source": "https://github.com/org/demo.git"}


def test_lobehub_discovery_extracts_skill_identifiers():
    response = Mock()
    response.raise_for_status.return_value = None
    response.text = '<a href="/zh/skills/openclaw-skills-skill-vetter">vet</a>'
    with patch("capability_discovery.httpx.get", return_value=response):
        rows = ExternalCapabilityDiscovery([{"type": "lobehub"}]).search("security")
    assert rows[0]["name"] == "openclaw-skills-skill-vetter"


def test_lobehub_page_acquisition_installs_vetted_documentation(tmp_path):
    response = Mock()
    response.raise_for_status.return_value = None
    response.text = "# skill-vetter\n\nSecurity checklist.\n\n## Install This Skill\n\n```sh\nignore\n```"
    acquisition = CapabilityAcquisition(tmp_path)
    with patch("capability_acquisition.httpx.get", return_value=response):
        result = acquisition.acquire_skill("https://lobehub.com/zh/skills/demo", "demo")
    assert result["ok"]
    assert (tmp_path / ".agents" / "skills" / "demo" / "SKILL.md").read_text(encoding="utf-8").startswith("# skill-vetter")


def test_mcp_acquisition_persists_only_vetted_local_manifest(tmp_path):
    acquisition = CapabilityAcquisition(tmp_path)
    result = acquisition.acquire_mcp({"name": "local-clock", "command": "/usr/local/bin/clock-mcp", "args": ["--stdio"]})
    assert result["ok"]
    assert acquisition.acquired_mcp_manifests() == [result["manifest"]]
    rejected = acquisition.acquire_mcp({"name": "remote", "command": "npx", "args": ["-y", "untrusted-mcp"]})
    assert not rejected["ok"]
