"""
Unlimited-OCR Web界面
基于Gradio的中文OCR识别界面
"""

import os
import sys

# 首次启动自动修补模型代码
sys.path.insert(0, os.path.dirname(__file__))
from patch_model import main as patch_main
patch_main()

import tempfile
import gradio as gr
from pathlib import Path
from ocr_engine import OCREngine

# 全局OCR引擎实例
ocr_engine = None


def get_engine(model_path: str = "./models/Unlimited-OCR"):
    """获取或初始化OCR引擎"""
    global ocr_engine
    if ocr_engine is None:
        ocr_engine = OCREngine(model_path=model_path)
    return ocr_engine


def process_image(image, progress=gr.Progress()):
    """处理单张图片"""
    if image is None:
        return "请上传图片", None
    
    progress(0.1, desc="正在加载模型...")
    engine = get_engine()
    
    progress(0.3, desc="正在进行OCR识别...")
    output_dir = os.path.join(os.path.dirname(__file__), "outputs")
    os.makedirs(output_dir, exist_ok=True)
    result = engine.ocr_single_image(image, output_dir)

    progress(0.9, desc="保存结果...")
    output_file = os.path.join(output_dir, "result.md")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(result)
    
    progress(1.0, desc="完成!")
    return result, output_file


def process_pdf(pdf, progress=gr.Progress()):
    """处理PDF文件"""
    if pdf is None:
        return "请上传PDF文件", None
    
    progress(0.1, desc="正在加载模型...")
    engine = get_engine()
    
    progress(0.3, desc="正在转换PDF页面...")
    output_dir = os.path.join(os.path.dirname(__file__), "outputs")
    os.makedirs(output_dir, exist_ok=True)
    result = engine.ocr_pdf(pdf, output_dir)
    
    progress(0.9, desc="保存结果...")
    # 保存为md文件
    pdf_name = Path(pdf).stem
    output_file = os.path.join(output_dir, f"{pdf_name}_ocr.md")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(result)
    
    progress(1.0, desc="完成!")
    return result, output_file


def create_ui():
    """创建Gradio界面"""
    
    with gr.Blocks(title="Unlimited-OCR 整合包") as app:
        gr.Markdown(
            """
            <div class="main-title">
            <h1>Unlimited-OCR 整合包</h1>
            <p>百度出品的无限页OCR识别工具 | 支持单图和多页PDF一次性识别</p>
            </div>
            """
        )
        
        with gr.Tabs():
            with gr.TabItem("图片OCR"):
                with gr.Row():
                    with gr.Column(scale=1):
                        image_input = gr.Image(
                            label="上传图片",
                            type="filepath",
                            height=400
                        )
                        image_btn = gr.Button("开始识别", variant="primary", size="lg")
                    
                    with gr.Column(scale=1):
                        image_result = gr.Markdown(
                            label="识别结果",
                            value="",
                            elem_classes=["result-box"]
                        )
                        image_download = gr.File(label="下载结果")
                
                image_btn.click(
                    fn=process_image,
                    inputs=[image_input],
                    outputs=[image_result, image_download],
                    show_progress="full"
                )
            
            with gr.TabItem("PDF多页OCR"):
                with gr.Row():
                    with gr.Column(scale=1):
                        pdf_input = gr.File(
                            label="上传PDF文件",
                            file_types=[".pdf"],
                            height=400
                        )
                        pdf_btn = gr.Button("开始识别", variant="primary", size="lg")
                    
                    with gr.Column(scale=1):
                        pdf_result = gr.Markdown(
                            label="识别结果",
                            value="",
                            elem_classes=["result-box"]
                        )
                        pdf_download = gr.File(label="下载结果")
                
                pdf_btn.click(
                    fn=process_pdf,
                    inputs=[pdf_input],
                    outputs=[pdf_result, pdf_download],
                    show_progress="full"
                )
        
        with gr.Accordion("使用说明", open=False):
            gr.Markdown(
                """
                ### 功能特点
                - 支持单张图片OCR识别
                - 支持多页PDF一次性识别（核心特色）
                - 识别结果可复制和下载
                
                ### 使用方法
                1. 首次使用请先运行 `安装.bat` 安装依赖
                2. 双击 `启动.bat` 启动程序
                3. 在浏览器中打开 http://127.0.0.1:7860
                4. 上传图片或PDF即可开始识别
                
                ### 配置说明
                - 编辑 `config.yaml` 可修改端口等设置
                - 模型文件位于 `models/` 目录
                """
            )
    
    return app


def main():
    """主函数"""
    import yaml
    
    # 加载配置
    config_path = Path(__file__).parent / "config.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    else:
        config = {}
    
    webui_config = config.get("webui", {})
    host = webui_config.get("host", "127.0.0.1")
    port = webui_config.get("port", 7860)
    share = webui_config.get("share", False)
    
    # 创建并启动界面
    app = create_ui()
    app.launch(
        server_name=host,
        server_port=port,
        share=share,
        inbrowser=True,
        theme=gr.themes.Soft(),
        css="""
        .main-title {
            text-align: center;
            margin-bottom: 20px;
        }
        .result-box {
            min-height: 300px;
        }
        """
    )


if __name__ == "__main__":
    main()
