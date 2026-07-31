import sys
from pathlib import Path

# 挂载 src 目录与 src/daming_agent 目录至 sys.path，保证单元测试零改动无缝运行
root_dir = Path(__file__).resolve().parents[1]
src_dir = root_dir / "src"
agent_dir = src_dir / "daming_agent"

if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
if str(agent_dir) not in sys.path:
    sys.path.insert(0, str(agent_dir))
