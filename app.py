import argparse
import os
import sys
import threading
import time
from pathlib import Path

# 自动挂载 src 源码目录支持模块查找
SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
AGENT_DIR = SRC_DIR / "daming_agent"
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from dotenv import load_dotenv

from daming_agent.agent import LocalAgent
from daming_agent.channels.cli_channel import CLIChannel
from daming_agent.channels.feishu_channel import FeishuChannel
from daming_agent.logger import get_logger, init_logging
from daming_agent.process_lock import ProcessLock

logger = get_logger("app")


def main() -> None:
    load_dotenv()
    init_logging()

    parser = argparse.ArgumentParser(description="Daming Agent 运行入口")
    parser.add_argument(
        "--server",
        action="store_true",
        help="以后台守护服务模式运行（开启飞书 Bot 常驻服务，无 CLI 交互中断）",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="仅以交互式终端客户端模式运行",
    )
    parser.add_argument(
        "--feishu",
        action="store_true",
        help="以独立常驻模式运行飞书 Bot",
    )

    args = parser.parse_args()

    # 默认模式处理：若未传任何参数，或显式传 --server，默认作为后台守护服务运行
    is_server_mode = args.server or (not args.cli and not args.feishu)
    daemon_mode = args.feishu or is_server_mode
    process_lock = None
    if daemon_mode:
        process_lock = ProcessLock(Path(__file__).resolve().parent / "logs" / "daming-agent.lock")
        if not process_lock.acquire():
            holder = f"（当前持有者 PID: {process_lock.holder_pid}）" if process_lock.holder_pid else ""
            logger.error(f"🛑 Daming Agent 守护服务已经在运行{holder}；本次启动已安全退出。")
            return

        logger.info(f"🔒 已获取 Daming Agent 守护服务单实例锁（PID: {os.getpid()}）。")

    agent = None

    try:
        agent = LocalAgent()

        # 1. 独立飞书 Bot 模式
        if args.feishu:
            logger.info("🚀 启动独立飞书 Bot 服务...")
            channel = FeishuChannel()
            channel.start(
                agent_callback=agent.reply_message,
                agent_stream_callback=agent.reply_message_stream,
                agent_control_callback=agent.control_conversation,
                agent_ingress_callback=agent.prepare_incoming_message,
                outbox_store=agent.outbox,
            )
            return

        # 2. 纯 CLI 终端对话模式
        if args.cli:
            logger.info("💬 启动单机终端 CLI 对话模式...")
            cli_channel = CLIChannel()
            cli_channel.start(
                agent_callback=agent.reply_message,
                agent_stream_callback=agent.reply_message_stream,
                agent_control_callback=agent.control_conversation,
                agent_ingress_callback=agent.prepare_incoming_message,
            )
            return

        # 尝试启动飞书渠道
        feishu_app_id = os.getenv("FEISHU_APP_ID", "").strip()
        feishu_app_secret = os.getenv("FEISHU_APP_SECRET", "").strip()

        if feishu_app_id and feishu_app_secret and not feishu_app_id.startswith("请在"):
            try:
                feishu_channel = FeishuChannel(app_id=feishu_app_id, app_secret=feishu_app_secret)
                feishu_thread = threading.Thread(
                    target=feishu_channel.start,
                    args=(agent.reply_message, agent.reply_message_stream, agent.control_conversation, agent.prepare_incoming_message, agent.outbox),
                    daemon=True,
                )
                feishu_thread.start()
                logger.info("🤖 [已接入]: 飞书 Bot 已在后台长连接线程启动。")
            except Exception as e:
                logger.warning(f"⚠️ [飞书 Bot 启动跳过/失败]: {e}")
        else:
            logger.info("💡 未配置有效飞书凭证，如需接入飞书请在 .env 中填写 FEISHU_APP_ID / SECRET。")

        # 3. Server 守护服务模式 (推荐默认)
        if is_server_mode:
            logger.info("==================================================")
            logger.info("🚀 Daming Agent 守护服务已进入常驻运行状态")
            logger.info("按 Ctrl+C 可停止 Agent 后台守护服务")
            logger.info("==================================================")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("🛑 收到终止信号，正在关闭服务...")
            return

    finally:
        if agent is not None:
            try:
                agent.close()
            except Exception as e:
                logger.warning(f"⚠️ Agent 关闭时发生异常: {e}")
        if process_lock is not None:
            try:
                process_lock.release()
            except Exception as e:
                logger.warning(f"⚠️ 守护服务单实例锁释放失败: {e}")
        logger.info("👋 Daming Agent 已安全退出。")


if __name__ == "__main__":
    main()

