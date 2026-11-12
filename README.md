# simple_mp4_to_mp3

把 MP4（以及 MOV / MKV / AVI / FLV / WEBM / M4V）视频里的音轨导出成 MP3。提供**图形界面**和**命令行**两个版本，都有进度条。

## 功能

- 批量添加文件或整个文件夹（可选包含子文件夹）
- 当前文件进度 + 总进度，显示已用时间和预计剩余时间
- 可选码率：128k / 192k / 256k / 320k
- 自定义输出目录，或输出到原视频所在目录
- 支持中途停止，未完成的文件会被自动删除
- 只依赖 Python 标准库（tkinter）和 ffmpeg

## 环境要求

1. Python 3.8 及以上
2. [ffmpeg](https://ffmpeg.org/download.html)，满足下面任一条件即可：
   - 已加入系统 PATH
     - Windows：`winget install ffmpeg`
     - macOS：`brew install ffmpeg`
     - Linux：`sudo apt install ffmpeg`
   - 或者把 `ffmpeg` / `ffprobe` 可执行文件放在本程序同一目录下（也可以放在 `ffmpeg/` 或 `ffmpeg/bin/` 子目录里）

> Linux 上如果提示缺少 tkinter，请执行 `sudo apt install python3-tk`。

## 使用

### 图形界面

```bash
python mp4_to_mp3_gui.py
```

1. 点「添加文件」或「添加文件夹」
2. 选择输出目录（留空就输出到原视频旁边）和码率
3. 点「开始转换」

### 命令行

```bash
python mp4_to_mp3.py video.mp4                  # 单个文件 → video.mp3
python mp4_to_mp3.py video.mp4 -o 音频.mp3       # 指定输出文件名
python mp4_to_mp3.py ./videos                   # 转换文件夹内所有视频
python mp4_to_mp3.py ./videos -r -o ./mp3 -b 320k  # 包含子文件夹，指定输出目录和码率
python mp4_to_mp3.py ./videos -f                # 覆盖已存在的 MP3
```

## 打包成 exe（可选）

```bash
pip install pyinstaller
pyinstaller -F -w -n mp4_to_mp3 mp4_to_mp3_gui.py
```

生成的 `dist/mp4_to_mp3.exe` 同目录下放上 `ffmpeg.exe` 和 `ffprobe.exe`，在没装 ffmpeg 的电脑上也能直接运行。

## 文件说明

| 文件 | 说明 |
|---|---|
| `converter.py` | 核心转换逻辑（调用 ffmpeg，报告进度） |
| `mp4_to_mp3_gui.py` | 图形界面版 |
| `mp4_to_mp3.py` | 命令行版 |
