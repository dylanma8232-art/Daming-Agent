import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

APP_LOG_FILE = LOGS_DIR / "daming_app.log"
ERROR_LOG_FILE = LOGS_DIR / "daming_error.log"


class ColoredConsoleFormatter(logging.Formatter):
    """带 ANSI 颜色的终端日志格式化器。"""

    COLOR_CODES = {
        logging.DEBUG: "\033[36m",     # 青色
        logging.INFO: "\033[32m",      # 绿色
        logging.WARNING: "\033[33m",   # 黄色
        logging.ERROR: "\033[31m",     # 红色
        logging.CRITICAL: "\033[35m",  # 紫色
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLOR_CODES.get(record.levelno, self.RESET)
        time_str = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        level_name = f"{color}[{record.levelname:<7}]{self.RESET}"
        logger_name = f"\033[34m[{record.name}]\033[0m"
        message = record.getMessage()

        formatted = f"{time_str} {level_name} {logger_name} {message}"
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        return formatted


class SafeStreamHandler(logging.StreamHandler):
    def handleError(self, record: logging.LogRecord) -> None:
        pass

    def emit(self, record: logging.LogRecord) -> None:
        try:
            super().emit(record)
        except Exception:
            pass


class SafeRotatingFileHandler(RotatingFileHandler):
    def handleError(self, record: logging.LogRecord) -> None:
        pass

    def emit(self, record: logging.LogRecord) -> None:
        try:
            super().emit(record)
        except Exception:
            pass


_logging_initialized = False


def init_logging(log_level: int = logging.INFO) -> None:
    """初始化全局日志系统（仅执行一次）。"""
    global _logging_initialized
    if _logging_initialized:
        return

    root_logger = logging.getLogger("daming")
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()

    # 1. 控制台 Handler (带颜色格式)
    console_handler = SafeStreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(ColoredConsoleFormatter())
    root_logger.addHandler(console_handler)

    # 2. 全量日志文件 Handler (Rotate: 10MB x 5)
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    app_file_handler = SafeRotatingFileHandler(
        APP_LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    app_file_handler.setLevel(log_level)
    app_file_handler.setFormatter(file_formatter)
    root_logger.addHandler(app_file_handler)

    # 3. 错误日志文件 Handler (仅 WARNING/ERROR)
    error_file_handler = SafeRotatingFileHandler(
        ERROR_LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    error_file_handler.setLevel(logging.WARNING)
    error_file_handler.setFormatter(file_formatter)
    root_logger.addHandler(error_file_handler)

    _logging_initialized = True


def get_logger(name: str = "daming") -> logging.Logger:
    """获取指定子模块的 Logger。"""
    if not _logging_initialized:
        init_logging()
    if name == "daming" or name.startswith("daming."):
        return logging.getLogger(name)
    return logging.getLogger(f"daming.{name}")


def get_recent_logs(max_lines: int = 200, level_filter: Optional[str] = None) -> list[str]:
    """读取最近的日志行，供 Web Dashboard 展示。"""
    if not APP_LOG_FILE.exists():
        return []
    try:
        with APP_LOG_FILE.open("r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        if level_filter:
            target_level = f"[{level_filter.upper()}]"
            lines = [l for l in lines if target_level in l]
        return [l.rstrip() for l in lines[-max_lines:]]
    except Exception as e:
        return [f"读取日志文件失败: {e}"]
