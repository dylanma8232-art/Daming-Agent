# Daming Agent

> 工业级通用自主 AI Agent 框架 | Industrial-Grade Universal Autonomous AI Agent Framework

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)
[![Release](https://img.shields.io/badge/release-v1.0.0-orange.svg)](https://github.com/dylanma8232-art/Daming-Agent/releases/tag/v1.0.0)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/dylanma8232-art/Daming-Agent/issues)

Daming Agent 是一个轻量、自主且高可靠的 Python AI Agent 框架。它支持单步思考 (ReAct)、多代理并发、DAG 任务编排与飞书机器人接入，同时具备代码防改砸、模型超时熔断与中途实时干预等工业级安全护栏。

---

## 🚀 快速上手 (Quick Start)

### 1. 安装 (Installation)
```bash
pip install git+https://github.com/dylanma8232-art/Daming-Agent.git
```

### 2. 配置 (Configuration)
```bash
cp .env.example .env
```

在 `.env` 中填写你的大模型 API Key（支持任何 OpenAI 兼容接口）：
```env
CLOUD_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
CLOUD_API_KEY=your_api_key_here
CLOUD_MODEL=qwen3.7-plus
```

### 3. 运行 (Usage)
```bash
python app.py
```

---

## ✨ 核心特性 (Key Features)

- 🔀 **中途实时干预 (Mid-Flight Steering)**：任务执行中可随时发消息调整方向，无需中断进程或丢失上下文。
- 🛡️ **MD5 行哈希防改砸 (Hashline Precision Editing)**：每次文件修改前校验目标代码段 MD5 行签名，杜绝 LLM 行号漂移导致的改串行。
- ⚡ **模型自动熔断降级 (Automatic Failover)**：模型 504 超时或断连时秒级无感切换至备用模型，长流式任务不崩溃。
- 🧠 **多模式认知引擎 (Multi-Engine Systems)**：支持 ReAct 即时循环、TaskGraph DAG 复杂任务编排与多子代理并发执行。
- 🛑 **物理安全手刹 (Safety Guardrails)**：静态 AST 编译安检 + 物理目录锁，严禁越权修改 sensitive 密钥或误删文件。
- 💬 **多渠道开箱即用 (Universal Channels)**：原生支持终端 CLI 交互与飞书 WebSocket 机器人常驻。

---

## 💻 开发者代码示例 (Developer Example)

```python
from daming_agent.agent import LocalAgent

# 初始化 Agent
agent = LocalAgent()

# 运行任务
response = agent.reply_message_stream("分析当前项目结构并输出重构建议")
print(response.content)
```

---

## 📄 许可证 (License)

[GNU AGPL v3.0](LICENSE) — 个人学习与非商业研究免费使用。商业产品集成或 SaaS 服务使用需开源相应代码。

Free for non-commercial research. Commercial deployments require open-sourcing under AGPL.

## 🤝 社区与贡献 (Community)

欢迎提 [GitHub Issues](https://github.com/dylanma8232-art/Daming-Agent/issues) 反馈问题或提交建议！
Found a bug or have an idea? Feel free to open an [Issue](https://github.com/dylanma8232-art/Daming-Agent/issues)!
