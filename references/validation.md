# 本机检查与验证记录

验证日期：2026-10-16（中国标准时间）。未上传 GitHub，未下载新模型，未复制个人视频、语音或模型权重到项目。

## 复用来源与环境

- 主要复用原 `jianying-compatible-subtitles/scripts/burn_jianying_subtitles.py` 的中文文案分句、识别字符时间戳、近似匹配、静音边界调整、SRT 输出和编码逻辑。
- 查阅旧 `short-video-subtitle-style` 和采访转录代码后，保留较新的兼容性合成方案，没有复制个人采访数据或旧 ASS 风格。
- Python 3.12.9；FFmpeg 8.1 essentials；faster-whisper 1.2.1；opencc-python-reimplemented 0.1.7；CPU int8。
- 本机 Hugging Face 用户缓存发现 base、small、large-v3-turbo；本次实际推理测试使用 base。另外发现 sherpa-onnx SenseVoice int8，但未将其作为本项目后端。
- 项目没有开发电脑绝对路径依赖，没有内嵌模型路径，没有打包 Python 环境或 FFmpeg 二进制文件。

## 已完成检查

执行 `python scripts/check_environment.py`：ffmpeg、ffprobe、subtitles/libass、libx264 及识别依赖均可用。

执行 `python tests/smoke_test.py --model base`：

1. 生成 640×360 测试视频和测试音轨，使用中文示例 SRT 烧录；校验 H.264、yuv420p、分辨率不变及音轨存在。
2. 比较解码后的视频帧校验值，确认字幕实际改变了画面。
3. 测试路径包含中文、空格和单引号，完成合成。
4. 再次写入非空输出目录被拒绝，已有视频字节保持不变。
5. 使用 Windows zh-CN 合成语音生成测试口播，调用本地 base 模型进行真实推理；自动字幕包含预期“字幕”关键词，产出 SRT 和 MP4。
6. 用同一测试口播与中文 TXT 进行识别对齐，确认文案出现在生成 SRT 中，并成功烧录视频。

测试音视频在系统临时目录创建，测试结束自动清除。首次帧比较测试误取了音轨校验值，修正为仅比较视频帧后，全套测试通过。

SKILL.md 通过 skill-creator 的 quick_validate.py 校验。该校验器在 Windows 默认 GBK 下不能读取中文 UTF-8 文件，因此验证时使用 `python -X utf8`；不需要修改全局编码。

## 验证范围

这是基本功能和兼容性验证，未做字幕画面的人工视觉验收、真实长视频识别准确率评估或跨平台实机测试。small/large-v3-turbo、自定义离线模型目录、首次联网下载、全新电脑依赖安装未实际运行验证。TXT 沿用近似对齐方法，真实素材仍需检查识别准确度、字幕时长、位置与字体。
