# 🚀 Daming Agent - 工业级通用自主 AI Agent 框架

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)
[![Release](https://img.shields.io/badge/release-v1.0.0-orange.svg)](https://github.com/dylanma8232-art/Daming-Agent/releases/tag/v1.0.0)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/dylanma8232-art/Daming-Agent/issues)

[中文介绍](#-中文介绍) | [English Documentation](#-english-documentation)

---

## 🇨🇳 中文介绍

### 💡 这个框架解决什么问题？

在真实复杂工程与自动化场景中，传统 AI Agent 常常面临三大痛点：
1. **中途纠偏难**：长链条任务跑偏时只能强杀进程重新开始，浪费时间与 Token。
2. **改代码容易改砸**：编辑大文件时因上下文行号漂移导致替换错位置。
3. **网络波动易崩溃**：大模型 API 超时或断联导致整个任务直接中途崩溃失败。

**Daming Agent 专门为解决上述工程痛点而生，提供安全防错、中途干预与高可用容灾能力。**

---

### ✨ 5 大核心亮点

#### 1. 🔀 中途实时插队干预 (Mid-Flight Live Steering)
长任务执行过程中，用户可以通过飞书或 CLI 发送消息实时插队。Agent **无需重启进程**，即可原地点无感“掉头”重新规划，已完成的工作完整保留。

#### 2. 🛡️ MD5 行哈希防改砸编辑 (Hashline Precision Editing)
每次修改代码文件前，强制对目标代码块进行 **MD5 行签名校验**。当行号漂移时自动拒绝写入并重新定位，从根本上杜绝 AI 修改文件改改砸的事故。

#### 3. ⚡ 模型超时自动熔断降级 (Automatic Model Failover)
主模型出现 504 超时或 5xx 报错时，系统按预设容灾链秒级无感切换至备用模型，任务不中断。管理员可以对话动态注册新模型。

#### 4. 🛑 EnvLock 物理安全手刹 (Physical Safety Gate)
静态 AST 编译级安检门 + 物理目录锁，拦截危险命令与越权文件写入，防范越狱攻击与误操作。

#### 5. 🧠 4 大认知引擎矩阵 (4 Cognitive Engines)
按任务复杂度自动调度最匹配的推理引擎：
- **ReAct**：轻量单步思考-行动循环
- **TaskGraph DAG**：解耦规划与执行，支持并发子任务
- **Hierarchical Supervisor**：主控 + Worker + 独立 Auditor 三层治理
- **Reflection / Hindsight**：任务失败自动复盘，持续积累避错经验

---

### 📦 一键安装与配置

```bash
# 一键安装
pip install git+https://github.com/dylanma8232-art/Daming-Agent.git

# 复制配置文件
cp .env.example .env
```

在 `.env` 中填写你的大模型 API Key：
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

### 💡 What Problems Does It Solve?

In real-world production and automation, AI Agents frequently encounter three failure modes:
1. **Inability to steer live tasks**: Getting off track forces a hard process kill, wasting time and tokens.
2. **Code edit corruption**: Large file edits fail due to LLM line-number drift.
3. **Fragile API connections**: Model timeouts or disconnects crash long-running workflows completely.

**Daming Agent is designed specifically to eliminate these bottlenecks with precision guardrails, live steering, and automatic failover.**

---

### ✨ Key Features

#### 1. 🔀 Mid-Flight Live Steering
Interrupt a running agent mid-task with new instructions via CLI or Feishu. The agent pivots immediately without process restarts or context loss.

#### 2. 🛡️ MD5 Hashline Precision Editing
Every file modification validates an MD5 checksum of the target lines. If line references drift, the edit is rejected and relocated automatically, ensuring zero file corruption.

#### 3. ⚡ Automatic Model Failover
When the primary LLM times out or returns 5xx errors, the system failovers to backup models seamlessly in seconds. Admins can dynamically register new models via prompt.

#### 4. 🛑 EnvLock Physical Safety Gate
Combines AST static inspection with directory physical locks to block unauthorized file edits and destructive terminal commands.

#### 5. 🧠 4 Cognitive Engines
Dynamically dispatches reasoning engines based on task complexity:
- **ReAct**: Fast single-step reasoning loop
- **TaskGraph DAG**: Decoupled planning & parallel execution
- **Hierarchical Supervisor**: Master-Worker-Auditor 3-tier governance
- **Reflection / Hindsight**: Automatic post-failure review & error avoidance

---

### 📦 Installation & Setup

```bash
# One-line installation
pip install git+https://github.com/dylanma8232-art/Daming-Agent.git

# Environment setup
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

## ⚖️ 许可证 / License

本项目采用 [GNU AGPL v3.0](LICENSE) 官方许可证开库。个人学习与非商业研究免费使用。商业产品集成或 SaaS 服务使用必须以 AGPL 协议开源相应代码。

Licensed under [GNU AGPL v3.0](LICENSE). Free for non-commercial research. Commercial deployments or SaaS integration require open-sourcing under AGPL.

## 🤝 开源共创 / Community

欢迎提交 [GitHub Issues](https://github.com/dylanma8232-art/Daming-Agent/issues) 反馈问题或建议！
Found a bug or have a suggestion? Feel free to open an [Issue](https://github.com/dylanma8232-art/Daming-Agent/issues)!
