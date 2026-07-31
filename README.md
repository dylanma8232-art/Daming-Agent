# 🚀 Daming Agent - 工业级通用自主 AI Agent 框架

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)
[![Release](https://img.shields.io/badge/release-v1.0.0-orange.svg)](https://github.com/dylanma8232-art/Daming-Agent/releases/tag/v1.0.0)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/dylanma8232-art/Daming-Agent/issues)

[中文](#-中文) | [English](#-english)

---

## 🇨🇳 中文

### 🏛️ 1. 框架全景架构

```
               【交互渠道: 终端 CLI / 飞书 WebSocket Bot】
                                  │
                                  ▼
               ┌──────────────────────────────────────┐
               │     🔀 中途实时插队干预控制器        │
               └──────────────────┬───────────────────┘
                                  │
                                  ▼
               ┌──────────────────────────────────────┐
               │    🧠 4 大认知引擎矩阵与动态路由器   │
               │ (ReAct / TaskGraph DAG / Supervisor) │
               └──────┬───────────┬───────────┬───────┘
                      │           │           │
          ┌───────────┴──┐   ┌────┴─────┐   ┌─┴────────────┐
          │ 🛡️ MD5 行哈希 │   │ ⚡ 自动超时 │   │ 🛑 EnvLock  │
          │  防改砸编辑器 │   │  熔断降级链│   │ 物理目录手刹 │
          └──────────────┘   └──────────┘   └──────────────┘
```

---

### ✨ 2. 核心亮点

- 🔀 **中途实时插队干预 (Mid-Flight Live Steering)**：长任务运行中随时发消息，Agent 在线实时掉头，不杀进程、不丢上下文。
- 🛡️ **MD5 行哈希防改砸 (Hashline Precision Editing)**：修改大文件前强制校验 MD5 行签名，杜绝 LLM 行号漂移导致的代码改砸事故。
- ⚡ **模型超时自动熔断降级 (Automatic Model Failover)**：主模型 504 超时或断连时，秒级无感切换至后备模型链，长流式任务 100% 保活。
- 🛑 **EnvLock 物理安全手刹 (Physical Safety Gate)**：静态 AST 编译安检 + 物理目录锁，严禁越权修改 `.env` 密钥或误删敏感路径。
- 🧠 **4 大认知引擎矩阵 (4 Cognitive Engines)**：按任务复杂度在 ReAct、TaskGraph DAG、Hierarchical Supervisor 与 Reflection 间自动调度。

---

### 💡 3. 解决什么问题

- **解决长任务跑偏失控**：消除传统 Agent 跑偏后只能 `Ctrl+C` 强杀进程、作废前期 Token 的痛点。
- **解决代码改砸噩梦**：消除 LLM 修改大型代码文件时因行号漂移导致的代码改串行问题。
- **解决 API 波动崩盘**：消除长链条任务执行中途因模型 504 超时或断连导致的前功尽弃问题。

---

### 📦 4. 安装与配置

```bash
# 一键安装
pip install git+https://github.com/dylanma8232-art/Daming-Agent.git

# 配置文件
cp .env.example .env
```

编辑 `.env`：
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

### 🏛️ 1. Framework Architecture

```
               [Channels: CLI Terminal / Feishu WebSocket Bot]
                                  │
                                  ▼
               ┌──────────────────────────────────────┐
               │    🔀 Mid-Flight Live Steering       │
               └──────────────────┬───────────────────┘
                                  │
                                  ▼
               ┌──────────────────────────────────────┐
               │    🧠 4 Cognitive Engine Matrix      │
               │ (ReAct / TaskGraph DAG / Supervisor) │
               └──────┬───────────┬───────────┬───────┘
                      │           │           │
          ┌───────────┴──┐   ┌────┴─────┐   ┌─┴────────────┐
          │ 🛡️ MD5 Hashline│   │ ⚡ Model  │   │ 🛑 EnvLock   │
          │ Precision Edit│   │ Failover │   │ Safety Gate  │
          └──────────────┘   └──────────┘   └──────────────┘
```

---

### ✨ 2. Key Highlights

- 🔀 **Mid-Flight Live Steering**: Redirect a running agent via natural messages mid-task. No process restart, no context loss.
- 🛡️ **Hashline Precision Editing**: Mandatory MD5 line-level checksum verification prevents line-drift code corruption during large file edits.
- ⚡ **Automatic Model Failover**: API timeout or 5xx disconnect? The agent seamlessly switches to backup LLM chains in seconds.
- 🛑 **EnvLock Physical Safety Gate**: AST static analysis + physical directory locks prevent credential leaks and unauthorized writes.
- 🧠 **4 Cognitive Engines**: Dynamically dispatches **ReAct**, **TaskGraph DAG**, **Supervisor**, or **Reflection** based on task complexity.

---

### 💡 3. Problems Solved

- **Eliminates Uncontrollable Long Tasks**: No need to kill processes when tasks drift.
- **Eliminates Code Edit Corruption**: MD5 line hashing guarantees zero code drift accidents.
- **Eliminates API Timeout Crashes**: Failover chain keeps streaming tasks 100% alive.

---

### 📦 4. Installation & Setup

```bash
pip install git+https://github.com/dylanma8232-art/Daming-Agent.git
cp .env.example .env
python app.py
```

---

## ⚖️ 许可证 License

[GNU AGPL v3.0](LICENSE) — 个人学习与非商业研究免费使用。商业产品集成或 SaaS 服务使用必须开源对应代码。

Free for non-commercial research. Commercial deployments require open-sourcing under AGPL.

## 🤝 社区 Community

欢迎提 [Issue](https://github.com/dylanma8232-art/Daming-Agent/issues) 反馈问题或建议！
Found a bug or have an idea? Feel free to open an [Issue](https://github.com/dylanma8232-art/Daming-Agent/issues)!
