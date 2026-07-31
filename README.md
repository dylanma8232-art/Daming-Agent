# 🚀 Daming Agent —— 打破传统 Agent 框架天花板的 5 大独家突破
> **5 Engineering Breakthroughs No Other Agent Framework Has Done**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Noncommercial-red.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/dylanma8232-art/Daming-Agent/issues)
[![v1.0.0](https://img.shields.io/badge/release-v1.0.0-orange.svg)](https://github.com/dylanma8232-art/Daming-Agent/releases)

[中文版](#-5-大独家技术王牌-让你一眼看出区别) | [English](#-english-5-breakthrough-innovations)

---

## 🇨🇳 5 大独家技术王牌，让你一眼看出区别

市面上绝大多数 Agent 框架都存在 **"任务跑偏只能从头来、改大文件经常改砸、模型超时崩溃无法恢复"** 三大痛点。Daming Agent 用 5 项真正解决实际工程痛点的创新做到了它们做不到的事：

---

### 🔀 1. 中途实时插队干预 (Mid-Flight Live Steering)
**你们做不到的，我做到了。**

| 传统框架 | Daming Agent |
|:---|:---|
| 任务执行到一半发现方向跑偏 → 只能 `Ctrl+C` 杀掉进程，已做工作全部白费 | 直接在飞书/CLI 发一条消息，Agent **立即在线掉头**，不重启、不丢上下文、继续从当前状态执行 |

> 💬 举例：Agent 正在写报告写到一半，你突然改需求说"改成英文版"。不需要任何操作，发消息就行，Agent 下一步就已经切到了英文版方向。

---

### 🛡️ 2. MD5 行哈希防改砸编辑 (Hashline Collision-Proof Editing)
**永远告别"AI 帮我改代码反而改崩了"的噩梦。**

| 传统框架 | Daming Agent |
|:---|:---|
| LLM 给出的行号容易漂移 → 替换到了错误的代码行 → 文件改砸、逻辑混乱 | 修改前强制对目标代码块进行 **MD5 行签名校验**。哈希不对就拒绝写入、重新定位。改砸概率 = 0 |

---

### ⚡ 3. 断线超时自动熔断降级 (Automatic Model Failover)
**API 超时不等于任务失败。**

| 传统框架 | Daming Agent |
|:---|:---|
| 主模型 504 超时 → 进程崩溃，所有上下文丢失 | 自动捕获超时/5xx → 按熔断降级链**秒级无感切换备用模型**（如 qwen ➔ kimi ➔ deepseek）→ 任务继续 |

> 超级管理员可随时动态注册新模型：直接对 Agent 说"加一个 xxx 模型"即可，零代码修改。

---

### 🛑 4. EnvLock 物理目录安全手刹 (EnvLock Protection Gate)
**让 Agent 有能力的同时，绝对不越权。**

- AST 编译级静态安检门，在运行前拦截危险指令（如 `rm -rf`、修改 `.env` 密钥文件）。
- EnvLock 对核心目录加物理锁，即使 Agent 被"越狱"也无法越权破坏。

---

### 🧠 5. 4 大认知引擎矩阵 (4 Cognitive Engine Matrix)
**一个 Agent，4 种大脑模式，按任务复杂度自动切换。**

```
  简单问答/单步操作  →  ⚡ ReAct 引擎（即时思考-行动-观察极速循环）
  跨模块复杂工程    →  🕸️ TaskGraph DAG 引擎（规划与执行解耦，支持并发子任务）
  高风险/多角色工程  →  👑 Hierarchical Supervisor（主控-Worker-独立Auditor 三层治理）
  任务失败或完成后   →  🔍 Reflection 引擎（自动复盘踩坑，积累 Hindsight 避错经验）
```

---

## ⚡ 一键安装 (Install in One Line)

> 无需克隆代码，直接 pip 安装！

```bash
pip install git+https://github.com/dylanma8232-art/Daming-Agent.git
```

安装完成后，初始化配置并运行：

```bash
# 1. 复制配置模板
cp .env.example .env
# 编辑 .env，填入你的大模型 API Key（支持 OpenAI 兼容的任意接口）

# 2. 启动
daming-agent
```

> **支持任意 OpenAI 兼容接口**：阿里云百炼、Kimi、DeepSeek、OpenAI、本地 Ollama 均可直接使用。

---

## 🇬🇧 English: 5 Breakthrough Innovations

1. **🔀 Mid-Flight Live Steering** — Redirect a running agent mid-task via a simple message. No process restart, no lost context. Just pivot.
2. **🛡️ Hashline Collision-Proof Editing** — MD5 line-level checksum verification on every file edit. Code drift = 0. Corruption accidents = eliminated.
3. **⚡ Automatic Model Failover** — API timeout or 5xx error? The agent silently switches to a backup model chain in seconds, keeping tasks alive.
4. **🛑 EnvLock Physical Safety Gate** — AST-level static inspection + directory-level physical locks prevent credential leaks and unauthorized writes.
5. **🧠 4 Cognitive Engines** — Automatically selects the right thinking mode: ReAct, TaskGraph DAG, Hierarchical Supervisor, or Reflection.

```bash
# Install
pip install git+https://github.com/dylanma8232-art/Daming-Agent.git
```

---

## ⚖️ License

[PolyForm Noncommercial License 1.0.0](LICENSE) — Free for personal learning and research. **Commercial use requires explicit written authorization.**

## 🤝 Community

发现问题或有想法？欢迎提 [Issues](https://github.com/dylanma8232-art/Daming-Agent/issues)！作者亲自快速响应修复。
Found a bug or have an idea? Open an [Issue](https://github.com/dylanma8232-art/Daming-Agent/issues) — the author responds fast.
