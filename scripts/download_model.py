"""下载并转换 NLLB-200 为 CTranslate2 int8 格式。

用法::

    python scripts/download_model.py                      # 默认 600M int8
    python scripts/download_model.py --size 1.3b --type int8
    python scripts/download_model.py --device cpu --compute int8

首次运行会从 HuggingFace 拉取约 2.4GB 权重,随后转换为本地推理格式。
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "models"

# NLLB-200 distilled 系列,按参数量从小到大
SIZES = {
    "600m": "facebook/nllb-200-distilled-600M",
    "1.3b": "facebook/nllb-200-distilled-1.3B",
    "3.3b": "facebook/nllb-200-3.3B",
}


def main() -> int:
    ap = argparse.ArgumentParser(description="下载 NLLB-200 并转换为 CTranslate2 格式")
    ap.add_argument("--size", default="600m", choices=list(SIZES),
                    help="模型规模,默认 600m(2GB 显存友好)")
    ap.add_argument("--type", default="int8", dest="compute",
                    choices=["int8", "int8_float16", "float16", "float32"],
                    help="量化类型,默认 int8(CPU 友好、显存小)")
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"],
                    help="转换时的设备")
    ap.add_argument("--out", default=None, help="输出目录,默认 models/nllb-zh-int8")
    ap.add_argument("--threads", type=int, default=max(1, (os.cpu_count() or 4) - 1),
                    help="转换线程数")
    args = ap.parse_args()

    repo = SIZES[args.size]
    out = Path(args.out) if args.out else MODELS / f"nllb-zh-{args.compute}-{args.size}"

    if (out / "model.bin").exists() or (out / "model.bin").is_file():
        print(f"[skip] 模型已存在: {out}")
        return 0

    out.mkdir(parents=True, exist_ok=True)
    print(f"[1/2] 正在从 HuggingFace 下载 {repo} ...")
    # 注意:权重文件名为 pytorch_model.bin 或 model.safetensors,
    # 二者需显式匹配,否则只会拿到 tokenizer 与 config。
    patterns = [
        "config.json",
        "generation_config.json",
        "sentencepiece.bpe.model",
        "special_tokens_map.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "pytorch_model.bin",
        "model.safetensors",
        "*.safetensors",
    ]
    try:
        from huggingface_hub import snapshot_download
        local = snapshot_download(repo, allow_patterns=patterns)
    except Exception as exc:
        print(f"HF 下载失败({exc}),尝试镜像 hf-mirror.com ...", file=sys.stderr)
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
        from huggingface_hub import snapshot_download
        local = snapshot_download(repo, allow_patterns=patterns)
    print(f"      权重已缓存到 {local}")

    # 校验权重是否真的到位
    import glob as _glob
    has_weights = any(
        _glob.glob(os.path.join(local, p))
        for p in ("pytorch_model.bin", "*.safetensors")
    )
    if not has_weights:
        raise SystemExit(
            f"未在 {local} 找到模型权重文件(pytorch_model.bin / *.safetensors)。"
            f"请检查网络或手动下载权重后重试。"
        )

    print(f"[2/2] 转换为 CTranslate2 ({args.compute}, device={args.device}) ...")
    import ctranslate2
    import torch
    from transformers import AutoTokenizer

    # transformers 出于 CVE-2025-32434 的防护,要求 torch>=2.6 才能用 torch.load
    # 读取 .bin 权重;而 NLLB-200 只发布了 pytorch_model.bin。
    if tuple(int(x) for x in torch.__version__.split("+")[0].split(".")[:2]) < (2, 6):
        raise SystemExit(
            f"当前 torch 版本为 {torch.__version__},过低。\n"
            f"NLLB-200 仅提供 pytorch_model.bin,需 torch>=2.6 才能安全加载。\n"
            f"请先运行: pip install --upgrade \"torch>=2.6\""
        )

    # 注意:TransformersConverter 的第一个参数是「模型标识」(本地目录或
    # HF repo id),它内部会自行 from_pretrained。直接传 model 对象会把它
    # 当作 repo id 去 Hub 查询,报 HFValidationError。
    converter = ctranslate2.converters.TransformersConverter(local)
    converter.convert(
        output_dir=str(out),
        quantization=args.compute,
        force=True,
    )
    # 转换器会把 tokenizer 一并保存;再补存一份确保 special tokens 齐全
    AutoTokenizer.from_pretrained(local, src_lang="zho_Hans").save_pretrained(str(out))
    print(f"[done] 已保存到 {out}")
    size_mb = sum(f.stat().st_size for f in out.glob("*.*")) / 1e6
    print(f"       目录大小约 {size_mb:.0f} MB")
    print(f"\n使用: from zh_translator import Translator; "
          f"Translator(model_dir=r'{out}').translate('Hello world')")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
