import sys
from pathlib import Path
import uvicorn

SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
AGENT_DIR = SRC_DIR / "daming_agent"
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from daming_agent.agent import LocalAgent
from daming_agent.web_server import app, configure_agent


if __name__ == "__main__":
    configure_agent(LocalAgent())
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)

