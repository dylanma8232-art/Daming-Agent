"""进程级互斥锁，避免同一 Agent 守护服务被重复启动。"""

from __future__ import annotations

import fcntl
import os
from pathlib import Path
from typing import Optional


class ProcessLock:
    """基于 POSIX advisory lock 的非阻塞单实例锁。

    锁由操作系统在进程退出（包括异常退出）时自动释放；锁文件保留仅用于
    记录当前持有者 PID，不能据此判断锁是否仍然有效。
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._file = None
        self.holder_pid: Optional[str] = None

    def acquire(self) -> bool:
        """尝试获取锁；已有实例持锁时返回 ``False``。"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock_file = self.path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock_file.seek(0)
            self.holder_pid = lock_file.read().strip() or None
            lock_file.close()
            return False
        except OSError:
            lock_file.close()
            raise

        self._file = lock_file
        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        os.fsync(lock_file.fileno())
        return True

    def release(self) -> None:
        """释放锁。可重复调用，确保异常清理路径安全。"""
        if self._file is None:
            return
        try:
            fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
        finally:
            self._file.close()
            self._file = None
