# 视频字幕 AI Agent Skill

把这个文件夹交给能读取本地文件、执行 Python 的 AI Agent，并告诉它：“读取 SKILL.md，给我的视频加字幕。”它可以处理以下情况：

| 你提供的文件 | 处理方式 | 是否需要模型 |
| --- | --- | --- |
| 视频 + SRT | 使用现有时间轴直接烧录 | 否 |
| 视频 + 中文 TXT | 识别语音并近似对齐文案 | 是 |
| 只有视频 | 自动识别语音、生成 SRT、烧录 | 是 |

输出为 `video.mp4`、`video.subtitles.srt` 和 `verification.json`，统一放在指定的新文件夹。默认输出兼容剪映常用的 H.264/yuv420p，保留原始分辨率和原音频内容。

## 快速使用（Windows PowerShell）

安装 Python 3.10–3.12 和带 libass/libx264 的 FFmpeg，详见 [依赖安装](references/installation.md)。在本项目目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/check_environment.py
# 只有 TXT/自动识别需要这一步；联网下载一次，模型在项目外缓存
.\.venv\Scripts\python.exe scripts/download_model.py --model base
```

已有字幕：

```powershell
.\.venv\Scripts\python.exe scripts/video_subtitles.py --video "D:\素材\源视频.mp4" --srt "D:\素材\字幕.srt" --output-dir "outputs\srt-job"
```

自动识别字幕：

```powershell
.\.venv\Scripts\python.exe scripts/video_subtitles.py --video "D:\素材\源视频.mp4" --auto --model base --language zh --output-dir "outputs\auto-job"
```

对齐现有中文文案：

```powershell
.\.venv\Scripts\python.exe scripts/video_subtitles.py --video "D:\素材\源视频.mp4" --text-file "D:\素材\口播.txt" --model base --output-dir "outputs\txt-job"
```

也可以使用系统 Python；Linux/macOS 使用 `.venv/bin/python`。Agent 应根据当前机器选取解释器和路径。脱机使用本地模型目录时将 `--model base` 替换为目录路径，见 [模型获取与迁移](references/models.md)。默认 CPU/int8，无需显卡。

## 给别人使用

本项目不包含模型、FFmpeg、Python 环境或个人视频。下载后按安装说明准备环境即可；不能仅靠一份 SKILL.md 就自动具备运行依赖。可直接让 Agent 读取根目录 SKILL.md，或把整个目录复制到 Agent 的技能目录下并命名为 `video-subtitle-pack`。不同 Agent 的安装目录不同，代码不依赖特定 Agent API。

仓库中提供合成示例文案及生成测试视频的脚本，运行 `python tests/smoke_test.py` 测试 SRT 模式；加入 `--model base` 还会使用系统合成语音测试自动识别和 TXT 对齐（该语音测试限 Windows）。测试不使用个人视频。

## 注意事项

- 字幕建议 UTF-8；SRT/TXT 也会尝试 GB18030 解码，输出统一 UTF-8。
- 默认微软雅黑，其他系统需安装有中文字形的字体并确保 FFmpeg 能匹配中文字体。字体不随项目分发。
- TXT 对齐沿用原来的中文近似匹配算法，内容差异大、长停顿或语速过快可能产生偏移，需要校对。自动字幕用 Whisper 分段时间戳；自动识别支持 `--language auto` 或 Whisper 语言代码。
- 每个任务使用独立空目录，脚本拒绝覆盖已有结果。失败后可能留下空输出目录，可直接重试。
- 不会自动联网下载模型；下载必须显式执行 download_model.py。
- CRF/字号/底部留白可调整，完整参数用 `--help` 查看。视频宽高必须为偶数。

## 项目内容与发布

`scripts/subtitle_core.py` 复用本机原 `jianying-compatible-subtitles` 代码，保留文案匹配和编码设置，修改为按需加载识别依赖、只读本地模型、临时字幕路径处理，并去除固定 H.264 level 3.1，避免限制高分辨率视频。`scripts/video_subtitles.py` 为统一入口。检查与验证记录见 [验证记录](references/validation.md)。

本项目代码和文档以 [MIT License](LICENSE) 开源，允许使用、修改和再分发，请保留许可证声明。FFmpeg、faster-whisper、CTranslate2、OpenCC 与模型各自遵循其上游许可证，未随本项目分发。

`.gitignore` 已排除视频、音频、个人字幕、权重、虚拟环境和输出。Git 忽略规则无法移除已经被跟踪的文件，发布前仍需检查待提交列表。
