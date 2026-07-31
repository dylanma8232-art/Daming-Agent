import sys
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style

from channels.base import BaseChannel, IncomingMessage, OutgoingMessage


class CLIChannel(BaseChannel):
    """交互式终端渠道：历史、补全、多行输入和实时流式输出。"""

    _COMMANDS = ["/help", "/clear", "/new", "/stop", "/model", "/quit", "/exit"]

    def __init__(self) -> None:
        super().__init__(channel_name="cli")
        base_dir = Path(__file__).resolve().parent.parent
        history_path = base_dir / "workspace" / ".cli_history"
        history_path.parent.mkdir(parents=True, exist_ok=True)
        self._session = PromptSession(
            history=FileHistory(str(history_path)),
            completer=WordCompleter(self._COMMANDS, sentence=True),
            complete_while_typing=False,
            multiline=False,
            bottom_toolbar=self._bottom_toolbar,
            style=Style.from_dict({
                "prompt": "bold ansigreen",
                "bottom-toolbar": "bg:#1f2937 #d1d5db",
            }),
        )

    @staticmethod
    def _bottom_toolbar():
        return [("class:bottom-toolbar", " Enter 发送 · Tab 补全命令 · ↑↓ 历史 · Ctrl-R 搜索 · Ctrl-C 取消")]

    def start(self, agent_callback, agent_stream_callback=None, agent_control_callback=None, agent_ingress_callback=None) -> None:
        print("=== Daming Agent (CLI 终端标准渠道) 已启动 ===")
        print("输入 /help 查看说明，输入 /quit 退出对话。\n")

        while True:
            try:
                user_input = self._session.prompt([( "class:prompt", "你 > ")]).strip()
            except KeyboardInterrupt:
                print("\n输入已取消。")
                continue
            except EOFError:
                print("\n再见。")
                break

            if not user_input:
                continue
            if user_input == "/help":
                print("\n命令：/help、/clear、/new、/stop、/model、/quit 或 /exit")
                print("模型：/model 查看；/model primary|fast|fallback|auto 切换。")
                print("Enter 发送；Tab 补全命令；Ctrl-R 搜索历史。\n")
                continue
            if user_input == "/clear":
                print("\033[2J\033[H", end="", flush=True)
                continue
            if user_input in {"/quit", "/exit"}:
                print("再见。")
                break

            incoming = IncomingMessage(
                channel_name=self.channel_name,
                chat_id="cli_session",
                user_id="local_user",
                content=user_input,
                conversation_id="cli_session",
                chat_type="cli",
                raw_data={"delivery_id": f"cli-{__import__('uuid').uuid4().hex}"},
            )

            if user_input in {"/stop", "/new"}:
                if agent_control_callback:
                    agent_control_callback(incoming, "stop" if user_input == "/stop" else "new")
                print("\n已停止当前任务。\n" if user_input == "/stop" else "\n已开始新对话。\n")
                continue
            if agent_ingress_callback and not agent_ingress_callback(incoming):
                continue

            status_line_active = False
            printed_agent_prompt = False
            emitted_chunk = False

            def clear_status_line():
                nonlocal status_line_active
                if status_line_active:
                    sys.stdout.write("\r\033[K")
                    sys.stdout.flush()
                    status_line_active = False

            def print_chunk(chunk: str):
                nonlocal emitted_chunk, printed_agent_prompt
                clear_status_line()
                if not printed_agent_prompt:
                    sys.stdout.write("\n\033[1;32mAgent >\033[0m ")
                    printed_agent_prompt = True
                emitted_chunk = True
                sys.stdout.write(chunk)
                sys.stdout.flush()

            def status_handler(status_text: str):
                nonlocal status_line_active, printed_agent_prompt
                if printed_agent_prompt:
                    return
                clean_text = status_text.strip()
                if clean_text.startswith("⚠️"):
                    clear_status_line()
                    sys.stdout.write(f"\n\033[33m💡 {clean_text}\033[0m\n")
                    sys.stdout.flush()
                else:
                    sys.stdout.write(f"\r\033[K\033[90m⏳ [Agent] {clean_text}\033[0m")
                    sys.stdout.flush()
                    status_line_active = True

            if agent_stream_callback:
                try:
                    import inspect
                    sig = inspect.signature(agent_stream_callback)
                    accepts_status = "on_status" in sig.parameters
                except Exception:
                    accepts_status = False

                if accepts_status:
                    outgoing: OutgoingMessage = agent_stream_callback(incoming, on_chunk=print_chunk, on_status=status_handler)
                else:
                    outgoing: OutgoingMessage = agent_stream_callback(incoming, on_chunk=print_chunk)

                clear_status_line()
                if outgoing.content and not emitted_chunk:
                    if not printed_agent_prompt:
                        sys.stdout.write("\n\033[1;32mAgent >\033[0m ")
                        printed_agent_prompt = True
                    sys.stdout.write(outgoing.content)
                    sys.stdout.flush()
            else:
                outgoing: OutgoingMessage = agent_callback(incoming)
                clear_status_line()
                if not printed_agent_prompt:
                    sys.stdout.write("\n\033[1;32mAgent >\033[0m ")
                    printed_agent_prompt = True
                sys.stdout.write(outgoing.content)
                sys.stdout.flush()

            if printed_agent_prompt or emitted_chunk or outgoing.content:
                print("\n")
            if outgoing.media_files:
                print(f"📎 [生成附件路径]: {', '.join(outgoing.media_files)}\n")

    def send_message(self, chat_id: str, message: OutgoingMessage) -> bool:
        print(f"\nAgent > {message.content}\n")
        if message.media_files:
            print(f"📎 [生成附件路径]: {', '.join(message.media_files)}\n")
        return True

    def add_reaction(self, chat_id: str, message_id: str, reaction_type: str) -> bool:
        return True

