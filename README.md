# 🚀 Daming Agent - 工业级通用自主 AI Agent 框架
> **Industrial-Grade Universal Autonomous AI Agent Framework**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)
[![Release](https://img.shields.io/badge/release-v1.0.0-orange.svg)](https://github.com/dylanma8232-art/Daming-Agent/releases/tag/v1.0.0)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/dylanma8232-art/Daming-Agent/issues)

[中文介绍](#-中文介绍) | [English Documentation](#-english-documentation)

---

## 🇨🇳 中文介绍

### 💡 为什么需要 Daming Agent？（核心独特价值）

通用 Agent 框架（如 LangChain、AutoGPT）通常只停留在“工具调用”层面，但在真正的复杂工程与生产落地上，往往会因为以下 3 个**致命死穴**而无法使用：

1. **长任务不可控**：长链条任务一旦跑偏，用户只能 `Ctrl+C` 强杀进程，前期消耗的 Token 和时间全部作废。
2. **改代码改砸率极高**：修改数百行大文件时，LLM 给出的行号稍有漂移，就会把代码替换串行、破坏项目结构。
3. **API 波动易前功尽弃**：跑了十几步复杂任务，突然遭遇模型 504 超时或限流，进程崩溃直接导致整个任务失败。

**Daming Agent 不仅是一个 Agent 执行器，更是一套专门为“防改砸、长任务可控、高可用保活”而生的工业级 Agent 安全与容灾底座。**

```
                     ┌────────────────────────────────────────┐
                     │       用户请求 / 飞书消息 / CLI       │
                     └───────────────────┬────────────────────┘
                                         │
                     ┌───────────────────▼────────────────────┐
                     │ 🔀 中途实时插队干预控制器              │ ➔ (长任务在线随时掉头，不杀进程不丢上下文)
                     └───────────────────┬────────────────────┘
                                         │
                     ┌───────────────────▼────────────────────┐
                     │ 🧠 4大认知引擎 + 动态路由器            │ ➔ (ReAct / TaskGraph DAG / Supervisor / Reflection)
                     └─────┬─────────────┬─────────────┬──────┘
                           │             │             │
            ┌──────────────┴──┐   ┌──────┴──────┐   ┌──┴──────────────┐
            │ 🛡️ MD5 行哈希   │   │ ⚡ 自动超时  │   │ 🛑 EnvLock 物理 │
            │  防改砸编辑器   │   │  熔断降级链 │   │  目录安全手刹   │
            │(行号漂移自动定位│   │(断线秒切备用│   │(AST静态安检锁死 │
            │ 改砸概率彻底归零│   │ 任务100%保活│   │ 敏感密钥与路径) │
            └─────────────────┘   └─────────────┘   └─────────────────┘
```

---

### 🔥 4 大王牌工程护栏（为什么与其他 Agent 不同）

#### 1. 🔀 中途实时插队干预 (Mid-Flight Live Steering) —— 解决“长任务控制死穴”
- **痛点**：Agent 执行长任务到一半，你发现它理解稍微偏了，或者你临时想调整需求，传统框架只能强杀进程重来。
- **突破**：可以在 Agent 正在思考和执行工具的过程中，直接在飞书/CLI 发消息打断“插队”。Agent **无需杀进程、无需丢上下文**，直接原地无感“掉头”重新规划并接着执行。

#### 2. 🛡️ MD5 行哈希防改砸编辑 (Hashline Precision Editing) —— 解决“AI改代码改砸噩梦”
- **痛点**：普通 Agent 帮你在大型文件里改代码时，由于 LLM 提供的行号容易漂移，极其容易把代码改串行或删掉非目标函数。
- **突破**：所有的写代码与文件替换操作，强制进行 **MD5 行签名校验 (Hashline)**。替换前对目标代码块逐行比对 Hash 值，行号漂移时自动拒绝写入并精准重新定位，**代码改砸概率彻底降为 0**！

#### 3. ⚡ 模型断连自动秒级熔断降级 (Automatic Failover) —— 解决“API超时崩溃死穴”
- **痛点**：跑复杂任务跑了 15 步，第 16 步遇到模型 504 超时或 API 限流，传统 Agent 直接报错崩溃退出。
- **突破**：管理员可配置容灾模型链（如 Qwen ➔ Kimi ➔ DeepSeek）。当主模型发生超时或网络断开时，系统自动捕获并**秒级无感降级切换至备用模型**，长流式任务 100% 成功保活。

#### 4. 🛑 EnvLock 物理目录安全手刹 (Physical Safety Gate) —— 解决“越权改删危险”
- **痛点**：给 Agent 高控制权时，它可能被 Prompt 越狱或因操作失误修改 `.env` 密钥文件或误删重要目录。
- **突破**：内置静态 AST 编译级安检门与 EnvLock 物理锁，对关键路径与危险 Shell 指令加锁，确保自主能力的同时提供安全底线。

---

### 📊 核心能力对比 (Comparison)

| 维度 | 普通开源 Agent 框架 | 🚀 Daming Agent 框架 |
| :--- | :--- | :--- |
| **长任务跑偏纠正** | 只能 `Ctrl+C` 强杀进程，全部重来 | 🔀 **实时消息插队，在线无感掉头** |
| **大文件代码修改** | 容易行号漂移改错行、改砸源码 | 🛡️ **MD5 Hashline 行哈希校对，改砸率归零** |
| **模型 API 504 超时**| 报错崩溃，丢弃所有历史上下文 | ⚡ **秒级无感熔断降级，自动切换备用模型** |
| **安全手刹** | 无物理隔离，容易删改敏感文件 | 🛑 **EnvLock 物理锁 + AST 编译级安检** |
| **任务推理架构** | 单一 ReAct 或固定写死流程 | 🧠 **4 大认知引擎自动调度 (ReAct / DAG / Supervisor)** |

---

### 📦 一键安装与配置

```bash
# 1. 一键安装
pip install git+https://github.com/dylanma8232-art/Daming-Agent.git

# 2. 复制配置文件
cp .env.example .env
```

在 `.env` 中填写你的大模型 API Key（支持任何 OpenAI 兼容接口）：
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

### 💡 Why Daming Agent? (Core Value Proposition)

Generic agent frameworks often fail in real-world engineering due to three critical flaws:
1. **Uncontrollable long tasks**: Mid-task direction shifts require killing the process and wasting tokens.
2. **Code edit corruption**: Large file edits fail due to LLM line-number drift.
3. **Fragile API connections**: Model 504 timeouts or rate limits crash long-running workflows completely.

**Daming Agent is an industrial-grade Agent safety & fault-tolerance engine built for zero code corruption, live task steering, and automatic failover.**

```
                     ┌────────────────────────────────────────┐
                     │      User Prompt / Feishu / CLI        │
                     └───────────────────┬────────────────────┘
                                         │
                     ┌───────────────────▼────────────────────┐
                     │ 🔀 Mid-Flight Live Steering Controller │ ➔ (Pivot mid-task live, no process kill)
                     └───────────────────┬────────────────────┘
                                         │
                     ┌───────────────────▼────────────────────┐
                     │ 🧠 4 Cognitive Engines + Router         │ ➔ (ReAct / TaskGraph DAG / Supervisor / Reflection)
                     └─────┬─────────────┬─────────────┬──────┘
                           │             │             │
            ┌──────────────┴──┐   ┌──────┴──────┐   ┌──┴──────────────┐
            │ 🛡️ MD5 Hashline │   │ ⚡ Automatic │   │ 🛑 EnvLock      │
            │ Precision Edit  │   │ Model Failover│   │ Safety Gate     │
            │(Zero code drift)│   │(100% task stay│   │(AST static check│
            │ Zero corruption │   │ alive on 504) │   │ physical locks) │
            └─────────────────┘   └─────────────┘   └─────────────────┘
```

---

### 🔥 4 Core Innovations

#### 1. 🔀 Mid-Flight Live Steering
Interrupt a running agent mid-task via natural messages. The agent pivots immediately without process restarts or context loss.

#### 2. 🛡️ MD5 Hashline Precision Editing
Every file modification validates an MD5 checksum of target lines. If line references drift, the edit is rejected and relocated automatically — ensuring zero code corruption.

#### 3. ⚡ Automatic Model Failover
When the primary LLM times out or fails with 5xx errors, the system failovers to backup model chains seamlessly in seconds. Tasks stay 100% alive.

#### 4. 🛑 EnvLock Physical Safety Gate
Combines AST static inspection with directory physical locks to block unauthorized file edits and destructive terminal commands.

---

### 📦 Quick Start

```bash
# Installation
pip install git+https://github.com/dylanma8232-art/Daming-Agent.git

# Setup env
cp .env.example .env
```

Configure `.env` (supports any OpenAI-compatible API):
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
