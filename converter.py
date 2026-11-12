"""核心转换逻辑：调用 ffmpeg 将视频音轨导出为 MP3，并通过回调报告进度。"""
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional

VIDEO_EXTS = {".mp4", ".m4v", ".mov", ".mkv", ".avi", ".flv", ".webm"}

# Windows 下隐藏 ffmpeg 弹出的黑色控制台窗口
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def _app_dir() -> Path:
    """程序所在目录（兼容 PyInstaller 打包后的 exe）。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def find_tool(name: str) -> Optional[str]:
    """优先使用程序目录下的 ffmpeg/ffprobe，其次使用系统 PATH 中的。"""
    exe = name + (".exe" if sys.platform == "win32" else "")
    for cand in (_app_dir() / exe, _app_dir() / "ffmpeg" / exe, _app_dir() / "ffmpeg" / "bin" / exe):
        if cand.is_file():
            return str(cand)
    return shutil.which(name)


def get_duration(src: Path) -> float:
    """读取媒体时长（秒），失败返回 0。"""
    ffprobe = find_tool("ffprobe")
    if not ffprobe:
        return 0.0
    try:
        out = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(src)],
            capture_output=True, text=True, creationflags=_NO_WINDOW,
        ).stdout.strip()
        return float(out)
    except (ValueError, OSError):
        return 0.0


def collect_videos(folder: Path, recursive: bool = False) -> list:
    pattern = "**/*" if recursive else "*"
    return sorted(p for p in folder.glob(pattern) if p.is_file() and p.suffix.lower() in VIDEO_EXTS)


class Converter:
    """单个文件的转换任务，可从其他线程调用 cancel() 中止。"""

    def __init__(self):
        self._proc: Optional[subprocess.Popen] = None
        self.cancelled = False

    def cancel(self):
        self.cancelled = True
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()

    def convert(self, src: Path, dst: Path, bitrate: str = "192k",
                on_progress: Optional[Callable[[float], None]] = None) -> tuple:
        """
        转换 src -> dst。on_progress(ratio) 会被反复调用，ratio 取值 0~1。
        返回 (成功与否, 错误信息)。
        """
        ffmpeg = find_tool("ffmpeg")
        if not ffmpeg:
            return False, "未找到 ffmpeg"
        dst.parent.mkdir(parents=True, exist_ok=True)
        duration = get_duration(src)
        cmd = [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-nostats",
            "-progress", "pipe:1", "-y",
            "-i", str(src),
            "-vn", "-acodec", "libmp3lame", "-b:a", bitrate,
            str(dst),
        ]
        self._proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace", creationflags=_NO_WINDOW,
        )
        if on_progress:
            on_progress(0.0)
        for line in self._proc.stdout:
            key, _, val = line.strip().partition("=")
            if key == "out_time_us" and duration > 0 and val.isdigit() and on_progress:
                on_progress(min(int(val) / 1e6 / duration, 1.0))
        self._proc.wait()
        err = self._proc.stderr.read().strip()
        code = self._proc.returncode
        self._proc = None

        if self.cancelled:
            try:
                os.remove(dst)  # 删除未完成的文件
            except OSError:
                pass
            return False, "已取消"
        if code != 0:
            return False, err or f"ffmpeg 退出码 {code}"
        if on_progress:
            on_progress(1.0)
        return True, ""
