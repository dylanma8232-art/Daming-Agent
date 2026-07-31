"""渠道无关的 Agent 意图识别与能力路由。"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Intent(StrEnum):
    CHAT = "chat"
    RESEARCH = "research"
    FILE_WORK = "file_work"
    OFFICE_WORK = "office_work"
    BROWSER_INTERACTION = "browser_interaction"
    ORCHESTRATION = "orchestration"
    SCHEDULE = "schedule"
    CAPABILITY = "capability"
    EXTERNAL_CAPABILITY = "external_capability"
    MODEL_CONTROL = "model_control"
    TOKEN_STATS = "token_stats"
    LARK_OPERATION = "lark_operation"


@dataclass(frozen=True)
class IntentDecision:
    primary: Intent
    confidence: float
    tool_names: frozenset[str]


class IntentRouter:
    """唯一入口：用户消息 → 意图 → 本轮最小能力集。"""

    BASE_TOOLS = frozenset({
        "capability_search", "search_skills", "get_current_datetime",
        "manage_plan", "clarify", "calculate", "read_clipboard", "write_clipboard", "notify"
    })
    ROUTES: dict[Intent, tuple[tuple[str, ...], frozenset[str]]] = {
        Intent.EXTERNAL_CAPABILITY: (("外部", "external", "github", "lobehub", "安装skill", "安装 skill", "安装技能", "安装mcp", "安装 mcp", "安装tool", "安装 tool", "mcp", "插件", "增加能力", "增加技能", "创建技能", "添加技能", "新建技能", "新增技能", "创建skill", "添加skill", "增加skill", "新增skill", "扩展技能", "写一个技能", "写一个skill", "新建", "创建", "增加", "添加", "skill", "技能"), frozenset({"discover_external_capabilities", "acquire_external_skill", "acquire_external_mcp", "acquire_external_tool", "write_file", "list_files", "read_text_file"})),

        Intent.ORCHESTRATION: (("多代理", "子代理", "任务图", "并行", "拆分任务", "计划", "主从", "主控", "supervisor"), frozenset({"spawn_subagent", "spawn_parallel_subagents", "list_subagents", "get_subagent_result", "cancel_subagent", "create_task_graph", "create_supervisor_governance_graph", "dispatch_task_graph", "get_task_graph", "retry_task_graph_node", "add_task_graph_node", "rollback_task_graph", "manage_plan"})),

        Intent.BROWSER_INTERACTION: (("浏览器", "网页", "网站", "打开", "访问", "点击", "截图", "登录", "扫码", "填写表单", "图片", "图像"), frozenset({"open_browser", "click", "click_visual", "type_text", "screenshot", "close_browser", "analyze_image"})),
        Intent.RESEARCH: (("新闻", "搜索", "调研", "查一下", "检索", "网页", "网站", "web", "api", "http", "请求"), frozenset({"web_search", "fetch_webpage", "http_request", "open_browser"})),
        Intent.FILE_WORK: (("文件", "代码", "项目", "目录", "日志", "读取", "写入", "修改", "修复", "搜索文件", "查找内容", "grep", "删除", "移动", "重命名"), frozenset({"list_files", "read_text_file", "read_file_lines", "write_file", "append_file", "replace_file_content", "run_command", "search_files", "move_file", "delete_file"})),
        Intent.OFFICE_WORK: (("pdf", "word", "ppt", "excel", "文档", "表格", "幻灯片"), frozenset({"read_office_file", "create_word_document", "create_ppt_presentation", "create_pdf_document", "create_excel_spreadsheet"})),
        Intent.SCHEDULE: (("定时", "cron", "提醒", "通知"), frozenset({"create_cron", "list_cron_jobs", "pause_cron", "resume_cron", "delete_cron", "notify"})),
        Intent.MODEL_CONTROL: (("切换模型", "换模型", "使用模型", "新增模型", "添加模型", "注册模型", "/model", "什么模型", "用的什么模型", "当前模型", "哪种模型", "哪个模型"), frozenset({"register_model", "list_available_models", "get_session_model", "set_session_model"})),

        Intent.TOKEN_STATS: (("token", "消耗"), frozenset({"get_token_stats"})),
        Intent.LARK_OPERATION: (("飞书", "日历", "审批", "云盘", "lark"), frozenset({"lark_cli"})),
        Intent.CAPABILITY: (("能力", "技能", "skill", "工具"), frozenset({"view_skill", "discover_external_capabilities", "acquire_external_skill", "write_file"})),
    }


    def classify(self, message: str, *, selected_skills: bool = False) -> IntentDecision:
        text = message.lower().strip()
        active = {intent: sum(keyword in text for keyword in keywords) for intent, (keywords, _) in self.ROUTES.items()}
        active = {intent: score for intent, score in active.items() if score}
        primary = max(active, key=active.get) if active else Intent.CHAT
        tools = set(self.BASE_TOOLS)
        for intent in active:
            tools.update(self.ROUTES[intent][1])
        if selected_skills:
            tools.add("view_skill")
        confidence = 0.90 if not active else min(0.95, 0.55 + 0.15 * active[primary])
        return IntentDecision(primary, confidence, frozenset(tools))
