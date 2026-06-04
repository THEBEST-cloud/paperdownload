import os
import subprocess
import time
from pathlib import Path

_DISPLAY = ":99"
_proc = None


def ensure_display(display: str = _DISPLAY) -> str:
    """启动(或复用)一个 Xvfb 虚拟显示器，返回 DISPLAY。已在跑则直接用。"""
    global _proc
    lock = Path("/tmp/.X%s-lock" % display.lstrip(":"))
    if lock.exists():
        os.environ["DISPLAY"] = display
        return display
    _proc = subprocess.Popen(
        ["Xvfb", display, "-screen", "0", "1280x1024x24"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(20):
        if lock.exists():
            break
        time.sleep(0.3)
    os.environ["DISPLAY"] = display
    return display
