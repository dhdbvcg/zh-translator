# 贡献指南

感谢参与。这个项目不大,流程也尽量简单。

## 开发环境

```bash
git clone https://github.com/<你的用户名>/zh-translator.git
cd zh-translator
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
pip install -e .
python scripts/download_model.py
```

> 模型权重约 630 MB,首次下载需要几分钟。国内建议设置镜像:
> `$env:HF_ENDPOINT = "https://hf-mirror.com"`

## 提交前必跑

```bash
python tests/test_core.py        # 单元测试,不需要模型
python tests/diag_lang.py        # 语种识别准确率
node --check web/app.js          # 前端语法(需 Node)
node tests/domcheck.js           # 检查 DOM 引用完整性
```

如果改了翻译逻辑,还需要(需先 `zhtrans --serve` 起服务):

```bash
python tests/acceptance.py       # 端到端验收
python tests/web_selftest.py     # HTTP 接口自检
python eval/benchmark.py         # 多语种质量与速度
```

## 代码风格

- 遵循 PEP 8,行宽 100 以内;
- 中文注释优先,说明「为什么」而非「做了什么」;
- 公开函数写 docstring,关键取舍写明原因(尤其是踩过的坑)。

## 提交信息

用祈使句写明做了什么,例如:

```
fix: 过滤解码输出中的特殊 token
perf: 线程数改用物理核心数
feat: 增加 --speed 速度档位
```

## 关于模型许可

代码是 MIT,但默认基座模型 NLLB-200 是 **CC-BY-NC-4.0(禁商用)**。
如果你打算做商用,需要换一个许可兼容的基座。
详见 [LICENSE](LICENSE)。

## 不要提交的内容

- `models/`(模型权重,约 630 MB)
- `apikey.md` 或任何密钥文件
- `__pycache__/`、`.venv/`、编译产物

这些都已在 `.gitignore` 中。
