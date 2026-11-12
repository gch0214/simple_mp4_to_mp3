#!/usr/bin/env python3
"""MP4 转 MP3 —— 图形界面版（tkinter，Python 自带，无需额外安装库）。"""
from __future__ import annotations

import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from converter import VIDEO_EXTS, Converter, collect_videos, find_tool

BITRATES = ["128k", "192k", "256k", "320k"]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MP4 转 MP3")
        self.geometry("720x520")
        self.minsize(600, 420)

        self.files: list = []
        self.out_dir = tk.StringVar(value="")
        self.bitrate = tk.StringVar(value="192k")
        self.overwrite = tk.BooleanVar(value=False)
        self.msgs: queue.Queue = queue.Queue()
        self.worker: threading.Thread | None = None
        self.converter: Converter | None = None
        self.stop_flag = False
        self.errors: list = []

        self._build_ui()
        self.after(100, self._poll)
        if not find_tool("ffmpeg"):
            messagebox.showwarning(
                "未找到 ffmpeg",
                "请先安装 ffmpeg 并加入 PATH，\n或把 ffmpeg 放在本程序同一目录下。\n\n"
                "Windows: winget install ffmpeg\nmacOS:   brew install ffmpeg",
            )

    # ---------- 界面 ----------
    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        # 文件列表
        lf = ttk.LabelFrame(self, text="待转换文件")
        lf.pack(fill="both", expand=True, **pad)
        btns = ttk.Frame(lf)
        btns.pack(fill="x", padx=4, pady=4)
        ttk.Button(btns, text="添加文件", command=self.add_files).pack(side="left")
        ttk.Button(btns, text="添加文件夹", command=self.add_folder).pack(side="left", padx=4)
        ttk.Button(btns, text="移除选中", command=self.remove_selected).pack(side="left")
        ttk.Button(btns, text="清空", command=self.clear_files).pack(side="left", padx=4)

        cols = ("name", "status")
        self.tree = ttk.Treeview(lf, columns=cols, show="headings", selectmode="extended")
        self.tree.heading("name", text="文件")
        self.tree.heading("status", text="状态")
        self.tree.column("name", width=520)
        self.tree.column("status", width=120, anchor="center")
        sb = ttk.Scrollbar(lf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=(0, 4))
        sb.pack(side="right", fill="y", pady=(0, 4))

        # 设置
        sf = ttk.LabelFrame(self, text="设置")
        sf.pack(fill="x", **pad)
        ttk.Label(sf, text="输出目录：").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(sf, textvariable=self.out_dir).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(sf, text="浏览…", command=self.choose_out).grid(row=0, column=2, padx=4)
        ttk.Label(sf, text="（留空 = 与原视频同目录）", foreground="gray").grid(row=1, column=1, sticky="w", padx=4)
        ttk.Label(sf, text="码率：").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        ttk.Combobox(sf, textvariable=self.bitrate, values=BITRATES, width=8, state="readonly").grid(
            row=2, column=1, sticky="w", padx=4)
        ttk.Checkbutton(sf, text="覆盖已存在的 MP3", variable=self.overwrite).grid(
            row=2, column=1, sticky="e", padx=4)
        sf.columnconfigure(1, weight=1)

        # 进度
        pf = ttk.Frame(self)
        pf.pack(fill="x", **pad)
        self.cur_label = ttk.Label(pf, text="当前文件：-")
        self.cur_label.pack(anchor="w")
        self.cur_bar = ttk.Progressbar(pf, maximum=100)
        self.cur_bar.pack(fill="x", pady=2)
        self.total_label = ttk.Label(pf, text="总进度：0/0")
        self.total_label.pack(anchor="w")
        self.total_bar = ttk.Progressbar(pf, maximum=100)
        self.total_bar.pack(fill="x", pady=2)

        # 操作按钮
        af = ttk.Frame(self)
        af.pack(fill="x", padx=8, pady=(4, 10))
        self.start_btn = ttk.Button(af, text="开始转换", command=self.start)
        self.start_btn.pack(side="right")
        self.stop_btn = ttk.Button(af, text="停止", command=self.stop, state="disabled")
        self.stop_btn.pack(side="right", padx=6)

    # ---------- 文件操作 ----------
    def _add(self, paths):
        existing = set(self.files)
        for p in paths:
            p = Path(p)
            if p not in existing and p.suffix.lower() in VIDEO_EXTS:
                self.files.append(p)
                existing.add(p)
                self.tree.insert("", "end", iid=str(len(self.files) - 1), values=(str(p), "等待"))

    def add_files(self):
        types = [("视频文件", " ".join(f"*{e}" for e in sorted(VIDEO_EXTS))), ("所有文件", "*.*")]
        self._add(filedialog.askopenfilenames(title="选择视频文件", filetypes=types))

    def add_folder(self):
        d = filedialog.askdirectory(title="选择文件夹")
        if d:
            recursive = messagebox.askyesno("包含子文件夹？", "是否同时添加子文件夹中的视频？")
            found = collect_videos(Path(d), recursive)
            if not found:
                messagebox.showinfo("提示", "该文件夹下没有找到视频文件。")
            self._add(found)

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for i, p in enumerate(self.files):
            self.tree.insert("", "end", iid=str(i), values=(str(p), "等待"))

    def remove_selected(self):
        if self._busy():
            return
        idx = {int(i) for i in self.tree.selection()}
        self.files = [p for i, p in enumerate(self.files) if i not in idx]
        self._refresh_tree()

    def clear_files(self):
        if self._busy():
            return
        self.files.clear()
        self._refresh_tree()

    def choose_out(self):
        d = filedialog.askdirectory(title="选择输出目录")
        if d:
            self.out_dir.set(d)

    def _busy(self):
        return self.worker is not None and self.worker.is_alive()

    # ---------- 转换 ----------
    def start(self):
        if self._busy():
            return
        if not self.files:
            messagebox.showinfo("提示", "请先添加要转换的文件。")
            return
        if not find_tool("ffmpeg"):
            messagebox.showerror("错误", "未找到 ffmpeg，无法转换。")
            return
        for i in range(len(self.files)):
            self.tree.set(str(i), "status", "等待")
        self.stop_flag = False
        self.errors = []
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        out = self.out_dir.get().strip()
        self.worker = threading.Thread(
            target=self._run,
            args=(list(self.files), Path(out) if out else None, self.bitrate.get(), self.overwrite.get()),
            daemon=True,
        )
        self.worker.start()

    def stop(self):
        self.stop_flag = True
        if self.converter:
            self.converter.cancel()
        self.stop_btn.config(state="disabled")

    def _run(self, files, out_dir, bitrate, overwrite):
        """后台线程：逐个转换，通过队列把进度发回界面线程。"""
        total = len(files)
        ok = fail = 0
        for i, src in enumerate(files):
            if self.stop_flag:
                self.msgs.put(("status", i, "已取消"))
                continue
            dst = (out_dir / src.with_suffix(".mp3").name) if out_dir else src.with_suffix(".mp3")
            self.msgs.put(("current", i, src.name))
            if dst.exists() and not overwrite:
                self.msgs.put(("status", i, "跳过（已存在）"))
                ok += 1
                self.msgs.put(("total", i + 1, total))
                continue
            self.msgs.put(("status", i, "转换中…"))
            start = time.time()
            self.converter = Converter()
            success, err = self.converter.convert(
                src, dst, bitrate,
                on_progress=lambda r, s=start: self.msgs.put(("progress", r, time.time() - s)),
            )
            self.converter = None
            if success:
                ok += 1
                self.msgs.put(("status", i, "✓ 完成"))
            else:
                fail += 1
                self.msgs.put(("status", i, "已取消" if err == "已取消" else "✗ 失败"))
                if err != "已取消":
                    self.msgs.put(("error", src.name, err))
            self.msgs.put(("total", i + 1, total))
        self.msgs.put(("done", ok, fail))

    def _poll(self):
        """界面线程：处理后台发来的消息（tkinter 只能在主线程更新）。"""
        try:
            while True:
                msg = self.msgs.get_nowait()
                kind = msg[0]
                if kind == "current":
                    self.cur_label.config(text=f"当前文件：{msg[2]}")
                    self.cur_bar["value"] = 0
                    self.tree.see(str(msg[1]))
                elif kind == "progress":
                    ratio, elapsed = msg[1], msg[2]
                    self.cur_bar["value"] = ratio * 100
                    eta = elapsed / ratio - elapsed if ratio > 0 else 0
                    name = self.cur_label.cget("text").split("  ")[0]
                    self.cur_label.config(text=f"{name}  {ratio*100:.1f}%  已用 {elapsed:.0f}s  剩余 {eta:.0f}s")
                elif kind == "status":
                    self.tree.set(str(msg[1]), "status", msg[2])
                elif kind == "total":
                    done, total = msg[1], msg[2]
                    self.total_bar["value"] = done / total * 100
                    self.total_label.config(text=f"总进度：{done}/{total}")
                elif kind == "error":
                    self.errors.append(f"{msg[1]}：{msg[2][:200]}")
                elif kind == "done":
                    self.start_btn.config(state="normal")
                    self.stop_btn.config(state="disabled")
                    text = f"成功 {msg[1]} 个，失败 {msg[2]} 个。"
                    if self.errors:
                        text += "\n\n失败原因：\n" + "\n".join(self.errors[:5])
                        messagebox.showwarning("完成", text)
                    else:
                        messagebox.showinfo("完成", text)
        except queue.Empty:
            pass
        self.after(100, self._poll)


if __name__ == "__main__":
    App().mainloop()
