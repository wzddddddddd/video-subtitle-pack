# 依赖安装

推荐 Windows x64，Python 3.10–3.12。本机验证版本为 Python 3.12。其他系统未进行实机验证。

1. 从 https://www.python.org/downloads/ 安装 Python，启用 PATH；运行 `python --version` 确认。
2. 从 https://ffmpeg.org/download.html 获取适用于本系统的 FFmpeg。Windows 可使用其链接到的 Gyan 构建，将解压目录的 bin 加入 PATH；重新打开终端。需要同时有 ffmpeg、ffprobe，包含 subtitles/libass 和 libx264。
3. 在项目根目录创建独立环境并安装识别依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/check_environment.py
```

SRT 直接合成不必安装 requirements.txt。检查脚本会报告识别依赖是否存在，但基础 SRT 环境检查不要求这些依赖。

依赖固定了已验证的顶层版本，间接依赖由 pip 解析；不是完整离线环境锁定文件。下载模型见 models.md。CPU int8 是默认方式，不需要 CUDA，不自动安装 GPU 环境。

Linux/macOS 使用相应包管理器安装带 libass/libx264 的 FFmpeg；中文字体需另行安装，如 Noto Sans CJK。字幕内容出现方框时先检查字体，而不是更改编码。系统字体及外部软件不捆绑到仓库。

无网络的目标机：在相同操作系统、架构、Python 版本的联网机器下载 wheels：

```powershell
python -m pip download -r requirements.txt -d "D:\offline-wheels"
# 目标机器运行
python -m pip install --no-index --find-links "D:\offline-wheels" -r requirements.txt
```

另行转移 FFmpeg、Python 安装程序及模型目录。安装包和 wheels 不要加入项目版本库。

常见错误：找不到 ffmpeg → 修正 PATH；模型未缓存 → 显式下载或传本地目录；缺少音轨 → 只用 SRT 模式或换含口播的视频；输出目录非空 → 选新目录；ASR 输出为空 → 检查音轨是否有人声。不要盲目循环重试或上传素材。
