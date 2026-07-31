import os
import re
from pathlib import Path
from typing import Any, Optional


class SkillManager:
    """管理一个或多个 Skill 根目录下符合 SKILL.md 规范的技能。"""

    def __init__(self, skill_roots: list[Path]) -> None:
        self.skill_roots = [root.resolve() for root in skill_roots]
        auto_gen = (Path(__file__).parent.parent / "skills" / "auto-generated").resolve()
        if auto_gen not in self.skill_roots:
            self.skill_roots.append(auto_gen)
        for root in self.skill_roots:
            root.mkdir(parents=True, exist_ok=True)
        self.skills: dict[str, dict[str, Any]] = {}
        self._fingerprint: tuple[tuple[str, int, int], ...] = ()
        self.scan_skills()

    def scan_skills(self) -> None:
        """Refresh metadata only when a SKILL.md file actually changed.

        The Agent invokes this once per user turn.  Re-reading every complete
        SOP on every turn made ordinary chat pay for the whole skill catalog.
        """
        paths = []
        for root in self.skill_roots:
            if root.exists():
                paths.extend(root.glob("*/SKILL.md"))
        fingerprint = tuple(sorted(
            (str(path), path.stat().st_mtime_ns, path.stat().st_size) for path in paths
        ))
        if self.skills and fingerprint == self._fingerprint:
            return
        self.skills.clear()
        for root in self.skill_roots:
            if not root.exists():
                continue
            for folder in root.iterdir():
                if folder.is_dir():
                    skill_md = folder / "SKILL.md"
                    if skill_md.is_file():
                        try:
                            content = skill_md.read_text(encoding="utf-8")
                            frontmatter = self._parse_frontmatter(content)
                            name = frontmatter.get("name", folder.name)
                            description = frontmatter.get("description", "未提供描述。")
                            # 同名时优先项目本地 skills/，避免第三方包覆盖本地定制。
                            if name not in self.skills:
                                self.skills[name] = {
                                    "name": name,
                                    "folder": folder.name,
                                    "path": skill_md,
                                    "description": description,
                                    "content": content,
                                    "root": root,
                                }
                        except Exception as e:
                            print(f"⚠️ 解析技能文件 {skill_md} 失败: {e}")
        self._fingerprint = fingerprint

    def get_skill_summary_hint(self, skill_names: Optional[list[str]] = None) -> str:
        selected = self.skills if skill_names is None else {
            name: self.skills[name] for name in skill_names if name in self.skills
        }
        if not selected:
            return "（当前未加载任何 SKILL.md 技能）"
        lines = []
        for name, data in selected.items():
            lines.append(f"- [{name}]: {data['description']}")
        return "\n".join(lines)

    def match_skills(self, user_input: str, limit: int = 3) -> list[str]:
        """Deterministically select a small relevant skill set for a turn."""
        return [item["name"] for item in self.search_skills(user_input, limit=limit)]

    def search_skills(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search the local Skill catalog without loading every SOP into a model turn."""
        text = query.lower().strip()
        if not text:
            return []
        tokens = self._search_tokens(text)
        scored: list[tuple[int, str]] = []
        for name, data in self.skills.items():
            haystack = f"{name} {data['folder']} {data['description']}".lower()
            score = (4 if name.lower() in text or data['folder'].lower() in text else 0)
            score += sum(1 for token in tokens if token in haystack)
            if score:
                scored.append((score, name))
        return [
            {"name": name, "description": self.skills[name]["description"], "score": score}
            for score, name in sorted(scored, key=lambda row: (-row[0], row[1]))[:limit]
        ]

    @staticmethod
    def _search_tokens(text: str) -> set[str]:
        tokens = {token for token in re.findall(r"[a-z0-9][a-z0-9_-]*", text) if len(token) >= 2}
        for phrase in re.findall(r"[\u4e00-\u9fff]+", text):
            if len(phrase) <= 4:
                tokens.add(phrase)
            tokens.update(phrase[index:index + 2] for index in range(len(phrase) - 1))
        return tokens

    def view_skill(self, skill_name: str) -> str:
        """根据技能名称读取完整的 SKILL.md 指导内容。"""
        if skill_name in self.skills:
            path: Path = self.skills[skill_name]["path"]
            return f"=== 技能 SOP 标准规范 [{skill_name}] ===\n" + path.read_text(encoding="utf-8")
        
        # 模糊匹配
        for name, data in self.skills.items():
            if skill_name.lower() in name.lower():
                return f"=== 技能 SOP 标准规范 [{name}] ===\n" + data["path"].read_text(encoding="utf-8")

        return f"未找到技能: '{skill_name}'。可用技能列表: {list(self.skills.keys())}"

    @staticmethod
    def _parse_frontmatter(text: str) -> dict[str, str]:
        """解析 YAML Frontmatter 元数据 (处于 --- 和 --- 之间的内容)。"""
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
        if not match:
            return {}
        yaml_text = match.group(1)
        result = {}
        for line in yaml_text.splitlines():
            line = line.strip()
            if ":" in line and not line.startswith("#"):
                key, val = line.split(":", 1)
                result[key.strip()] = val.strip().strip("\"'")
        return result
