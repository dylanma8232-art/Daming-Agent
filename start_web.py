"""独立调试时的 Daming Agent 管理后台启动入口。"""
import uvicorn

from agent import LocalAgent
from web_server import app, configure_agent


if __name__ == "__main__":
    configure_agent(LocalAgent())
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
