# zh-translator · 多语种中文翻译

把**任意语言(含小语种)翻译成简体中文**的本地 AI 翻译工具。
完全离线,无需联网,无需 API Key。

## 效果

在 2GB 显存笔记本 / 纯 CPU 环境实测(20 语种,平均 0.77 秒/句):

| 语种 | 原文 | 译文 |
|------|------|------|
| en | Hello, how are you today? | 您好,今天您怎么样? |
| de | Das Wetter ist heute sehr schön. | 今天天气非常好。 |
| ru | Привет, как дела сегодня? | 你好,今天怎么回事? |
| ja | こんにちは、お元気ですか。 | 您好,您好吗? |
| ar | مرحبا كيف حالك اليوم | 你好,你今天好吗? |
| sw | Habari za asubuhi, hujambo? | 您好,您好吗? |
| km | ជំរាបសួរ តើអ្នកយុត្តទេ? | 问问:你是谁? |
| th | สวัสดีครับ สบายดีไหม | 你好,你好吗? |
| ne | नमस्ते, तपाईं कसो हुनुहुन्छ? | 你好,你还好吗? |
| zu | Sawubona, unjani? | 您好,您好吗? |

完整结果: ```python eval/benchmark.py```

## 特点

- **121 个源语种**,含大量低资源小语种(斯瓦希里语、齐切瓦语、宿务语、高棉语、僧伽罗语、阿姆哈拉语……)
- **自动识别源语种**,带置信度;也可显式指定。29 条代表性测试 **100% 命中**
- **原生多语种模型**(NLLB-200),不走「英语中转」,小语种质量更好
- **int8 量化**,661MB,2GB 显存 / 纯 CPU 均可运行
- **保留结构**:HTML 保留标签,SRT 保留时间轴与行尾风格
- **中文后处理**:标点规范、简繁统一(OpenCC)、术语表、长文本切分
- 三种用法:Python API、命令行、HTTP 服务

## 安装

```bash
pip install -r requirements.txt
python scripts/download_model.py          # 首次约 2.4GB 下载 + 转换
```

国内网络建议加镜像:

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
# PowerShell
$env:HF_ENDPOINT = "https://hf-mirror.com"
python scripts/download_model.py
```

安装为命令行工具:

```bash
pip install -e .        # 之后可直接用 zhtrans
```

> 需要 torch>=2.6。NLLB-200 只提供 pytorch_model.bin,
> 低于该版本时 transformers 会因 CVE-2025-32434 防护拒绝加载。

## 快速开始

### Python

```python
from zh_translator import Translator

tr = Translator()                              # 自动选 CPU/CUDA

tr.translate("Hello world").text                # 你好,世界
tr.translate("Bonjour", source="fr").text       # 您好
tr.translate("こんにちは").text                  # 您好(自动识别日语)

r = tr.translate(
    "The library closes at six.", source="en",
    glossary={"图书馆": "library"},             # 术语表
)
print(r.text, r.source_lang_zh, r.confidence)

# 批量(可混合语种,自动分组)
for r in tr.translate_batch(["Good morning", "Guten Tag", "Bonjour"]):
    print(r.source_lang_zh, "->", r.text)
```

### 命令行

```bash
zhtrans "Hello world"                            # 自动识别
zhtrans --from ja "こんにちは"
zhtrans -i article.html -o article.zh.html --from en   # HTML 保留标签
zhtrans -i sub.srt -o sub.zh.srt --from en             # 字幕保留时间轴
zhtrans -i docs/ --to-file -o out/ --from auto         # 批量目录
zhtrans --langs                                        # 列出所有语种
zhtrans --serve --port 8848                            # HTTP 服务
```

### HTTP 服务

```bash
zhtrans --serve --port 8848
```

```bash
curl -X POST http://127.0.0.1:8848/translate \
  -H "Content-Type: application/json" \
-d '{"text":"Hello world","from":"auto"}'
# {"translation":"你好,世界","source_lang":"eng_Latn","detected":true}
```

接口:`POST /translate`、`POST /batch`、`GET /langs`、`GET /health`。

服务启动时会自动托管 `web/` 目录,**打开 http://127.0.0.1:8848/ 即可使用网页测试台**
(含交互翻译、批量翻译、8 项接口自检、121 语种表)。详见 [web/README.md](web/README.md)。

> 服务是前台进程,**请保持启动它的终端窗口开启**;窗口关闭后页面仍能打开,
> 但所有请求会报 "无法连接翻译服务"。首次启动加载模型约需 60–90 秒。

```bash
zhtrans --serve --web off    # 如需关闭静态页面托管
```

## 语种代码

支持 `en` / `eng` / `eng_Latn` / `English` / `英语` 任意写法。

```python
det = tr.detect("Xin chào")
print(det.flores, det.confidence, det.method)
# vie_Latn 0.79 stopword
```

低置信度时建议显式指定语种,或直接传 `source=`。

## 模型选择

| 规模 | 体积(int8) | 适用 |
|------|-----------|------|
| 600M(默认) | 661MB | 平衡 |
| 1.3B | ~1.4GB | 质量优先 |
| 3.3B | ~3.6GB | 需 8GB+ 显存 |

```bash
python scripts/download_model.py --size 1.3b --out models/nllb-zh-int8-1.3b
```

```python
tr = Translator(model_dir="models/nllb-zh-int8-1.3b")
```

## 速度

本项目默认已做性能调优(i5-1035G1 / 4 物理核 / int8 实测):

| 配置 | 平均延迟 | 相对原状 |
|------|---------|---------|
| 优化前(8 线程 / beam=4) | 1484 ms | — |
| **默认 auto** | **988 ms** | **-33%** |
| `--speed fast` | 700 ms | -53% |
| `--speed balanced` | 875 ms | -41% |
| `--speed quality` | 913 ms | -38% |

默认 auto 的译文与优化前完全一致(0/16 差异),即提速不损质量。

### 两项关键调整

**1. 线程数取物理核心,而非逻辑线程**

这台机器是 4 物理核 / 8 逻辑线程。超线程对矩阵计算几乎无收益,
反而带来同步开销:

| 线程数 | 平均延迟 |
|--------|---------|
| 8(逻辑线程) | 1807 ms |
| 4(物理核心) | 990 ms |

用满 8 线程反而慢 83%。tuning.py 通过 GetLogicalProcessorInformationEx
(Windows)自动读取物理核心数;必须用 Ex 版本,旧版在部分系统上
直接返回 ERROR_INVALID_PARAMETER。

**2. beam 按文本长度自适应**

短句(问候、寒暄)用 beam=1 与 beam=4 几乎没有质量差别,却能省一半时间。
因此 auto 模式会按长度选择:短句降到 2,长句保持档位上限。

### 用法

```bash
zhtrans --speed fast 'Hello world'          # 单次
zhtrans --serve --speed balanced               # 服务端默认档位
zhtrans --threads 4 --serve                    # 手动指定线程数
```

```python
tr = Translator(speed='fast')        # 极速
tr = Translator(speed='quality')     # 高质量
tr.translate(text, speed='fast')     # 单次覆盖
```

HTTP 接口增加 speed 字段(/translate 与 /batch 通用):

```bash
curl -X POST http://127.0.0.1:8848/translate \
  -H "Content-Type: application/json" \
-d ''{text: Hello world, speed: fast}''
```

各档位的差异主要出现在短句问候语上,长句差异很小;
fast 在高棉语上会明显变差(「你是谁」误作「你是个法官吗」),
涉及小语种或正式文本建议用 quality。
## 测试

```bash
python tests/test_core.py        # 28 项单元测试(不需要模型)
python tests/diag_lang.py        # 语种识别准确率
python tests/acceptance.py       # 端到端验收(需要模型)
python tests/web_selftest.py     # 网页自检的等价命令行版本(需先起服务)
node tests/domcheck.js           # 检查 JS 引用的 DOM id 是否都存在
python eval/benchmark.py         # 20 语种质量与速度
```

## 实现要点

**语种识别**(`detect.py`):四层判别,逐层收紧

1. 书写系统 Unicode 区段判定(假名/谚文/汉字为决定性特征)
2. 语种独占字符(如波兰语 ł、越南语 ơư、乌克兰语 їєґ)
3. 问候语词边界匹配(解决「Merhaba」这类无特征字符语种)
4. 功能词整词统计 + 与第二名的分差作置信度

**为什么用 NLLB-200**:原生多语种,而非「翻成英语再翻回来」。
后者在小语种上误差会累积,NLLB 直接在源语种与中文之间对齐。

**繁体输出**:实测 NLLB 的 `zho_Hant` 通道质量很差
("Hello world" 会被译成「您的位置:」),因此本项目统一先译简体,
再用 OpenCC 转繁体。

**术语表**:方向是 `{中文译词: 源语种术语}`。源语种术语在翻译前
被替换为占位符,译后再还原——直接对译文做字符串替换几乎不会命中,
因为模型已经把术语意译了。

## 目录结构

```
src/zh_translator/
  languages.py    121 语种表(ISO <-> FLORES)、中文名、资源层级
  detect.py       语种自动识别(书写系统/独占字符/问候语/功能词)
  tuning.py       性能调优(物理核心检测、速度档位、自适应 beam)
  _words.py       短文本补充词表
  engine.py       翻译引擎(批量解码、切分、术语占位符)
  postprocess.py  中文后处理(标点、OpenCC 简繁、冗余清理)
  cli.py          命令行(SRT / HTML 结构保留)
  server.py       HTTP 服务
scripts/download_model.py
tests/            test_core.py, diag_lang.py, acceptance.py, smoke_test.py
eval/             benchmark.py, sample.srt, sample.html
```

## 说明

- 简繁:默认简体;`target="zh-Hant"` 输出繁体
- 长文本:超过 2000 字符自动切分后翻译
- 若安装了 `langid`,会自动优先使用以提升识别准确率
- 许可:代码 MIT;**模型权重 NLLB-200 为 CC-BY-NC-4.0(禁商用)**,详见 [MODEL_LICENSE.md](MODEL_LICENSE.md)