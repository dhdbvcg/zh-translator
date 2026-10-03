"""轻量 HTTP 翻译服务(仅用标准库,无额外依赖)。

启动::

    zhtrans serve --port 8848

接口::

    POST /translate   {"text": "...", "from": "auto", "to": "zh"}
    POST /batch       {"texts": ["...", "..."], "from": "en"}
    GET  /langs       支持的语种列表
    GET  /health      健康检查

本服务为单进程单模型,适合本地使用或内网部署。
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .engine import TranslationError

MAX_BODY = 4 * 1024 * 1024  # 4MB


def make_handler(translator, static_dir=None):
    """为给定翻译器构造 HTTP 请求处理类。

    static_dir 非空时,同时提供该目录下的静态文件(用于测试页面)。
    """
    from pathlib import Path

    if static_dir is not None:
        static_dir = Path(static_dir)

    class Handler(BaseHTTPRequestHandler):
        server_version = "zh-translator/1.0"

        def log_message(self, fmt, *args):  # 静默默认访问日志
            pass

        def handle_one_request(self):
            # 客户端在响应写完前断开(网页刷新、请求超时、Ctrl-C 退出)
            # 属正常现象,不该在终端打一整屏堆栈。
            try:
                BaseHTTPRequestHandler.handle_one_request(self)
            except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                self.close_connection = True

        # ---------- 工具 ----------

        def _send(self, code: int, payload: dict):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            try:
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)
            except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                # 客户端提前断开(页面刷新/超时)是正常现象,静默处理
                self.close_connection = True

        def _read_json(self):
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0:
                return {}
            if length > MAX_BODY:
                raise ValueError("请求体过大")
            return json.loads(self.rfile.read(length).decode("utf-8"))

        def _send_bytes(self, code: int, body: bytes, content_type: str):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def _serve_static(self, url_path: str) -> bool:
            """提供静态文件(仅限 web 目录内,防目录穿越)。"""
            if static_dir is None or not static_dir.is_dir():
                return False
            rel = url_path.lstrip("/") or "index.html"
            target = (static_dir / rel).resolve()
            try:
                target.relative_to(static_dir.resolve())
            except ValueError:
                return False  # 越权访问
            if target.is_dir():
                target = target / "index.html"
            if not target.is_file():
                return False

            ctype = {
                ".html": "text/html; charset=utf-8",
                ".css": "text/css; charset=utf-8",
                ".js": "application/javascript; charset=utf-8",
                ".json": "application/json; charset=utf-8",
                ".svg": "image/svg+xml",
                ".ico": "image/x-icon",
            }.get(target.suffix.lower(), "application/octet-stream")
            self._send_bytes(200, target.read_bytes(), ctype)
            return True

        def _options(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        # ---------- 路由 ----------

        def do_OPTIONS(self):  # noqa: N802
            self._options()

        def do_GET(self):  # noqa: N802
            from . import languages as L

            if self.path.rstrip("/") == "/health":
                self._send(200, {"ok": True, "loaded": translator.is_loaded,
                                 "device": translator.runtime_device})
            elif self.path.rstrip("/") == "/langs":
                items = [
                    {"flores": i.flores, "iso1": i.iso1, "iso3": i.iso3,
                     "zh_name": i.zh_name, "en_name": i.en_name,
                     "script": i.script, "family": i.family,
                     "resource_tier": i.resource_tier}
                    for i in L.LANGS.values() if not L.is_chinese(i.flores)
                ]
                self._send(200, {"count": len(items), "languages": items})
            else:
                # 静态资源(测试页面等)
                if not self._serve_static(self.path.split("?")[0]):
                    self._send(404, {"error": "not found"})

        def do_POST(self):  # noqa: N802
            route = self.path.rstrip("/")
            if route not in {"/translate", "/batch"}:
                self._send(404, {"error": "not found"})
                return
            try:
                data = self._read_json()
            except Exception as exc:
                self._send(400, {"error": f"bad request: {exc}"})
                return

            source = data.get("from") or data.get("source") or "auto"
            target = data.get("to") or "zh"
            try:
                if route == "/translate":
                    text = data.get("text")
                    if not isinstance(text, str):
                        self._send(400, {"error": "缺少 text 字段"})
                        return
                    res = translator.translate(
                        text, source=source, target=target,
                        beam_size=data.get("beam"),
                        speed=data.get("speed"),
                    )
                    self._send(200, {
                        "translation": res.text,
                        "source_lang": res.source_lang,
                        "source_lang_zh": res.source_lang_zh,
                        "detected": res.detected,
                        "skipped": res.skipped,
                    })
                else:
                    texts = data.get("texts")
                    if not isinstance(texts, list):
                        self._send(400, {"error": "缺少 texts 字段"})
                        return
                    results = translator.translate_batch(
                        texts, source=source, target=target,
                        speed=data.get("speed"),
                    )
                    self._send(200, {"translations": [
                        {"translation": r.text, "source_lang": r.source_lang,
                         "skipped": r.skipped} for r in results
                    ]})
            except (TranslationError, ValueError) as exc:
                # 参数问题(语种不支持、类型错误等)属于调用方错误,返回 400
                self._send(400, {"error": str(exc)})
            except Exception as exc:
                self._send(500, {"error": str(exc)})

    return Handler


def serve(translator, host: str = "127.0.0.1", port: int = 8848,
          web_dir=None) -> int:
    """启动 HTTP 服务,阻塞直到 Ctrl-C。

    web_dir 指定后会同时托管该目录下的静态文件,默认指向项目 web/ 目录。
    """
    from pathlib import Path

    if web_dir is None:
        default_web = Path(__file__).resolve().parents[2] / "web"
        web_dir = default_web if default_web.is_dir() else None
    elif str(web_dir) == "off":
        web_dir = None
    else:
        web_dir = Path(web_dir)

    httpd = ThreadingHTTPServer((host, port), make_handler(translator, web_dir))
    print(f"翻译服务已启动: http://{host}:{port}")
    print(f"  POST /translate  {{'text': 'Hello', 'from': 'auto'}}")
    print(f"  POST /batch      {{'texts': [...], 'from': 'auto'}}")
    print(f"  GET  /langs")
    if web_dir:
        print(f"  GET  /            测试页面 ({web_dir})")
    print("按 Ctrl-C 停止")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
    finally:
        httpd.server_close()
    return 0
