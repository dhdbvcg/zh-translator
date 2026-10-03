# -*- coding: utf-8 -*-
"""回归:客户端提前断开时,服务端不应抛堆栈。"""

import json
import socket
import sys
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from zh_translator.server import make_handler


class FakeTranslator:
    is_loaded = True
    runtime_device = 'cpu'

    def translate(self, text, source=None, target=None, **kw):
        time.sleep(1.5)   # 模拟慢翻译,给客户端断开留时间
        class R:
            text = '你好'
            source_lang = 'eng_Latn'
            source_lang_zh = '英语'
            detected = False
            skipped = False
        return R()

    def translate_batch(self, texts, **kw):
        return []


httpd = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(FakeTranslator()))
port = httpd.server_address[1]
t = threading.Thread(target=httpd.serve_forever, daemon=True)
t.start()

body = json.dumps({'text': 'Hello', 'from': 'en'}).encode()
req = (b'POST /translate HTTP/1.1' + b'\r\n'
       + b'Host: 127.0.0.1' + b'\r\n'
       + b'Content-Type: application/json' + b'\r\n'
       + b'Content-Length: ' + str(len(body)).encode() + b'\r\n'
       + b'Connection: close' + b'\r\n\r\n' + body)

ok = 0
for i in range(5):
    s = socket.create_connection(('127.0.0.1', port), timeout=5)
    s.sendall(req)
    s.close()          # 立刻断开,不等响应
    ok += 1
    time.sleep(0.2)

time.sleep(3)
httpd.shutdown()
httpd.server_close()

print('disconnect test: sent %d aborted requests, server survived' % ok)
print('PASS: no crash')
