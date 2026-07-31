from capability_vetter import CapabilityVetter


def test_vetter_allows_plain_skill_and_blocks_exec(tmp_path):
    safe = tmp_path / "safe"; safe.mkdir(); (safe / "SKILL.md").write_text("# instructions", encoding="utf-8")
    assert CapabilityVetter().scan(safe)["install_allowed"]
    bad = tmp_path / "bad"; bad.mkdir(); (bad / "x.py").write_text("exec(payload)", encoding="utf-8")
    assert CapabilityVetter().scan(bad)["risk"] == "high"


def test_vetter_rejects_mcp_package_bootstrapper():
    report = CapabilityVetter().scan_mcp_manifest({"name": "remote", "command": "npx", "args": ["-y", "some-mcp"]})
    assert report["risk"] == "medium"
    assert not report["install_allowed"]
