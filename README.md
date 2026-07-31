# 🚀 Daming Agent

**工业级通用自主 AI Agent 框架**
**Industrial-Grade Autonomous AI Agent Framework**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)
[![Release](https://img.shields.io/badge/release-v1.0.0-orange.svg)](https://github.com/dylanma8232-art/Daming-Agent/releases/tag/v1.0.0)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/dylanma8232-art/Daming-Agent/issues)

---

## 这个框架解决什么问题？ / What Problems Does It Solve?

**中文**：现有的 Agent 框架在真实生产场景中面临三个核心痛点：
- **任务跑偏没有办法中途纠正**，只能杀掉进程从头开始
- **修改大文件代码时容易因行号漂移而改错位置**，导致文件改砸
- **模型 API 超时或断连后整个任务直接崩溃**，无法恢复

Daming Agent 专门为解决这三个问题而设计，同时提供企业级的安全防护与灵活的多引擎推理架构。

**English**: Most agent frameworks fail in production for three core reasons:
- **No way to steer a running task** without killing the process
- **Code edits corrupt files** when the LLM's line references drift
- **Tasks crash permanently** when an API times out or disconnects

Daming Agent is built to eliminate all three, while adding enterprise-grade safety guardrails and a flexible multi-engine reasoning system.

---

## ✨ 5 大核心亮点 / 5 Core Innovations

### 🔀 中途实时插队干预 · Mid-Flight Live Steering
任务进行到一半，你直接在飞书或 CLI 发一条消息，Agent 立刻调整方向，已完成的工作全部保留，零重启零中断。

> A running task goes wrong halfway through? Just send a message. The agent pivots immediately — no restart, no lost context, no wasted work.

---

### 🛡️ MD5 行哈希防改砸编辑 · Hashline Precision Editing
每次修改代码文件前，强制对目标代码块进行 MD5 行哈希校验。如果 LLM 返回的行号已经漂移，系统自动拒绝写入并重新精确定位，从根本上杜绝"AI 帮我改代码反而改砸了"。

> Before every file edit, the system verifies an MD5 hash of the exact target lines. If the LLM's line reference has drifted, the write is rejected and re-targeted. Code corruption = 0.

---

### ⚡ 模型超时自动熔断降级 · Automatic Model Failover
主模型出现 504 超时或 5xx 错误时，系统自动捕获异常，按预设的容灾链（如 qwen → kimi → deepseek）秒级无感切换备用模型，长流式任务不会中断。管理员可直接和 Agent 说话来动态注册新模型，零代码修改。

> When the primary model hits a timeout or 5xx, the system silently switches to the next model in the failover chain. Tasks keep running. Admins can register new models just by talking to the agent.

---

### 🛑 EnvLock 物理安全手刹 · Physical Safety Gate
AST 编译级静态安检门，在执行前拦截危险指令（如删除密钥文件）。物理目录锁对核心路径加锁，保障 Agent 即使在高控制权下也不会越权破坏系统。

> AST-level static inspection intercepts dangerous commands before execution. Physical directory locks prevent unauthorized writes, even if the agent is manipulated into trying.

---

### 🧠 4 大认知引擎矩阵 · 4 Cognitive Engines
按任务类型自动调度最适合的推理模式：

| 场景 | 引擎 | 描述 |
|:--|:--|:--|
| 简单问答与即时操作 | ⚡ ReAct | 思考-行动-观察极速循环 |
| 跨模块复杂工程 | 🕸️ TaskGraph DAG | 规划执行解耦，支持并发子任务 |
| 多角色协作与独立审计 | 👑 Hierarchical Supervisor | 主控 + Worker + 独立 Auditor 三层治理 |
| 任务失败后的经验积累 | 🔍 Reflection / Hindsight | 自动复盘，持续积累避错经验 |

> The right reasoning engine is selected automatically based on task complexity — from instant ReAct loops to full Supervisor-Worker-Auditor governance for high-stakes engineering.

---

## 📦 安装 / Installation

```bash
pip install git+https://github.com/dylanma8232-art/Daming-Agent.git
```

---

## ⚙️ 配置 / Configuration

```bash
cp .env.example .env
```

编辑 `.env` 填入你的配置 / Edit `.env` with your settings:

```env
# 大模型接口（支持任意 OpenAI 兼容接口，包括阿里云百炼、Kimi、DeepSeek 等）
# LLM API — supports any OpenAI-compatible endpoint
CLOUD_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
CLOUD_API_KEY=your_api_key_here
CLOUD_MODEL=qwen3.7-plus

# 飞书 Bot（可选 / Optional）
FEISHU_APP_ID=your_feishu_app_id
FEISHU_APP_SECRET=your_feishu_app_secret
FEISHU_ADMIN_OPEN_ID=your_feishu_open_id
```

启动 / Start:

```bash
python app.py
```

---

## ⚖️ 许可证 / License

[GNU AGPL v3.0](LICENSE) — 开源免费用于个人学习与非商业研究。任何将本框架用于商业产品或 SaaS 服务的，须将其产品代码全部以 AGPL 协议开源。

> Free for personal learning and open-source research. Any commercial product or SaaS built with this framework must also be open-sourced under AGPL v3.

## 🤝 共创 / Community

发现 Bug 或有功能建议？欢迎提 [Issue](https://github.com/dylanma8232-art/Daming-Agent/issues)，作者快速响应。
Found a bug or have an idea? Open an [Issue](https://github.com/dylanma8232-art/Daming-Agent/issues).
