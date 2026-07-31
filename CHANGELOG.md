# 📋 Daming Agent 迭代日志 (Changelog)

All notable changes to this project will be documented in this file.

## [v1.2.1] - 2026-07-31

### 💬 CLI 终端交互 UI 重构 (CLI Terminal UI Refactoring)
- **控制台日志隔离 (Log Noise Suppression)**：增加 `silence_console_logging()`，在 CLI 模式下静音标准输出的技术/路由/故障 Stack Trace，全量调试日志统一落盘存入 `logs/daming_app.log`。
- **单行动态 Spinner + 自动擦除 (Collapsible Status Bar)**：基于 ANSI `\r\033[K` 清行指令实现单行动态加载状态，在 Agent 开始回复文本时自动擦除中途状态，保持终端极简与纯净。
- **优雅降级 Notice**：熔断或故障自动降级时，输出淡黄色轻量提醒 Banner。

### 🧭 意图路由优化 (Intent Router Optimization)
- **通配通用浏览器能力挂载**：在 `IntentRouter` 中泛化网页与调研意图，消除死板具体的域名/特化网站硬编码词。
- **浏览器能力直通**：保证 `open_browser` 在涉及网页/调研场景下始终对模型可用，实现“只要模型看到工具就能自主推理并解决问题”的通用架构设计。

## [v1.2.0] - 2026-07-31

### ✨ 核心功能升级 (Core Features)

- **💾 会话历史磁盘隔离持久化 (Session History Disk Persistence)**
  - 实现基于 `session_id` 的短期对话历史持久化落地 (`sessions/{session_id}.json`)。
  - 支持多会话隔离加载、增量续写与重置清空 (`save_history`, `load_history`, `clear_history`)。
  - 自动对历史消息长度进行 100 轮安全截断保护，防止上下文无限膨胀。

- **🤖 浏览器人机协同干预 (Browser HITL - Human-In-The-Loop)**
  - **Playwright 反自动化检测防护**：注入 `--disable-blink-features=AutomationControlled` 与 `--test-type` 参数，移除默认自动化特征标。
  - **键盘仿真操控 (`press_key`)**：模拟人类键盘输入 (Enter / Tab / Escape / 方向键)，补齐表单提交与按键交互盲区。
  - **临时人工干预解除锁 (`request_human_intervention`)**：当遭遇扫码登录、人机图形验证码或极验校验时，临时解禁人类鼠标键盘控制，提示用户进行手工操作。
  - **AI 独占防干扰控制恢复 (`resume_agent_control`)**：人类操作完成后，一键恢复 Agent 物理悬浮防护与 DOM 独占运算。

- **🐦 飞书渠道 UI 与 Reaction 生命周期重构 (Feishu Channel Refactoring)**
  - **卡片精简呈现**：移除了飞书卡片顶栏 header，实现沉浸式与极简正文直接渲染。
  - **Reaction 动态回传**：收到用户消息后自动添加 `THINKING` (🤔) 表情，回复完成后自动清除，视觉化感知运行状态。
  - **媒体资源下载 (`download_message_resource`)**：实现飞书富文本中图片/文件资源向 Agent 工作区的无缝下载。

### 🧪 自动化测试套件 (Test Suite)
- 新增 `tests/test_browser_intervention_live.py`：在线测试浏览器人机协同及键盘操控。
- 新增 `tests/test_memory_persistence.py`：覆盖会话历史读写、落盘截断及清理逻辑。
- 全量测试套件 (74/74) 100% 通过。
