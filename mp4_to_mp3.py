#!/usr/bin/env python3
"""
MP4 转 MP3 —— 命令行版（带进度条）。

用法：
  python mp4_to_mp3.py video.mp4                 # 单个文件，输出 video.mp3
  python mp4_to_mp3.py video.mp4 -o out.mp3      # 指定输出文件
  python mp4_to_mp3.py ./videos                  # 批量转换文件夹内所有视频
  python mp4_to_mp3.py ./videos -o ./mp3 -b 320k # 指定输出目录与码率
"""
import argparse
import sys
import time
from pathlib import Path

from converter import Converter, collect_videos, find_tool


def draw_bar(prefix: str, ratio: float, elapsed: float, width: int = 30):
    ratio = max(0.0, min(ratio, 1.0))
    filled = round(width * ratio)
    bar = "█" * filled + "░" * (width - filled)
    eta = (elapsed / ratio - elapsed) if ratio > 0 else 0
    sys.stdout.write(f"\r{prefix} |{bar}| {ratio*100:5.1f}%  已用 {elapsed:4.0f}s  剩余 {eta:4.0f}s ")
    sys.stdout.flush()


def convert_one(src: Path, dst: Path, bitrate: str, overwrite: bool, tag: str = "") -> bool:
    prefix = f"{tag}{src.name[:30]}"
    if dst.exists() and not overwrite:
        print(f"{prefix} [跳过] 已存在")
        return True
    start = time.time()
    ok, err = Converter().convert(src, dst, bitrate,
                                  on_progress=lambda r: draw_bar(prefix, r, time.time() - start))
    print(" ✓" if ok else f"\n{prefix} [失败] {err}")
    return ok


def main():
    parser = argparse.ArgumentParser(description="视频音轨导出为 MP3")
    parser.add_argument("input", help="视频文件或包含视频的文件夹")
    parser.add_argument("-o", "--output", help="输出文件（单文件）或输出目录（批量）")
    parser.add_argument("-b", "--bitrate", default="192k", help="MP3 码率，默认 192k（可选 128k/256k/320k）")
    parser.add_argument("-r", "--recursive", action="store_true", help="批量模式下包含子文件夹")
    parser.add_argument("-f", "--force", action="store_true", help="覆盖已存在的 MP3")
    args = parser.parse_args()

    if find_tool("ffmpeg") is None:
        sys.exit("未找到 ffmpeg，请先安装并加入 PATH。")

    src = Path(args.input).expanduser()
    if not src.exists():
        sys.exit(f"路径不存在：{src}")

    if src.is_file():
        dst = Path(args.output) if args.output else src.with_suffix(".mp3")
        sys.exit(0 if convert_one(src, dst, args.bitrate, args.force) else 1)

    files = collect_videos(src, args.recursive)
    if not files:
        sys.exit("该文件夹下没有找到视频文件。")

    out_dir = Path(args.output) if args.output else None
    total, fails = len(files), 0
    try:
        for i, f in enumerate(files, 1):
            dst = (out_dir / f.relative_to(src)).with_suffix(".mp3") if out_dir else f.with_suffix(".mp3")
            if not convert_one(f, dst, args.bitrate, args.force, tag=f"[{i}/{total}] "):
                fails += 1
    except KeyboardInterrupt:
        sys.exit("\n已中断。")
    print(f"\n共 {total} 个文件，成功 {total - fails}，失败 {fails}。")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
