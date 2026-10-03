# 模型与许可说明

本仓库的**代码**采用 MIT 许可(见 [LICENSE](LICENSE))。

但项目默认使用的**模型权重**有独立许可,需要注意:

## 默认基座模型:NLLB-200 distilled 600M

| 项 | 值 |
|----|----|
| 来源 | <https://huggingface.co/facebook/nllb-200-distilled-600M> |
| 许可 | **CC-BY-NC-4.0** |
| 商业用途 | **不允许** |

也就是说:

- 代码(MIT)可以自由商用;
- 但使用默认基座模型时,**仅限非商业用途**;
- 若要商用,请把 `--model` 指向你拥有商业许可的模型,
  或替换 `src/zh_translator/engine.py` 中 `_translate_chunks` 的实现。

模型权重**不包含在本仓库中**,由 `scripts/download_model.py` 在本地下载,
并已被 `.gitignore` 排除。

## 依赖的第三方许可

| 组件 | 许可 |
|------|------|
| CTranslate2 | MIT |
| PyTorch | BSD-3-Clause |
| Transformers | Apache-2.0 |
| SentencePiece | Apache-2.0 |
| OpenCC | Apache-2.0 |
| NLLB-200(权重) | CC-BY-NC-4.0 |

## 可用的其他基座

本项目的推理层与具体模型解耦,除 NLLB-200 外也可使用:

```bash
python scripts/download_model.py --size 1.3b --out models/nllb-zh-int8-1.3b
python scripts/download_model.py --size 3.3b --out models/nllb-zh-int8-3.3b
```

更换其他模型时,需确保其支持 200+ 语种并覆盖 FLORES-200 语种代码。
