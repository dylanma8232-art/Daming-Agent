# 🚀 Daming Agent - 工业级通用自主 AI Agent 框架
> **Industrial-Grade Universal Autonomous AI Agent Framework**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)
[![Release](https://img.shields.io/badge/release-v1.0.0-orange.svg)](https://github.com/dylanma8232-art/Daming-Agent/releases/tag/v1.0.0)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/dylanma8232-art/Daming-Agent/issues)

[中文](#-中文) | [English](#-english)

---

## 🇨🇳 中文

### 🏛️ 1. 框架简介与定位

**Daming Agent** 是一套模块化、高可靠、自带工业级防护与多代理编排的 **Python AI Agent 核心框架**。

它为开发者和团队提供了一套完整的 **Agent 运行时 (Runtime)**，解耦了模型层、记忆层、编排层、安全防护层与渠道层。不仅能在 **终端 CLI** 与 **飞书/Lark 群聊** 中作为自主数字员工运行，还能通过 SDK 快速集成到现有的 Python 项目中。

---

### ✨ 2. 核心优势与王牌亮点 (Key Advantages)

#### 🔀 中途实时插队干预 (Mid-Flight Live Steering)
长链条任务运行中途，用户可以通过飞书或 CLI 发送新消息实时打断“插队”。Agent **无需重启进程、无需丢历史上下文**，即可在当前节点在线无感“掉头”重新规划并接着执行。

#### 🛡️ MD5 行哈希防改砸编辑 (Hashline Precision Editing)
修改大文件前强制对目标代码段进行 **MD5 行签名校验**。当 LLM 提供的行号漂移时，系统自动拒绝写入并重新精确定位，从根本上杜绝“AI 改大文件改串行”的事故。

#### ⚡ 模型断连自动秒级熔断降级 (Automatic Failover)
主模型出现 504 超时或 5xx 报错时，系统自动捕获并在预设容灾链（如 Qwen ➔ Kimi ➔ DeepSeek）中**秒级无感降级切换至备用模型**，长流式任务 100% 保活。管理员可直接在对话中动态注册新模型。

#### 🛑 EnvLock 物理目录安全手刹 (Physical Safety Gate)
基于静态 AST 编译分析与物理路径加锁，拦截危险指令（如 `rm -rf`）与越权文件写入，严禁修改 `.env` 密钥或误删敏感目录。

#### 💬 全渠道与离线队列 (Universal Channels & Outbox)
原生支持 CLI 命令行终端与飞书 WebSocket 长连接机器人常驻（包含 300ms 动态防抖、单表情独占状态与交互卡片）。

---

### 🧠 3. 4 大认知引擎矩阵 (4 Cognitive Engines)

按任务复杂度与风险等级自动调度最优推理模式：

| 引擎类型 | 适合场景 | 运作机制 |
| :--- | :--- | :--- |
| **⚡ ReAct 引擎** | 简单问答与即时工具调用 | 思考-行动-观察极速循环 |
| **🕸️ TaskGraph DAG 引擎** | 跨模块复杂工程分解 | 规划与执行解耦，多节点依赖图编排 |
| **👑 Hierarchical Supervisor** | 多角色分工与独立审计 | 主控 (Plan) + Worker + 独立 Auditor 3层治理 |
| **🔍 Reflection / Hindsight** | 任务执行失败后复盘 | 自动总结踩坑教训，积累避错经验 |

---

### 💡 4. 解决什么工程问题？

- **消灭长任务跑偏失控**：消除跑偏后只能 `Ctrl+C` 强杀进程、作废前期 Token 和时间的痛点。
- **消灭代码改砸噩梦**：消除 LLM 修改大型代码文件时因行号漂移导致的代码改串行问题。
- **消灭 API 波动导致的前功尽弃**：消除长链条任务执行中途因模型 504 超时或断连导致的任务崩盘。

---

### 💻 5. 开发者 SDK 代码示例 (Developer Examples)

```python
from daming_agent import DamingAgent

# 初始化 DamingAgent
agent = DamingAgent()

# 运行任务
response = agent.reply_message_stream("分析当前项目结构并输出重构建议")
print(response.content)
```

---

### 📦 6. 安装与配置 (Quick Start)

```bash
# 1. 一键安装
pip install git+https://github.com/dylanma8232-art/Daming-Agent.git

# 2. 配置文件
cp .env.example .env
```

在 `.env` 中填写你的大模型 API Key（支持任何 OpenAI 兼容接口）：
```env
CLOUD_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
CLOUD_API_KEY=your_api_key_here
CLOUD_MODEL=qwen3.7-plus
```

启动：
```bash
python app.py
```

---

## 🇬🇧 English

### 🏛️ 1. Framework Overview

**Daming Agent** is a modular, decoupled Python **AI Agent Core Framework** equipped with multi-agent orchestration and industrial security guardrails.

It provides a complete Agent Runtime, decoupling LLM model routing, memory management, DAG orchestration, security policy, and multi-channel adapters. It operates autonomously in CLI and Feishu/Lark Workspaces, and can be integrated into any Python project via SDK.

---

### ✨ 2. Key Advantages

#### 🔀 Mid-Flight Live Steering
Interrupt and redirect a running agent mid-task via natural messages without process restarts or context loss.

#### 🛡️ Hashline Precision Editing
Mandatory MD5 line-checksum verification on every file edit prevents line-drift code corruption during large file refactoring.

#### ⚡ Automatic Model Failover
When the primary LLM times out (504) or fails (5xx), the system seamlessly failovers to backup model chains in seconds. Tasks stay 100% alive.

#### 🛑 EnvLock Physical Safety Gate
AST static analysis + physical directory locks prevent credential leaks (`.env`) and destructive shell commands.

#### 💬 Universal Channels & Outbox
Native support for CLI REPL terminal and Feishu/Lark WebSocket bots (with reaction state updates and interactive cards).

---

### 🧠 3. 4 Cognitive Engines

| Engine | Best For | Mechanism |
| :--- | :--- | :--- |
| **⚡ ReAct Engine** | Simple Q&A and instant tools | Rapid Reason-Act-Observe loop |
| **🕸️ TaskGraph DAG** | Complex multi-step engineering | Decoupled Plan & Parallel Execute DAG |
| **👑 Supervisor** | Multi-role & independent audit | Master (Plan) + Worker + Auditor 3-tier governance |
| **🔍 Reflection** | Post-failure analysis | Hindsight memory review & error avoidance |

---

### 💡 4. Problems Solved

- **Eliminates Uncontrollable Long Tasks**: No process killing required when tasks drift mid-flight.
- **Eliminates Code Edit Corruption**: MD5 line hashing guarantees zero code drift accidents.
- **Eliminates API Timeout Crashes**: Automatic failover chain keeps streaming tasks 100% alive.

---

### 💻 5. Developer SDK Example

```python
from daming_agent import DamingAgent

# Initialize DamingAgent
agent = DamingAgent()

# Stream response
response = agent.reply_message_stream("Analyze project structure and generate refactoring suggestions")
print(response.content)
```

---

### 📦 6. Installation & Setup

```bash
# 1. One-line Installation
pip install git+https://github.com/dylanma8232-art/Daming-Agent.git

# 2. Setup env
cp .env.example .env
```

Configure `.env`:
```env
CLOUD_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
CLOUD_API_KEY=your_api_key_here
CLOUD_MODEL=qwen3.7-plus
```

Run:
```bash
python app.py
```

---

## ⚖️ 许可证 License

[GNU AGPL v3.0](LICENSE) — 个人学习与非商业研究免费使用。商业产品集成或 SaaS 服务使用必须开源对应代码。

Free for non-commercial research. Commercial deployments require open-sourcing under AGPL.

## 🤝 社区 Community

欢迎提交 [GitHub Issues](https://github.com/dylanma8232-art/Daming-Agent/issues) 反馈问题或建议！
Found a bug or have an idea? Feel free to open an [Issue](https://github.com/dylanma8232-art/Daming-Agent/issues)!
