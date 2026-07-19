"""
整合包首次启动自动修补脚本
修补模型代码以兼容当前环境
"""
import os
import json
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models", "Unlimited-OCR")
PATCH_MARKER = os.path.join(MODEL_DIR, ".patched")


def patch_unlimitedocr(content):
    """通用修补: modeling_unlimitedocr.py"""
    original = content

    # 1. 移除 autocast（让模型用加载时的精度，兼容所有GPU）
    content = content.replace(
        'with torch.autocast("cuda", dtype=torch.bfloat16):',
        'if False:  # autocast removed for GPU compatibility'
    )

    # 2. Add _get_device helper
    import_marker = "from .modeling_deepseekv2 import DeepseekV2Model, DeepseekV2ForCausalLM"
    if import_marker in content and "_get_device" not in content:
        helper = import_marker + '\n\ndef _get_device():\n    import torch\n    return torch.device("cuda" if torch.cuda.is_available() else "cpu")\n'
        content = content.replace(import_marker, helper)

    # 3. Fix .cuda() -> device-aware
    content = content.replace(".unsqueeze(0).cuda()", ".unsqueeze(0).to(_get_device())")
    content = content.replace(".cuda(),", ".to(_get_device()),")
    content = content.replace(".cuda()", ".to(_get_device())")

    # 4. Fix input_ids device
    content = content.replace(
        "input_ids=input_ids.unsqueeze(0).to(input_ids.device),",
        "input_ids=input_ids.unsqueeze(0).to(_get_device()),"
    )

    return content, content != original


def patch_deepseekv2(content):
    """通用修补: modeling_deepseekv2.py"""
    old_import = "from transformers.utils.import_utils import is_torch_fx_available"
    new_import = """try:\n    from transformers.utils.import_utils import is_torch_fx_available\nexcept ImportError:\n    def is_torch_fx_available():\n        return False"""

    if old_import in content:
        # Check if already patched - look for try: or except nearby
        before = content.split(old_import)[0]
        lines_before = before.rstrip().split("\n")
        last_line = lines_before[-1].strip() if lines_before else ""
        if last_line in ("try:", "except ImportError:"):
            return content, False  # Already patched
        content = content.replace(old_import, new_import)
        return content, True
    return content, False


def patch_file(path, patcher, label):
    """修补单个文件"""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    content, changed = patcher(content)
    if changed:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  [OK] {label}")


def patch_model_files():
    """修补 models 目录中的文件"""
    patch_file(
        os.path.join(MODEL_DIR, "modeling_unlimitedocr.py"),
        patch_unlimitedocr, "modeling_unlimitedocr.py"
    )
    patch_file(
        os.path.join(MODEL_DIR, "modeling_deepseekv2.py"),
        patch_deepseekv2, "modeling_deepseekv2.py"
    )


def patch_cache_files():
    """修补 HuggingFace 缓存中的文件"""
    cache_base = os.path.expanduser(r"~\.cache\huggingface\modules\transformers_modules")
    if not os.path.exists(cache_base):
        return

    for entry in os.listdir(cache_base):
        cache_dir = os.path.join(cache_base, entry)
        if not os.path.isdir(cache_dir):
            continue
        patch_file(
            os.path.join(cache_dir, "modeling_unlimitedocr.py"),
            patch_unlimitedocr, f"cache/{entry}/modeling_unlimitedocr.py"
        )
        patch_file(
            os.path.join(cache_dir, "modeling_deepseekv2.py"),
            patch_deepseekv2, f"cache/{entry}/modeling_deepseekv2.py"
        )


def patch_tokenizer():
    """修补 tokenizer.json merges 格式"""
    path = os.path.join(MODEL_DIR, "tokenizer.json")
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    model = data.get("model", {})
    merges = model.get("merges", [])

    if merges and isinstance(merges[0], list):
        model["merges"] = [" ".join(m) if isinstance(m, list) else str(m) for m in merges]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        print(f"  [OK] tokenizer.json (merges format)")


def patch_tokenizer_config():
    """修补 tokenizer_config.json"""
    path = os.path.join(MODEL_DIR, "tokenizer_config.json")
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    if cfg.get("tokenizer_class") == "LlamaTokenizer":
        cfg["tokenizer_class"] = "LlamaTokenizerFast"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        print(f"  [OK] tokenizer_config.json")


def patch_config():
    """修补 config.json"""
    path = os.path.join(MODEL_DIR, "config.json")
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    changed = False
    if cfg.get("pad_token_id") is None:
        cfg["pad_token_id"] = cfg.get("eos_token_id", 1)
        changed = True

    if changed:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        print(f"  [OK] config.json (pad_token_id)")


def clear_pycache():
    """清除所有 __pycache__"""
    for search_dir in [
        os.path.join(BASE_DIR, "models"),
        os.path.expanduser(r"~\.cache\huggingface\modules\transformers_modules"),
    ]:
        if not os.path.exists(search_dir):
            continue
        for root, dirs, files in os.walk(search_dir):
            for d in dirs:
                if d == "__pycache__":
                    shutil.rmtree(os.path.join(root, d))


def main():
    # Always patch cache (it gets regenerated)
    patch_cache_files()
    clear_pycache()

    if os.path.exists(PATCH_MARKER):
        return

    print("首次启动，正在修补模型代码...")

    patch_model_files()
    patch_tokenizer()
    patch_tokenizer_config()
    patch_config()

    with open(PATCH_MARKER, "w") as f:
        f.write("patched")

    print("修补完成！")


if __name__ == "__main__":
    main()
