import json
import os
import subprocess
import threading
import select
from typing import Any, Optional
from capability_vetter import CapabilityVetter


class MCPStdioClient:
    """轻量级 MCP (Model Context Protocol) Stdio 客户端。"""

    def __init__(self, name: str, command: str, args: list[str], env: Optional[dict[str, str]] = None, request_timeout: float = 30.0) -> None:
        self.name = name
        self.command = command
        self.args = args
        self.env = env or os.environ.copy()
        self.process: Optional[subprocess.Popen] = None
        self._request_id = 0
        self._lock = threading.Lock()
        self.request_timeout = request_timeout

    def start(self) -> bool:
        try:
            cmd = [self.command] + self.args
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=self.env,
            )
            # 发送 MCP initialize 握手请求
            init_response = self._send_request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "daming-agent-client", "version": "1.0.0"},
                },
            )
            if init_response and "result" in init_response:
                # 发送 initialized 通知
                self._send_notification("notifications/initialized", {})
                return True
            return False
        except Exception as error:
            print(f"⚠️ [MCP Server {self.name}] 启动失败: {error}")
            return False

    def list_tools(self) -> list[dict[str, Any]]:
        """获取 MCP Server 暴露的工具，并转换为 OpenAI Function Schema 格式。"""
        if not self.process or self.process.poll() is not None:
            return []
        response = self._send_request("tools/list", {})
        if not response or "result" not in response:
            return []
        
        mcp_tools = response["result"].get("tools", [])
        openai_tools = []
        for tool in mcp_tools:
            name = f"mcp_{self.name}_{tool['name']}"
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool.get("description", f"MCP Tool from {self.name}"),
                    "parameters": tool.get("inputSchema", {"type": "object", "properties": {}}),
                },
                "_mcp_server": self.name,
                "_mcp_original_name": tool['name'],
                "annotations": tool.get("annotations", {}),
            })
        return openai_tools

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """调用 MCP 工具并返回格式化结果。"""
        response = self._send_request("tools/call", {"name": tool_name, "arguments": arguments})
        if not response or "error" in response:
            error_msg = response.get("error", {}).get("message", "未知错误") if response else "未收到回应"
            return f"MCP 工具调用失败: {error_msg}"
        
        content_items = response.get("result", {}).get("content", [])
        texts = []
        for item in content_items:
            if item.get("type") == "text":
                texts.append(item.get("text", ""))
        return "\n".join(texts) or "MCP 工具执行完毕（无返回文本）。"

    def close(self) -> None:

        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                pass

    def _send_request(self, method: str, params: dict[str, Any]) -> Optional[dict[str, Any]]:
        with self._lock:
            self._request_id += 1
            req_id = self._request_id
            payload = {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": method,
                "params": params,
            }
            try:
                line = json.dumps(payload) + "\n"
                self.process.stdin.write(line)
                self.process.stdin.flush()

                # A stalled MCP must not block an Agent session forever.
                ready, _, _ = select.select([self.process.stdout], [], [], self.request_timeout)
                if not ready:
                    raise TimeoutError(f"MCP 请求超时 ({self.request_timeout}s): {method}")
                resp_line = self.process.stdout.readline()
                if resp_line:
                    return json.loads(resp_line)
            except Exception as error:
                print(f"⚠️ [MCP Server {self.name}] 通信错误: {error}")
            return None

    def _send_notification(self, method: str, params: dict[str, Any]) -> None:
        with self._lock:
            payload = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
            }
            try:
                line = json.dumps(payload) + "\n"
                self.process.stdin.write(line)
                self.process.stdin.flush()
            except Exception:
                pass


class MCPClientManager:
    """管理多个 MCP Server 的链接与调度。"""

    def __init__(self) -> None:
        self.clients: dict[str, MCPStdioClient] = {}
        self.tool_map: dict[str, tuple[MCPStdioClient, str]] = {}
        self.tool_annotations: dict[str, dict[str, Any]] = {}
        self._tool_schema_by_name: dict[str, dict[str, Any]] = {}
        self._tool_schema_snapshot: list[dict[str, Any]] = []
        self.vetter = CapabilityVetter()

    def add_server(self, name: str, command: str, args: list[str], env: Optional[dict[str, str]] = None) -> bool:
        # A reloaded persistent manifest must not leave the old subprocess alive.
        if name in self.clients:
            self.clients[name].close()
            self.clients.pop(name, None)
            prefix = f"mcp_{name}_"
            for tool_name in [item for item in self.tool_map if item.startswith(prefix)]:
                self.tool_map.pop(tool_name, None)
                self.tool_annotations.pop(tool_name, None)
                self._tool_schema_by_name.pop(tool_name, None)
        client = MCPStdioClient(name, command, args, env=env)
        if client.start():
            self.clients[name] = client
            tools = client.list_tools()
            for tool in tools:
                full_name = tool["function"]["name"]
                orig_name = tool["_mcp_original_name"]
                self.tool_map[full_name] = (client, orig_name)
                self.tool_annotations[full_name] = dict(tool.get("annotations", {}))
                self._tool_schema_by_name[full_name] = {
                    "type": tool["type"], "function": tool["function"]
                }
            self._tool_schema_snapshot = list(self._tool_schema_by_name.values())
            return True
        return False

    def load_from_config(self, servers: list[dict[str, Any]]) -> dict[str, bool]:
        """从声明式配置自动连接 MCP；无需再改 Agent 源码。"""
        results: dict[str, bool] = {}
        seen: set[str] = set()
        for server in servers:
            if not isinstance(server, dict) or not server.get("enabled", True):
                continue
            name = str(server.get("name", "")).strip()
            command = str(server.get("command", "")).strip()
            args = server.get("args", [])
            env = server.get("env")
            if not name or not command or not isinstance(args, list):
                print(f"⚠️ 跳过无效 MCP 配置: {server!r}")
                continue
            if name in seen:
                print(f"⚠️ 跳过重复 MCP 配置: {name}")
                continue
            seen.add(name)
            report = self.vetter.scan_mcp_manifest(server)
            if not report["install_allowed"]:
                print(f"⚠️ 拒绝高风险 MCP 配置 {name}: {report['findings']}")
                results[name] = False
                continue
            safe_env = {str(k): str(v) for k, v in env.items()} if isinstance(env, dict) else None
            results[name] = self.add_server(name, command, [str(arg) for arg in args], safe_env)
        return results

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Return the discovery snapshot; never issue tools/list on a model turn."""
        return list(self._tool_schema_snapshot)

    def is_mcp_tool(self, tool_name: str) -> bool:
        return tool_name in self.tool_map

    def is_read_only_tool(self, tool_name: str) -> bool:
        """遵循 MCP 的 readOnlyHint；未声明时保守地按外部写入处理。"""
        return bool(self.tool_annotations.get(tool_name, {}).get("readOnlyHint", False))

    def call_mcp_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        if tool_name not in self.tool_map:
            return f"未找到 MCP 工具: {tool_name}"
        client, orig_name = self.tool_map[tool_name]
        return client.call_tool(orig_name, arguments)

    def close_all(self) -> None:
        for client in self.clients.values():
            client.close()
