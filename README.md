# 🚀 Daming Agent - 工业级通用自主 AI Agent 框架
> **Industrial-Grade Universal Autonomous AI Agent Framework**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)
[![Release](https://img.shields.io/badge/release-v1.0.0-orange.svg)](https://github.com/dylanma8232-art/Daming-Agent/releases/tag/v1.0.0)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/dylanma8232-art/Daming-Agent/issues)

[中文介绍](#-中文介绍) | [English Documentation](#-english-documentation)

---

## 🇨🇳 中文介绍

### 💡 Daming Agent 到底是什么？

**Daming Agent** 是一套部署在你的电脑或服务器上的**全能自主 AI 助手框架**。

它不仅能在 **终端 CLI、Web 控制台以及飞书/Lark 群聊** 里与你实时对话，还能像一个真实的资深程序员与数字员工一样，**自主写代码改项目、运行 Bash 命令、控制浏览器抓取网页、处理 Office 文档**，并具备工业级的防改砸与断线容灾护栏。

```
                       ┌────────────────────────────────────────┐
                       │          你的交互终端            │
                       │   CLI / Web 控制台 / 飞书 Bot    │
                       └───────────────────┬────────────────────┘
                                           │
                                           ▼
                       ┌────────────────────────────────────────┐
                       │       Daming Agent 核心自主引擎       │
                       │   (ReAct / TaskGraph / Supervisor)     │
                       └─────┬─────────────┬─────────────┬──────┘
                             │             │             │
              ┌──────────────┴──┐   ┌──────┴──────┐   ┌──┴──────────────┐
              │ 💻 本地代码与文件 │   │ 🌐 浏览器操控 │   │ 📄 文档与数据处理│
              │  读写/重构/跑测试 │   │ Web 抓取/自动化│   │ PDF/Word/Excel  │
              └─────────────────┘   └─────────────┘   └─────────────────┘
```

---

### 🛠️ 你可以用它做什么？

* 💻 **自主代码重构与项目开发**：自动阅读代码库、定位 Bug、重构代码、运行 `pytest` 验证测试。
* 🌐 **网页自动化与深度抓取**：无需人工干预，自动使用无头浏览器操控网页、搜集资料并生成总结。
* 📄 **Office 文档与数据批量处理**：解析或导出 PDF、Word (.docx)、Excel (.xlsx)、PPT (.pptx) 数据报表。
* 📡 **团队飞书数字员工 (Feishu Bot)**：支持 WebSocket 免公网 IP 接入飞书群聊与私聊，带单表情状态与交互卡片。
* 🧠 **复杂多步骤长任务编排**：自动将大型任务拆解为 DAG 任务图，分发多个子 Agent 并行处理。

---

### 🔥 5 大独家安全与工程护栏

普通 Agent 框架在处理真实复杂任务时，经常面临“改砸代码”、“中途跑偏只能重来”、“API 超时直接崩溃”的困境。Daming Agent 提供了 5 项工业级突破：

| 突破特性 | 解决了什么问题？ |
| :--- | :--- |
| 🔀 **中途实时插队干预** | 任务执行中途发现方向偏差，直接发消息即可在线干预“掉头”，**无需强杀进程**，已做工作完全保留。 |
| 🛡️ **MD5 行哈希防改砸** | 写入大文件前强制校验目标代码块 MD5 行签名，上下文漂移时自动拒绝并定位，**代码改砸率归零**。 |
| ⚡ **模型断连自动熔断降级** | API 超时或 5xx 故障时，秒级无感切换至后备模型链（如 Qwen ➔ Kimi ➔ DeepSeek），长任务绝不崩溃。 |
| 🛑 **EnvLock 物理防护手刹** | 静态 AST 编译安检 + 物理目录锁，严禁越权修改 `.env` 密钥或误删敏感文件。 |
| 🧠 **4 大认知引擎矩阵** | 根据任务复杂度在 **ReAct**（单步）、**TaskGraph**（DAG）、**Supervisor**（主从审计）与 **Reflection** 间自由切换。 |

---

### 📦 一键安装与快速上手

```bash
# 1. 一键安装
pip install git+https://github.com/dylanma8232-art/Daming-Agent.git

# 2. 复制配置文件
cp .env.example .env
```

在 `.env` 中配置你的 API Key（支持任何 OpenAI 兼容接口，如阿里云百炼、DeepSeek、Kimi 等）：
```env
CLOUD_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
CLOUD_API_KEY=your_api_key_here
CLOUD_MODEL=qwen3.7-plus
```

启动 Agent：
```bash
python app.py
```

---

## 🇬🇧 English Documentation

### 💡 What is Daming Agent?

**Daming Agent** is an **industrial-grade autonomous AI assistant framework** deployed on your local machine or server.

It interacts with you seamlessly across **CLI, Web Dashboard, and Feishu/Lark Workspace**, while autonomously **writing/refactoring code, executing shell commands, operating headless browsers, processing office documents**, and orchestrating multi-agent workflows.

---

### 🛠️ Key Capabilities

* 💻 **Autonomous Code Engineering**: Reads repositories, debugs issues, edits code safely, and runs tests automatically.
* 🌐 **Browser & Web Automation**: Operates headless browsers via Playwright for deep research and data scraping.
* 📄 **Document Processing**: Parses and generates PDF, Word (.docx), Excel (.xlsx), and PowerPoint (.pptx) reports.
* 📡 **Feishu/Lark Bot Integration**: Enterprise WebSocket long-connection integration with reactions and interactive cards.
* 🧠 **Multi-Agent DAG Orchestration**: Deconstructs complex goals into TaskGraph DAGs executed by parallel sub-agents.

---

### 🔥 5 Engineering Breakthroughs

* 🔀 **Mid-Flight Steering**: Interrupt and redirect a running agent via natural messages without process restarts.
* 🛡️ **Hashline Precision Editing**: Mandatory MD5 line-checksum verification prevents code drift corruption.
* ⚡ **Automatic Model Failover**: Seamlessly switches to backup LLM chains upon HTTP/API timeouts or 5xx failures.
* 🛑 **EnvLock Protection Gate**: AST static analysis + physical directory locks prevent credential leaks and bad writes.
* 🧠 **4 Cognitive Engines**: Dynamically switches between **ReAct**, **TaskGraph DAG**, **Supervisor**, and **Reflection**.

---

### 📦 Quick Start

```bash
# Installation
pip install git+https://github.com/dylanma8232-art/Daming-Agent.git

# Copy environment config
cp .env.example .env
```

Configure your `.env` (supports any OpenAI-compatible API):
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

## ⚖️ 许可证 / License

本项目采用 [GNU AGPL v3.0](LICENSE) 许可证开源。个人学习与研究免费。商业产品集成或 SaaS 使用必须开源对应代码。

Licensed under [GNU AGPL v3.0](LICENSE). Free for non-commercial research. Commercial/SaaS deployments require open-sourcing under AGPL.

## 🤝 开源共创 / Community

欢迎提交 [GitHub Issues](https://github.com/dylanma8232-art/Daming-Agent/issues) 反馈 Bug 或建议！
Found a bug or have an idea? Feel free to open an [Issue](https://github.com/dylanma8232-art/Daming-Agent/issues)!
