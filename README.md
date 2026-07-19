# Unlimited-OCR-Portable 整合包

基于百度Unlimited-OCR的Windows一键运行整合包，支持单图和多页PDF一次性识别。

## 功能

- 单张图片 OCR 识别
- 多页 PDF 一次性识别（核心特色）
- 自动适配 GPU 精度（bfloat16 / float16 / float32）
- Gradio 中文 Web 界面，拖拽上传
- 内嵌 Python + 预装依赖 + 预置模型，复制到任意 Windows 电脑，双击即可使用。

## 系统要求

| 要求 | 说明 |
|------|------|
| 操作系统 | Windows 10/11 (64-bit) |
| NVIDIA 显卡 | GTX 1060 及以上，显存 6GB+ |
| 显卡驱动 | 已安装，支持 CUDA 12.1 |
| Python | **不需要**，已内嵌 |
| 磁盘空间 | 约 12GB |

## 整合包下载

> GitHub 仓库仅包含源码。完整整合包（含内嵌 Python 和模型文件）请从 [Releases](../../releases) 下载。

下载后解压到任意目录，目录结构如下：

```
unlimitedOCR/
├── python/                 # 内嵌 Python 3.12 + 所有依赖
├── models/                 # 模型文件 (~6.3GB)
│   └── Unlimited-OCR/
├── outputs/                # OCR 结果输出目录
├── 启动.bat                # 双击启动
├── webui.py                # Gradio Web 界面
├── ocr_engine.py           # OCR 引擎（GPU 自动适配）
├── patch_model.py          # 自动修补脚本
├── config.yaml             # 配置文件
└── README.md
```

## 使用方法

1. 确保已安装 NVIDIA 显卡驱动
2. 双击 `启动.bat`
3. 浏览器自动打开 http://127.0.0.1:7860
4. 上传图片或 PDF 即可开始识别

## GPU 精度自动适配

程序根据显卡的 Compute Capability 自动选择最佳精度：

| GPU 架构 | 代表型号 | 使用精度 |
|----------|----------|---------|
| Ampere+ | RTX 30/40/50 系列, A100 | bfloat16 |
| Turing | RTX 20 系列, GTX 1660 | float16 |
| Pascal | GTX 10 系列 | float16 |
| 更老 / 无 GPU | - | float32 |

## 配置

编辑 `config.yaml` 修改设置：

```yaml
webui:
  host: "127.0.0.1"
  port: 7860
  share: false       # 是否创建公网链接
```

## 模型兼容性修补

首次启动时 `patch_model.py` 会自动修补模型代码的 5 个兼容性问题：

1. `is_torch_fx_available` 导入报错 — transformers 4.44 已移除
2. `.cuda()` 硬编码 — CPU 模式下崩溃
3. `input_ids` 设备不匹配 — CPU/GPU 混合
4. `autocast("cuda", bfloat16)` — 老显卡不支持
5. `tokenizer.json` merges 格式不兼容 — tokenizers 0.19 期望字符串格式

## 常见问题

**启动报错 "CUDA not available"**
检查 NVIDIA 显卡驱动是否安装，运行 `nvidia-smi` 查看。

**启动报错 "No module named 'gradio'"**
整合包不完整，确保 `python/Lib/site-packages/` 下有 gradio 目录。

**识别结果为空**
检查图片是否清晰，PDF 是否为扫描版（非文本版）。

**内存不足**
GTX 1060 (6GB) 建议处理单张图片，大 PDF 可能需要更多显存。

## 源码文件说明

| 文件 | 说明 |
|------|------|
| `webui.py` | Gradio Web 界面主程序 |
| `ocr_engine.py` | OCR 引擎封装，GPU 自动适配 |
| `patch_model.py` | 模型代码兼容性自动修补 |
| `config.yaml` | 配置文件 |
| `启动.bat` | Windows 启动脚本 |

## License

MIT

基于百度 [Unlimited-OCR](https://github.com/PaddlePaddle/Unlimited-OCR) 项目整合。
