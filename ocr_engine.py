"""
Unlimited-OCR 引擎封装
支持单图和多页PDF OCR识别
"""

import os
import tempfile
import torch
from pathlib import Path


class OCREngine:
    def __init__(self, model_path: str = "./models/Unlimited-OCR", device: str = "auto"):
        """
        初始化OCR引擎
        
        Args:
            model_path: 模型路径（本地路径或HuggingFace模型ID）
            device: 设备类型 auto/cpu/cuda
        """
        self.model_path = model_path
        self.device = self._resolve_device(device)
        self.model = None
        self.tokenizer = None
        self._loaded = False
        
    def _resolve_device(self, device: str) -> str:
        """解析设备类型"""
        if device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            return "cpu"
        return device
    
    def load_model(self):
        """加载模型"""
        if self._loaded:
            return
            
        from transformers import AutoModel, AutoTokenizer
        
        print(f"正在加载模型: {self.model_path}")
        print(f"使用设备: {self.device}")
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_path,
            trust_remote_code=True
        )
        
        # 根据GPU计算能力选择精度
        if self.device == "cuda":
            cc = torch.cuda.get_device_capability(0)
            if cc[0] >= 8:
                # Ampere+ (A100, RTX 30/40/50): bfloat16
                dtype = torch.bfloat16
            elif cc[0] >= 6:
                # Pascal/Volta/Turing (GTX 10/16/RTX 20, V100): float16
                dtype = torch.float16
            else:
                # 更老的卡: float32
                dtype = torch.float32
        else:
            dtype = torch.float32
            
        self.model = AutoModel.from_pretrained(
            self.model_path,
            trust_remote_code=True,
            use_safetensors=True,
            torch_dtype=dtype,
        )
        
        if self.device == "cuda":
            self.model = self.model.cuda()
        else:
            self.model = self.model.float()
        self.model = self.model.eval()
        
        self._loaded = True
        print("模型加载完成!")
        
    def ocr_single_image(self, image_path: str, output_dir: str = None) -> str:
        """
        单图OCR识别
        
        Args:
            image_path: 图片路径
            output_dir: 输出目录
            
        Returns:
            OCR识别结果文本
        """
        self.load_model()
        
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="ocr_")
        os.makedirs(output_dir, exist_ok=True)
        
        result = self.model.infer(
            self.tokenizer,
            prompt='<image>document parsing.',
            image_file=image_path,
            output_path=output_dir,
            base_size=1024,
            image_size=640,
            crop_mode=True,
            max_length=32768,
            no_repeat_ngram_size=35,
            ngram_window=128,
            save_results=True,
        )
        
        return self._read_result(output_dir)
    
    def ocr_multi_pages(self, image_paths: list, output_dir: str = None) -> str:
        """
        多页OCR识别（支持PDF转图片后的多页处理）
        
        Args:
            image_paths: 图片路径列表
            output_dir: 输出目录
            
        Returns:
            OCR识别结果文本
        """
        self.load_model()
        
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="ocr_multi_")
        os.makedirs(output_dir, exist_ok=True)
        
        # Process in batches to avoid max_length overflow
        batch_size = 5
        all_results = []
        for i in range(0, len(image_paths), batch_size):
            batch = image_paths[i:i + batch_size]
            batch_dir = os.path.join(output_dir, f"batch_{i // batch_size}")
            os.makedirs(batch_dir, exist_ok=True)
            
            self.model.infer_multi(
                self.tokenizer,
                prompt='<image>Multi page parsing.',
                image_files=batch,
                output_path=batch_dir,
                image_size=1024,
                max_length=131072,
                no_repeat_ngram_size=35,
                ngram_window=1024,
                save_results=True,
            )
            batch_result = self._read_result(batch_dir)
            if batch_result:
                all_results.append(batch_result)
        
        return "\n\n".join(all_results) if all_results else ""
    
    def ocr_pdf(self, pdf_path: str, output_dir: str = None, dpi: int = 300) -> str:
        """
        PDF文件OCR识别
        
        Args:
            pdf_path: PDF文件路径
            output_dir: 输出目录
            dpi: PDF转图片DPI
            
        Returns:
            OCR识别结果文本
        """
        import fitz  # PyMuPDF
        
        # PDF转图片
        doc = fitz.open(pdf_path)
        tmp_dir = tempfile.mkdtemp(prefix="pdf_ocr_")
        image_paths = []
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        
        for i, page in enumerate(doc):
            out_path = os.path.join(tmp_dir, f"page_{i + 1:04d}.png")
            page.get_pixmap(matrix=mat).save(out_path)
            image_paths.append(out_path)
        doc.close()
        
        # 多页OCR
        return self.ocr_multi_pages(image_paths, output_dir)
    
    def _read_result(self, output_dir: str) -> str:
        """读取OCR结果"""
        results = []
        for file in sorted(Path(output_dir).glob("*.md")):
            with open(file, "r", encoding="utf-8") as f:
                results.append(f.read())
        return "\n\n".join(results) if results else ""
