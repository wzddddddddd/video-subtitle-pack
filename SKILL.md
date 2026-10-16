---
name: video-subtitle-pack
description: 为本地视频烧录已有 SRT 字幕，将中文 TXT 文案对齐语音，或离线识别视频语音生成字幕，输出剪映兼容的 MP4 和可编辑 SRT。适用于本地字幕合成，不涉及配音或视频上传。
---

# 视频字幕工具包

使用本目录的 `scripts/video_subtitles.py`，所有路径相对于本 Skill 所在目录解析；调用时把示例中的路径替换为实际路径。不要依赖开发者电脑上的绝对路径。

先阅读 [安装说明](references/installation.md)，执行 `python scripts/check_environment.py`。SRT 模式只需要 Python、FFmpeg；TXT 和自动字幕还需要 requirements.txt 中的依赖及已缓存的 Whisper 模型。模型获取见 [模型说明](references/models.md)。普通处理禁止隐式下载模型，缺少模型时报告并提供获取命令。

根据用户提供的素材选择模式：

- 已有时间轴的 SRT：`python scripts/video_subtitles.py --video INPUT --srt SUBTITLES --output-dir OUTPUT`
- 中文 TXT 文案：`python scripts/video_subtitles.py --video INPUT --text-file COPY --model base --output-dir OUTPUT`
- 仅有视频：`python scripts/video_subtitles.py --video INPUT --auto --model base --language zh --output-dir OUTPUT`

OUTPUT 必须是新建或空文件夹。输入不明确时，只检查用户指定的素材目录；多个候选时让用户选择。不要误用上次生成的 video.mp4；不要把示例文案当成用户文案。TXT 必须与口播大致一致；这是近似匹配，不是强制对齐模型，较大差异需用户修正文案或改用自动字幕。

保持原始画面尺寸、原始音频内容；AAC 复制，其他音频转 AAC。使用 H.264 High、yuv420p、faststart，默认 CRF 16、slow。输出 video.mp4、video.subtitles.srt 和 verification.json。输入宽高为奇数时脚本会拒绝处理，应先根据用户意图决定补边或缩放。

脚本会检查视频编码、像素格式、分辨率和音轨。交付前再抽查前、中、后字幕与口播是否一致、是否有乱码或遮挡；没有人工检查时，明确说明仅完成自动检查。静音或无人声应报告，无需生成虚假字幕。识别结果需要校对，尤其是人名、术语和时间轴。

不要修改源视频，不要上传视频，不要将用户素材、模型、缓存、环境或输出加入版本库。失败时检查错误，只修复明确问题后重试；不切换到云服务。命令用参数列表执行，避免拼接用户提供的字幕文本到 shell。
