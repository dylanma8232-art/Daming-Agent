import os
import sys
import json
import asyncio
import threading
import re
from typing import Dict, Any, List
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from agent import LocalAgent
from channels.base import IncomingMessage, OutgoingMessage
from logger import get_logger, get_recent_logs

logger = get_logger("web_server")

load_dotenv()
app = FastAPI(title="Daming Agent Web Management Dashboard", version="1.0.0")

# 挂载 Daming OS HTTP 中间件自动注入 AgentContext 与事件追踪
try:
    from daming_os.middleware import DamingMiddleware
    app.add_middleware(DamingMiddleware)
    logger.info("🌐 [Daming OS 中间件挂载成功]: 已为 Web Dashboard 开启请求上下文与 Trace 关联")
except Exception as e:
    logger.warning(f"⚠️ [Daming OS 中间件挂载告警]: {e}")

base_dir = Path(__file__).parent
static_dir = base_dir / "static"
static_dir.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Agent 由宿主进程注入。这样 CLI、Web 与飞书可共享同一运行时，
# 而会话隔离仍由 SessionManager 按渠道和对话 ID 处理。
agent: LocalAgent | None = None


def configure_agent(agent_instance: LocalAgent) -> None:
    global agent
    agent = agent_instance


def get_agent() -> LocalAgent:
    if agent is None:
        raise RuntimeError("Web 管理后台尚未绑定 Agent 运行时。")
    return agent

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    index_file = static_dir / "index.html"
    if index_file.exists():
        return index_file.read_text(encoding="utf-8")
    return "<h1>Daming Agent Web Dashboard Initialization Error</h1>"

@app.get("/api/status")
async def get_status():
    """获取 Agent 运行状态、凭证与渠道状态。"""
    feishu_app_id = os.getenv("FEISHU_APP_ID", "")
    model_name = os.getenv("CLOUD_MODEL", "qwen3.7-plus")
    
    # 统计 skills 数量
    agents_skills_dir = base_dir / ".agents" / "skills"
    skills_count = len(list(agents_skills_dir.glob("*"))) if agents_skills_dir.exists() else 0

    return JSONResponse({
        "status": "online",
        "agent_name": "Daming Agent",
        "model": model_name,
        "super_admin": "Wenchen Ma (马文晨)",
        "feishu_configured": bool(feishu_app_id),
        "feishu_ws_status": "connected" if feishu_app_id else "disabled",
        "official_skills_count": skills_count,
        "memory_backend": "daming",
        "total_tokens_used": agent.token_tracker.get_summary()["global_totals"]["total_tokens"] if hasattr(agent, "token_tracker") else 0
    })

@app.get("/api/logs")
async def get_logs(limit: int = 200, level: str = ""):
    """获取 Agent 系统运行日志（从 logs/daming_app.log 读取）。"""
    logs = get_recent_logs(max_lines=limit, level_filter=level if level else None)
    return JSONResponse({"logs": logs, "total": len(logs)})

@app.get("/api/runtime")
async def get_runtime(limit: int = 100):
    """任务、审批与工具审计的统一运行视图。"""
    return JSONResponse(agent.runtime_store.summary(limit=limit))


@app.get("/api/daming/status")
async def get_daming_status():
    """Daming OS 闭环状态：共享 Adapter、待演化提案、质量阻断与能力缺口。"""
    return JSONResponse(get_agent().daming_status())


@app.post("/api/daming/quality/{run_id}")
async def review_daming_quality(run_id: str, request: Request):
    """独立复核高风险任务；不通过时继续保持质量门阻断。"""
    data = await request.json()
    if "passed" not in data:
        return JSONResponse({"ok": False, "error": "passed is required"}, status_code=400)
    return JSONResponse(get_agent().review_quality(run_id, bool(data["passed"]), str(data.get("note", ""))))

@app.get("/api/runtime/tasks")
async def get_runtime_tasks(session_id: str = "", limit: int = 100):
    return JSONResponse({"items": agent.runtime_store.tasks(session_id or None, limit)})

@app.get("/api/runtime/tasks/{task_id}")
async def get_runtime_task(task_id: str, session_id: str = ""):
    task = agent.runtime_store.get_task(task_id, session_id or None)
    return JSONResponse(task or {"error": "not found"}, status_code=200 if task else 404)

@app.get("/api/runtime/approvals")
async def get_runtime_approvals(session_id: str = "", limit: int = 100):
    return JSONResponse({"items": agent.runtime_store.approvals(session_id or None, limit)})

@app.get("/api/runtime/audit")
async def get_runtime_audit(session_id: str = "", limit: int = 100):
    return JSONResponse({"items": agent.runtime_store.audit_rows(session_id or None, limit)})

@app.get("/api/runtime/subagents")
async def get_subagents(session_id: str = "", limit: int = 100):
    return JSONResponse({"items": agent.runtime_store.subagents(session_id or None, limit)})

@app.get("/api/runtime/task-graphs")
async def get_task_graphs(session_id: str = "", limit: int = 100):
    return JSONResponse({"items": agent.runtime_store.task_graphs(session_id or None, limit)})

@app.get("/api/runtime/task-graphs/{graph_id}")
async def get_task_graph(graph_id: str, session_id: str = ""):
    try:
        return JSONResponse(agent.task_graph_manager.snapshot(graph_id, session_id or None))
    except ValueError:
        return JSONResponse({"error": "not found"}, status_code=404)

@app.get("/api/runtime/crons")
async def get_crons(session_id: str = "", limit: int = 100):
    return JSONResponse({"items": agent.runtime_store.cron_jobs(session_id or None, limit)})

@app.post("/api/runtime/crons/{cron_id}/{action}")
async def change_cron(cron_id: str, action: str, request: Request):
    data = await request.json()
    session_id = str(data.get("session_id", "")).strip()
    if not session_id or action not in {"pause", "resume", "delete"}:
        return JSONResponse({"ok": False, "error": "invalid request"}, status_code=400)
    ok = agent.cron_manager.delete(cron_id, session_id) if action == "delete" else agent.cron_manager.set_status(cron_id, session_id, action == "resume")
    return JSONResponse({"ok": ok})

@app.post("/api/runtime/subagents/{subagent_id}/cancel")
async def cancel_subagent(subagent_id: str, request: Request):
    data = await request.json(); session_id = str(data.get("session_id", "")).strip()
    return JSONResponse({"ok": bool(session_id) and agent.subagent_manager.cancel(subagent_id, session_id)})

@app.post("/api/approvals/{approval_id}")
async def resolve_approval(approval_id: str, request: Request):
    data = await request.json()
    if bool(data.get("approved")):
        return JSONResponse(agent.execute_approved(approval_id))
    ok = agent.reject_approval(approval_id)
    return JSONResponse({"ok": ok, "status": "rejected" if ok else None})

@app.get("/api/skills")
async def get_skills():
    """获取已挂载的 27 项飞书官方 Skills 列表。"""
    skills_dir = base_dir / ".agents" / "skills"
    skills_list = []
    if skills_dir.exists():
        for skill_path in sorted(skills_dir.glob("lark-*")):
            if skill_path.is_dir():
                skill_md = skill_path / "SKILL.md"
                desc = "飞书官方 AI Skill"
                if skill_md.exists():
                    lines = skill_md.read_text(encoding="utf-8").splitlines()
                    for line in lines[:10]:
                        if "description:" in line.lower():
                            desc = line.split(":", 1)[-1].strip()
                            break
                skills_list.append({
                    "name": skill_path.name,
                    "description": desc,
                    "type": "official_lark"
                })
    return JSONResponse({"skills": skills_list})

@app.post("/api/chat/stream")
async def chat_stream(request: Request):
    """Web 控制台极速流式打字对话接口。"""
    data = await request.json()
    user_prompt = data.get("prompt", "").strip()
    conversation_id = data.get("conversation_id", "").strip()
    if not user_prompt:
        return JSONResponse({"error": "Empty prompt"}, status_code=400)
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,80}", conversation_id):
        return JSONResponse({"error": "Invalid conversation_id"}, status_code=400)

    incoming = IncomingMessage(
        channel_name="web_dashboard",
        chat_id=conversation_id,
        user_id="super_admin",
        content=user_prompt,
        conversation_id=conversation_id,
        chat_type="web",
    )

    async def event_generator():
        chunk_queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def on_chunk(chunk: str):
            asyncio.run_coroutine_threadsafe(chunk_queue.put(chunk), loop)

        def run_agent():
            try:
                agent.reply_message_stream(incoming, on_chunk=on_chunk)
            finally:
                asyncio.run_coroutine_threadsafe(chunk_queue.put(None), loop)

        threading.Thread(target=run_agent, daemon=True).start()

        while True:
            chunk = await chunk_queue.get()
            if chunk is None:
                yield "data: [DONE]\n\n"
                break
            payload = json.dumps({"chunk": chunk}, ensure_ascii=False)
            yield f"data: {payload}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
