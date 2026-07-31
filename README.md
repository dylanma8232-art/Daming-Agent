# 🚀 Daming Agent

**工业级通用自主 AI Agent 框架** | Industrial-Grade Autonomous AI Agent Framework

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Noncommercial-red.svg)](LICENSE)
[![v1.0.0](https://img.shields.io/badge/release-v1.0.0-orange.svg)](https://github.com/dylanma8232-art/Daming-Agent/releases/tag/v1.0.0)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/dylanma8232-art/Daming-Agent/issues)

---

## ✨ 核心亮点 Core Highlights

### 🔀 中途实时插队干预 · Mid-Flight Live Steering
任务执行中途，通过飞书或 CLI 发送消息即可让 Agent 立即调整方向，无需重启进程，已完成的工作完整保留。

### 🛡️ MD5 行哈希防改砸编辑 · Hashline Precision Editing
每次文件修改前对目标代码块进行 MD5 行签名校验，行号漂移时自动拒绝写入并重新定位，从根本上杜绝 AI 改代码改砸的事故。

### ⚡ 模型超时自动熔断降级 · Automatic Model Failover
主模型超时或断连时，自动按预设容灾链无感切换备用模型，长流式任务不中断。管理员可直接对话动态注册新模型，无需修改代码。

### 🛑 EnvLock 物理安全手刹 · Physical Safety Gate
AST 编译级静态安检 + 物理目录锁，拦截危险指令与越权文件操作，在高控制权与安全边界之间精确平衡。

### 🧠 4 大认知引擎 · 4 Cognitive Engines
按任务类型自动调度最优推理模式：
- **ReAct** — 单步思考-行动-观察，轻量即时
- **TaskGraph DAG** — 规划与执行解耦，支持并发子任务
- **Hierarchical Supervisor** — 主控 + Worker + 独立 Auditor 三层治理
- **Reflection / Hindsight** — 失败后自动复盘，持续积累避错经验

---

## 📦 安装

```bash
pip install git+https://github.com/dylanma8232-art/Daming-Agent.git
```

---

## ⚙️ 配置

复制配置模板并填入你的 API Key：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# 大模型接口（支持任意 OpenAI 兼容接口）
CLOUD_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
CLOUD_API_KEY=your_api_key_here
CLOUD_MODEL=qwen3.7-plus

# 飞书 Bot（可选）
FEISHU_APP_ID=your_feishu_app_id
FEISHU_APP_SECRET=your_feishu_app_secret
FEISHU_ADMIN_OPEN_ID=your_feishu_open_id
```

启动：

```bash
python app.py
```

---

## ⚖️ 许可证 License

[PolyForm Noncommercial License 1.0.0](LICENSE)：仅供个人学习与非商业研究使用，商业用途须获得书面授权。

## 🤝 共创 Community

欢迎提 [Issue](https://github.com/dylanma8232-art/Daming-Agent/issues) 反馈问题或建议，作者快速响应。
