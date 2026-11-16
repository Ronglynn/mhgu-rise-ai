#!/usr/bin/env python3
"""P94 background log watcher.

Started by 9_P91_oneshot.bat before the game. Polls the live log for the
P90 banner + [rai] lines. If nothing appears within the timeout, shows a
topmost Windows message box so the player can stop immediately instead of
finishing a 30-minute session with an empty plugin log.

Usage: watch_p91_log.py LOG STATUS [TIMEOUT_SECONDS]
"""
import ctypes
import datetime
import sys
import time
from pathlib import Path

FAIL_TEXT = (
    "P91 日志监视失败：启动 150 秒内没有出现 [rai] 横幅。\n\n"
    "本场很可能又是一次「没有记录」的空日志，继续打下去不会有判据数据。\n"
    "请立刻退出游戏，检查 Forge 的 [log] level 是否为 info，"
    "并把本消息告诉 Agent。\n\n"
    "（状态文件：out/P91_watch_status.txt）"
)


def main() -> int:
    if len(sys.argv) < 3:
        print("[x] usage: watch_p91_log.py LOG STATUS [TIMEOUT]")
        return 1
    log = Path(sys.argv[1])
    status = Path(sys.argv[2])
    timeout = int(sys.argv[3]) if len(sys.argv) > 3 else 150

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            data = log.read_bytes()
        except OSError:
            data = b""
        if b"P90 PROBE" in data and b"[rai]" in data:
            status.write_text(
                "OK  banner detected  %s  bytes=%d"
                % (datetime.datetime.now().strftime("%H:%M:%S"), len(data)),
                encoding="utf-8",
            )
            return 0
        time.sleep(5)

    status.write_text(
        "FAIL  no [rai] banner after %ds  %s"
        % (timeout, datetime.datetime.now().strftime("%H:%M:%S")),
        encoding="utf-8",
    )
    try:
        # MB_ICONEXCLAMATION | MB_TOPMOST | MB_SETFOREGROUND
        ctypes.windll.user32.MessageBoxW(0, FAIL_TEXT, "P91 LOG WATCH - FAIL", 0x30 | 0x40000 | 0x10000)
    except Exception:
        pass
    return 2


if __name__ == "__main__":
    sys.exit(main())
