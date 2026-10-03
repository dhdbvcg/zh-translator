"""性能调优:速度档位与线程数推断。

数值来自本机实测(i5-1035G1 / 4 物理核 / NLLB-600M int8),
换机器可用 eval/bench_combo.py 重新测量后调整。
"""

from __future__ import annotations

import os
import subprocess

# 预设速度档位:在延迟与译文质量之间取舍
PRESETS = {
    'fast': {
        'beam': 1,
        'note': '贪心解码,约 480 ms/句,适合网页实时翻译',
    },
    'balanced': {
        'beam': 2,
        'note': '约 630 ms/句,质量与速度折中(默认)',
    },
    'quality': {
        'beam': 4,
        'note': '束搜索,约 960 ms/句,追求准确',
    },
}

# 短句用小 beam 几乎不损质量,长句才真正需要束搜索
SHORT_TEXT_CHARS = 24
MEDIUM_TEXT_CHARS = 60


def auto_beam(text, preset='balanced'):
    """按文本长度选择 beam 宽度。

    短句用小 beam 几乎不损质量却能省一半时间,长句才真正需要束搜索。
    降档只在不高于请求档位的范围内进行,保证 quality >= balanced >= fast。

    注意:极短输入上贪心解码(beam=1)会退化——实测 Guten Tag / Bonjour /
    Buongiorno 都会被译成重复的「您好,您好。」。因此 fast 档在短于
    TINY_TEXT_CHARS 的输入上仍保底用 beam=2。
    """
    base = PRESETS.get(preset, PRESETS['balanced'])['beam']
    if not text:
        return base
    n = len(text.strip())
    if n <= TINY_TEXT_CHARS:
        return max(base, 2)
    if base <= 1:
        return 1
    if n <= SHORT_TEXT_CHARS:
        return 2
    return base

# 极短文本(<6 字符)上贪心解码会产出重复内容,保底用 beam=2
TINY_TEXT_CHARS = 16


_PHYSICAL_CACHE = None


def _physical_cores():
    """读取物理核心数,失败返回 0 表示未知。"""
    global _PHYSICAL_CACHE
    if _PHYSICAL_CACHE is not None:
        return _PHYSICAL_CACHE
    n = 0
    if os.name == 'nt':
        n = _windows_physical_cores()
    else:
        try:
            if hasattr(os, 'sched_getaffinity'):
                n = len(os.sched_getaffinity(0))
        except Exception:
            n = 0
        if not n:
            n = _sysctl_cores()
    _PHYSICAL_CACHE = n
    return n

def _windows_physical_cores():
    """用 GetLogicalProcessorInformationEx 统计物理核心。

    注意两点:旧版 GetLogicalProcessorInformation 在部分 Windows 上直接返回
    ERROR_INVALID_PARAMETER(err=87),必须改用 Ex 版本;
    且缓冲区中每条记录长度不固定,要用结构体自带的 Size 字段步进。
    """
    try:
        import ctypes
        import ctypes.wintypes as wintypes
    except Exception:
        return 0

    class GROUP_AFFINITY(ctypes.Structure):
        _fields_ = [
            ('Mask', ctypes.POINTER(ctypes.c_ulonglong)),
            ('Group', wintypes.WORD),
            ('Reserved', wintypes.WORD * 3),
        ]

    class LPI_EX(ctypes.Structure):
        _fields_ = [
            ('Relationship', wintypes.DWORD),
            ('Size', wintypes.DWORD),
            ('Flags', ctypes.c_ubyte),
            ('EfficiencyClass', ctypes.c_ubyte),
            ('Reserved', ctypes.c_ubyte * 20),
            ('GroupMask', GROUP_AFFINITY),
        ]

    k32 = ctypes.windll.kernel32
    fn = k32.GetLogicalProcessorInformationEx
    fn.restype = wintypes.BOOL
    fn.argtypes = [
        ctypes.c_int, ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(wintypes.DWORD)]

    size = wintypes.DWORD(0)
    fn(0, None, ctypes.byref(size))
    if not size.value:
        return 0
    buf = ctypes.create_string_buffer(size.value)
    # cast 只接受 2 个参数,第三个参数是 fn 自己的 byref(size)
    ok = fn(0, ctypes.cast(buf, ctypes.POINTER(ctypes.c_void_p)),
            ctypes.byref(size))
    if not ok:
        return 0

    count = 0
    off = 0
    head = ctypes.sizeof(LPI_EX)
    while off + head <= size.value:
        item = LPI_EX.from_buffer(buf, off)
        if item.Relationship == 0:
            count += 1
        if not item.Size:
            break
        off += item.Size
    return count


def _sysctl_cores():
    """用 sysctl 取物理核心数(仅 macOS/BSD 有此命令)。"""
    try:
        out = subprocess.run(
            ['sysctl', '-n', 'hw.physicalcpu'],
            capture_output=True, text=True, timeout=1,
        )
        return int(out.stdout.strip())
    except Exception:
        return 0


def default_intra_threads():
    """推断合适的 intraop 线程数。

    超线程对这类矩阵计算几乎没有收益,反而因同步开销变慢:
    本机实测 8 逻辑线程 1807 ms,4 物理线程 990 ms,慢 83%。
    因此优先取物理核心数,并对大机做保守收敛。
    """
    logical = os.cpu_count() or 4
    physical = _physical_cores() or logical
    if physical <= 0:
        return 0
    cap = 8
    return max(1, min(physical, cap))


def describe():
    """返回当前环境的调优信息,便于排查。"""
    logical = os.cpu_count()
    physical = _physical_cores() or logical
    return {
        'logical_cpus': logical,
        'physical_cpus': physical,
        'intra_threads': default_intra_threads(),
    }
