"""声明式 Tool 插件注册中心。

受信任项目目录中的 tool.yaml 是新增 Tool 的唯一接入点；Agent 主循环无需修改。
"""
from importlib import import_module
from pathlib import Path
from typing import Any, Callable

import yaml


class ToolRegistry:
    def __init__(self, base_dir: Path, roots: list[str]) -> None:
        self.base_dir = base_dir.resolve()
        self.roots = [(self.base_dir / root).resolve() for root in roots]
        self._tools: dict[str, tuple[dict[str, Any], Callable[..., str]]] = {}
        self.reload()

    def reload(self) -> None:
        self._tools.clear()
        for root in self.roots:
            if not root.exists():
                continue
            for manifest_path in root.rglob("tool.yaml"):
                self._load_manifest(manifest_path)

    def register_many(self, schemas: list[dict[str, Any]], executor: Callable[..., str]) -> None:
        """迁移既有内置 Tool：运行时同样通过 Registry 分发。"""
        for descriptor in schemas:
            function = descriptor.get("function", {})
            name = function.get("name")
            if not isinstance(name, str) or name in self._tools:
                continue
            def registered_executor(arguments: dict[str, Any], *, session_id: str, tool_name: str = name) -> str:
                return executor(tool_name, arguments, session_id=session_id)
            self._tools[name] = (descriptor, registered_executor)

    def _load_manifest(self, manifest_path: Path) -> None:
        try:
            data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
            name = str(data["name"])
            executor_ref = str(data["executor"])
            schema = data["schema"]
            if not name.replace("_", "").isalnum() or name in self._tools:
                raise ValueError("工具名无效或重复")
            if not isinstance(schema, dict) or schema.get("type") != "object":
                raise ValueError("schema 必须是 JSON Schema object")
            module_name, function_name = executor_ref.split(":", 1)
            if not module_name.startswith("tool_plugins."):
                raise ValueError("executor 仅允许 tool_plugins 命名空间")
            executor = getattr(import_module(module_name), function_name)
            if not callable(executor):
                raise ValueError("executor 不可调用")
            descriptor = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": str(data.get("description", name)),
                    "parameters": schema,
                },
            }
            self._tools[name] = (descriptor, executor)
        except Exception as error:
            print(f"⚠️ 加载 Tool 插件失败 {manifest_path}: {error}")

    def schemas(self) -> list[dict[str, Any]]:
        return [entry[0] for entry in self._tools.values()]

    def has(self, name: str) -> bool:
        return name in self._tools

    def execute(self, name: str, arguments: dict[str, Any], *, session_id: str) -> str:
        _, executor = self._tools[name]
        return str(executor(arguments, session_id=session_id))
