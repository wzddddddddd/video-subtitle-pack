# 模型获取与迁移

项目使用 faster-whisper 的 CTranslate2 Whisper 模型。默认 base，可选 small 或 large-v3-turbo（耗时和内存更高）。原版 Whisper 的单个 .pt 文件不能直接用。

联网准备一次：

```powershell
python scripts/download_model.py --model base
```

默认下载到 Hugging Face 用户缓存，通常为 `~/.cache/huggingface/hub`，不进入项目。可通过 Hugging Face 官方环境变量调整缓存位置；如果使用 `--cache-dir` 指定自定义缓存，请保存下载脚本打印的完整快照目录，之后用 `--model "完整快照目录"` 运行。

下载需要能访问 Hugging Face：
https://huggingface.co/Systran/faster-whisper-base

模型使用条款以下载时的模型卡/上游许可证为准。不要为重试下载更改整机网络配置或默认镜像。

离线迁移：将下载脚本输出的快照目录中的实际文件复制到仓库外独立目录，确保不是指向另一台机器缓存的断开符号链接。通常需要 model.bin、config.json、tokenizer.json、vocabulary.json（具体以快照内容为准）。然后：

```powershell
python scripts/video_subtitles.py --video "D:\input.mp4" --auto --model "D:\AI-models\faster-whisper-base" --output-dir "D:\result"
```

普通处理使用 `local_files_only=True`，不会自动下载。缓存不存在或目录不完整会报错，不会偷偷降级模型。

整理时在原电脑发现 Whisper base、small、large-v3-turbo 的缓存，以及 sherpa-onnx SenseVoice int8 模型。字幕代码已有 faster-whisper 调用，因此本项目复用 Whisper；SenseVoice 不属于此入口的后端，不能把它的 .onnx 文件传给 --model。无需安装 sherpa-onnx。所有原有模型仍留在原位置，未复制进仓库。
