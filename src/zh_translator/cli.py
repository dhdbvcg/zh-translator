"""命令行工具:把任意语种翻译成中文。

示例::

    # 自动识别语种
    zhtrans "Hello world"

    # 指定源语种
    zhtrans --from ja "こんにちは世界"
    zhtrans --from en --to zh-Hant "Hello world"

    # 文件翻译(SRT 字幕保留时间轴)
    zhtrans --input sub.srt --output sub.zh.srt --from en

    # 批量翻译目录下所有 .txt
    zhtrans --input docs/ --output out/ --to-file --from auto

    # 启动 HTTP 服务
    zhtrans serve --port 8848
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

from . import languages as L
from .engine import Translator, TranslationError

# SRT 字幕时间轴格式
_SRT_TIME = re.compile(
    r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*"
    r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{3})"
)


def _is_srt(text: str) -> bool:
    return bool(_SRT_TIME.search(text)) and "-->" in text


def _translate_srt(tr: Translator, text: str, source, target) -> str:
    """翻译 SRT 字幕,保留序号与时间轴,合并多行以提升译文连贯性。

    注意:SRT 常见 CRLF 行尾。若直接 split("\n"),每行会残留 "\r",
    导致时间轴正则匹配失败、整段原样返回(翻译被静默跳过),
    因此这里先统一行尾。
    """
    newline = "\r\n" if "\r\n" in text else "\n"
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")

    # 以空行为分隔切块。注意:不能用 \n\s*\n 切,因为字幕块内部是
    # 「序号 / 时间轴 / 文本」逐行排列,并不含空行;真正的分隔是空行。
    blocks = re.split(r"\n[ \t]*\n", normalized.strip())
    out_blocks = []
    for block in blocks:
        lines = [ln for ln in block.split("\n")]
        # 去掉块首尾空行
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        if not lines:
            continue

        # 定位时间轴行
        tpos = None
        for i, ln in enumerate(lines):
            if _SRT_TIME.search(ln):
                tpos = i
                break

        if tpos is None:
            out_blocks.append("\n".join(lines))
            continue

        idx_part = lines[:tpos]
        timing = lines[tpos].strip()
        body = [x.strip() for x in lines[tpos + 1:] if x.strip()]
        if not body:
            out_blocks.append("\n".join(lines))
            continue

        joined = " ".join(body)
        try:
            res = tr.translate(joined, source=source, target=target)
        except TranslationError as exc:
            print(f"[warn] 字幕块翻译失败: {exc}", file=sys.stderr)
            out_blocks.append("\n".join(lines))
            continue

        head = "\n".join(idx_part + [timing]) if idx_part else timing
        # 译文按标点折行,贴近字幕习惯
        out_blocks.append(head + "\n" + res.text)

    if not out_blocks:
        return text
    return ("\n\n".join(out_blocks) + "\n").replace("\n", newline)


# 需要翻译的 HTML 标签:文本内容通常是正文
_TRANSLATABLE = {
    'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'td', 'th',
    'blockquote', 'caption', 'summary', 'figcaption', 'label',
}

# 这些标签内部通常不翻译(脚本、样式、代码)
_SKIP_TAGS = {'script', 'style', 'code', 'pre', 'textarea', 'kbd', 'samp'}

_TAG = re.compile("(<[^>]+>)")
_HTMLISH = re.compile("<(html|body|div|p|h[1-6]|ul|ol|li|table|br|span|a)",
                    re.IGNORECASE)


def _looks_html(text: str) -> bool:
    """判断是否为 HTML 片段。"""
    return bool(_HTMLISH.search(text or ""))


def _translate_html(tr: Translator, html: str, source, target) -> str:
    """翻译 HTML 中的可见文本,保留标签与文档结构。"""
    out = []
    pos = 0
    skip_tag = None

    for m in _TAG.finditer(html):
        out.append(html[pos:m.start()])
        tag_text = m.group(1)
        pos = m.end()

        nm = re.match(r"</?\s*([A-Za-z0-9]+)", tag_text)
        name = nm.group(1).lower() if nm else ""
        closing = tag_text.startswith("</")

        if skip_tag is not None:
            if name == skip_tag and closing:
                skip_tag = None
            out.append(tag_text)
            continue

        if not closing and name in _SKIP_TAGS:
            skip_tag = name
            out.append(tag_text)
            continue

        out.append(tag_text)
        nxt = _TAG.search(html, pos)
        seg_end = len(html) if nxt is None else nxt.start()
        segment = html[pos:seg_end]

        if name in _TRANSLATABLE and not closing and segment.strip():
            try:
                res = tr.translate(segment.strip(), source=source, target=target)
                lead = segment[:len(segment) - len(segment.lstrip())]
                trail = segment[len(segment.rstrip()):]
                out.append(lead + res.text + trail)
            except TranslationError as exc:
                print("[warn] HTML 翻译失败: %s" % exc, file=sys.stderr)
                out.append(segment)
        else:
            out.append(segment)
        pos = seg_end

    out.append(html[pos:])
    return "".join(out)

def _translate_text(tr: Translator, text: str, source, target) -> str:
    if _is_srt(text):
        return _translate_srt(tr, text, source, target)
    if _looks_html(text):
        return _translate_html(tr, text, source, target)
    return tr.translate(text, source=source, target=target).text


def _read_input(path: str) -> str:
    """读取输入文件。

    必须用 newline="" 关闭通用换行转换:否则 CRLF 会被读成 LF,
    使得行尾风格无法保留,输出也无法沿用原文件的行尾。
    同时兼容 UTF-8 BOM。
    """
    p = Path(path)
    if p.is_dir():
        raise TranslationError("目录输入请使用 --to-file 模式")
    raw = p.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    return raw.decode("utf-8", errors="replace")


def _do_translate(tr: Translator, args) -> int:
    if args.input:
        text = _read_input(args.input)
    else:
        text = " ".join(args.text or [])
    if not text.strip():
        print("输入为空", file=sys.stderr)
        return 1

    t0 = time.time()
    out = _translate_text(tr, text, args.source, args.target)
    dt = time.time() - t0

    if args.json:
        print(json.dumps({"translation": out, "elapsed": round(dt, 3)},
                         ensure_ascii=False, indent=2))
    elif args.output:
        Path(args.output).write_bytes(out.encode("utf-8"))
        print(f"[done] 已写入 {args.output}  ({len(out)} 字符, {dt:.2f}s)")
    else:
        sys.stdout.write(out + "\n")
    return 0


def _do_batch(tr: Translator, args) -> int:
    in_path = Path(args.input)
    out_dir = Path(args.output or "translated")
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(in_path.rglob("*")) if in_path.is_dir() else [in_path]
    targets = [f for f in files if f.is_file()
               and (f.suffix.lower() in {".txt", ".md", ".srt", ".vtt", ".html", ".htm"})]
    if not targets:
        print("未找到可翻译的文件(.txt/.md/.srt/.vtt/.html)", file=sys.stderr)
        return 1

    ok, fail = 0, 0
    for i, f in enumerate(targets, 1):
        rel = f.relative_to(in_path) if in_path.is_dir() else Path(f.name)
        dst = out_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            src_text = _read_input(str(f))
            out = _translate_text(tr, src_text, args.source, args.target)
            dst.write_bytes(out.encode("utf-8"))
            ok += 1
            print(f"[{i}/{len(targets)}] OK   {rel}")
        except Exception as exc:
            fail += 1
            print(f"[{i}/{len(targets)}] FAIL {rel}: {exc}", file=sys.stderr)
    print(f"\n完成: 成功 {ok},失败 {fail}")
    return 0 if fail == 0 else 1


def _do_langs(tr: Translator, args) -> int:
    if args.langs:
        rows = sorted(L.LANGS.values(), key=lambda x: x.iso1)
        tier_mark = {"high": "★", "mid": "☆", "low": "·"}
        print(f"共支持 {len(rows)} 个源语种 -> 简体中文\n")
        for info in rows:
            if L.is_chinese(info.flores):
                continue
            print(f"  {info.iso1:>4}  {tier_mark.get(info.resource_tier, ' ')} "
                  f"{info.zh_name:<8} ({info.en_name}, {info.family})")
        print("\n★ 语料充足  ☆ 中等  · 低资源(小语种,质量受限)")
        return 0
    text = " ".join(args.text or []) or (args.input and _read_input(args.input) or "")
    if not text.strip():
        print("需要待识别的文本", file=sys.stderr)
        return 1
    det = tr.detect(text)
    info = L.LANGS.get(det.flores) or L.LANGS["eng_Latn"]
    print(json.dumps({
        "flores": info.flores, "iso1": info.iso1, "iso3": info.iso3,
        "zh_name": info.zh_name, "en_name": info.en_name,
        "script": info.script, "family": info.family,
        "resource_tier": info.resource_tier,
        "confidence": det.confidence, "method": det.method,
    }, ensure_ascii=False, indent=2))
    return 0


def _do_serve(tr: Translator, args) -> int:
    try:
        from .server import serve
    except ImportError as exc:
        print(f"服务端依赖缺失: {exc}", file=sys.stderr)
        return 1
    return serve(tr, host=args.host, port=args.port, web_dir=args.web)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="zhtrans",
        description="多语种(含小语种) -> 简体中文 翻译工具",
    )
    ap.add_argument("text", nargs="*", help="待翻译文本")
    ap.add_argument("-i", "--input", help="输入文件路径")
    ap.add_argument("-o", "--output", help="输出文件路径")
    ap.add_argument("-f", "--from", dest="source", default="auto",
                    help="源语种(默认 auto 自动识别)")
    ap.add_argument("-t", "--to", dest="target", default="zh",
                    help="目标语种: zh(简体) / zh-Hant(繁体)")
    ap.add_argument("-b", "--beam", type=int, default=None, help="beam 宽度")
    ap.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"],
                    help="推理设备")
    ap.add_argument("--model", default=None, help="模型目录")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    ap.add_argument("--to-file", action="store_true", help="批量翻译目录下所有文件")
    ap.add_argument("--langs", action="store_true", help="列出所有支持的源语种")
    ap.add_argument("--serve", action="store_true", help="启动 HTTP 翻译服务")
    ap.add_argument("--host", default="127.0.0.1", help="服务监听地址")
    ap.add_argument("--port", type=int, default=8848, help="服务监听端口")
    ap.add_argument("--speed", default="auto",
                    choices=["auto", "fast", "balanced", "quality"],
                    help="速度档位: fast 最快 / balanced 折中 / quality 最准")
    ap.add_argument("--threads", type=int, default=0,
                    help="推理线程数,0 表示按物理核心数自动(推荐)")
    ap.add_argument("--web", default=None,
                    help="额外托管的静态页面目录,默认 web/;传 off 关闭")
    return ap


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # 兼容旧写法:首个 token 为 langs / serve 时视为子命令
    legacy = None
    if argv and argv[0] in {"langs", "serve"}:
        legacy, argv = argv[0], argv[1:]

    ap = build_parser()
    args = ap.parse_args(argv)

    if legacy == "langs":
        args.langs = True
    if legacy == "serve":
        args.serve = True

    args.cmd = "langs" if args.langs else ("serve" if args.serve else "translate")

    tr = Translator(model_dir=args.model, device=args.device,
                   beam_size=args.beam or 4, speed=args.speed,
                   intra_threads=args.threads or 0)
    if args.cmd != "langs":
        try:
            tr.load()
        except TranslationError as exc:
            print("[error] %s" % exc, file=sys.stderr)
            return 2

    try:
        if args.cmd == "langs":
            return _do_langs(tr, args)
        if args.cmd == "serve":
            return _do_serve(tr, args)
        if args.to_file:
            return _do_batch(tr, args)
        return _do_translate(tr, args)
    except TranslationError as exc:
        print("[error] %s" % exc, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("已中断", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
