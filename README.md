# 🚀 Daming Agent - 工业级通用自主 AI Agent 框架
> **Industrial-Grade Universal Autonomous AI Agent Framework**

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-PolyForm%20Noncommercial-red.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/dylanma8232-art/Daming-Agent/issues)

[中文版](#-中文版-项目核心王牌亮点) | [English Version](#-english-version-key-innovations)

---

## 🇨🇳 中文版 项目核心王牌亮点

区别于市面上绝大多数“只能单向线性执行、模型超时就崩溃、改代码容易砸”的传统 Agent 框架，**Daming Agent 拥有 5 大真正解决真实工程痛点的独家王牌特性**：

### 🔥 5 大独家核心亮点 (Core Innovations)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                      Daming Agent 5 大王牌工程突破                        │
├──────────────────────────────────────────────────────────────────────────┤
│ 1. 🔀 中途实时插队干预 (Mid-flight Steering): 任务执行中人类随时在线掉头   │
│ 2. 🛡️ MD5 行哈希防改砸 (Hashline Edits): 告别行号漂移导致的代码文件改改砸  │
│ 3. ⚡ 断线超时自动熔断降级 (Auto Failover): 模型断连/超时无感切换备份模型    │
│ 4. 🛑 EnvLock 物理防护手刹 (EnvLock Protection): 静态 AST 校验与越权防护   │
│ 5. 🧠 4 大认知引擎矩阵 (4 Cognitive Engines): ReAct / TaskGraph / Supervisor │
└──────────────────────────────────────────────────────────────────────────┘
```

#### 1. 🔀 中途实时插队干预 (Mid-Flight Steering) —— 告别“强杀进程重新跑”
- **真实痛点**：传统 Agent 一旦启动长链条任务（如重构整个项目或搜集长篇报告），执行中途如果您发现方向偏差或临时改变主意，只能强杀进程从头开始，浪费大量 Token 和时间。
- **独家突破**：在 Agent 思考与工具执行中途，人类可以在飞书/CLI 中随时**发送新消息或引用当前进度**直接插队！Agent 引擎接收干预信号后，**无需杀进程**，直接原地点无感“掉头”重新规划并接着执行。

#### 2. 🛡️ MD5 行哈希防改砸 (Hashline Precision Editing) —— 告别行号漂移改串行
- **真实痛点**：Agent 在修改大文件代码时，由于 LLM 提供的行号容易漂移，经常发生“改错行、替换错代码段、误删有用函数”的事故。
- **独家突破**：所有文件修改工具强制开启 **Hashline (MD5 行哈希校对)**。在写入前对目标代码块逐行比对 Hash 值，若发生行号漂移则自动拒绝替换并重新定位，**代码改砸概率直接降为 0**！

#### 3. ⚡ 模型断连超时自动熔断降级 (Automatic Failover) —— 任务 100% 保活
- **真实痛点**：使用云端 LLM API 时，遇到网络波动、504 超时或 API 限流，Agent 流程会直接报错崩溃崩溃退出。
- **独家突破**：超级管理员可动态注册多个备用模型（如 `qwen-plus` ➔ `kimi-k3` ➔ `deepseek-r1`）。当主模型发生超时或网络断开时，系统自动捕获并在容灾链中**秒级熔断并无感降级切换至备用模型**，确保长流式任务 100% 成功完成。

#### 4. 🛑 EnvLock 物理目录安全手刹 (EnvLock Physical Sandbox Guard)
- **真实痛点**：Agent 在命令行具备高控制权时，可能越权修改 `.env` 密钥文件或误删重要系统路径。
- **独家突破**：通过 AST 编译级安检门与 EnvLock 物理锁，严格限制修改敏感文件与危险命令，在保证 Agent 自主能力的同时提供工业级安检。

#### 5. 🧠 4 大认知引擎矩阵 + 分层 Supervisor 治理 (4 Cognitive Engine Matrix)
- 结合单步思考的 **ReAct 循环**、解耦规划与执行的 **TaskGraph DAG**、踩坑复盘的 **Reflection 反思引擎**，以及支持“主控-Worker-Auditor”3 层独立审计治理的 **Hierarchical Supervisor** 引擎。

---

### 🌟 亮点对比表 (Comparison)

| 维度 | 普通开源 Agent 框架 | 🚀 Daming Agent 框架 |
| :--- | :--- | :--- |
| **中途方向修正** | 只能 `Ctrl+C` 强杀进程重新开始 | 🔀 **实时消息插队，在线无感掉头** |
| **代码文件修改** | 容易行号漂移改错行、改砸源码 | 🛡️ **MD5 Hashline 行哈希防改砸校验** |
| **模型网络波动** | 报错崩溃，丢失全部上下文 | ⚡ **自动超时熔断，秒级降级备份模型** |
| **安全控制** | 无物理隔离，容易删改敏感文件 | 🛑 **EnvLock 物理手刹 + AST 静态安检** |
| **任务编排** | 单一 ReAct 或写死流程 | 🧠 **4 大认知引擎 (DAG / Supervisor / ReAct)** |

---

### ⚡ 5 分钟快速上手 (QuickStart)

```bash
# 1. 克隆仓库
git clone https://github.com/dylanma8232-art/Daming-Agent.git
cd Daming-Agent

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 填写你的 API Key

# 4. 启动 CLI 交互模式
python main.py
```

---

## 🇬🇧 English Version: Key Innovations

### 🔥 5 Breakthrough Innovations

1. 🔀 **Mid-Flight Live Steering**: Pivot your agent mid-execution via natural language messages without killing the process or losing accumulated context.
2. 🛡️ **Hashline Collision-Proof Edits**: Mandatory MD5 line-checksum verification prevents code drift corruption during large file refactoring.
3. ⚡ **Automatic Dynamic Model Failover**: Seamlessly switches to fallback LLM chains upon HTTP/API timeouts or 5xx disconnects.
4. 🛑 **EnvLock Physical Protection Gate**: AST static validation prevents unauthorized file modifications or credential leaks.
5. 🧠 **4 Cognitive Engine Suite**: Seamless switching between **ReAct**, **TaskGraph DAG**, **Reflection**, and **Hierarchical Supervisor** (Master-Worker-Auditor).

---

## ⚖️ 开源许可证 (License)

遵循 **[PolyForm Noncommercial License 1.0.0](LICENSE)** 协议：仅供个人学习、科研与非商业探索。未经授权严禁用于商业盈利或产品集成。

---

## 🤝 开源共创与 Community Co-Creation

欢迎提 [GitHub Issues](https://github.com/dylanma8232-art/Daming-Agent/issues) 或 Pull Requests！作者会快速响应修复。
