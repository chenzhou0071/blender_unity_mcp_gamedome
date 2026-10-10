"""从参考录音提取游戏音效（M5：用户指定直接使用实录）。
用法：
  python tools/audio_extract.py footstep [refmp3]   脚步：10ms 包络找脉冲峰 → 切 4 变体（0.30s）
  python tools/audio_extract.py fire [refmp3]       火盆：整段采用 + 150ms 循环交叉淡化 + 响度对齐
  python tools/audio_extract.py door [refmp3]       石门：裁纯静音 + 头尾淡化 + 响度对齐（单发音）
  python tools/audio_extract.py grind [refmp3]      推石：裁持续摩擦活跃段 + 循环交叉淡化 + 响度对齐
默认参考：docs/milestones/M5/ref_audio/{footstep,fire,door,grind}_ref.mp3
注意：上述 wav 以此脚本产出为准（audio_gen.py 已移除对应合成，重跑勿覆盖）。
"""
import os
import sys
import math
import struct
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audio_gen import write_wav, SR

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "game", "3D-Demo", "Assets", "Audio")
REF = os.path.join(HERE, "..", "docs", "milestones", "M5", "ref_audio", "footstep_ref.mp3")
FIRE_REF = os.path.join(HERE, "..", "docs", "milestones", "M5", "ref_audio", "fire_ref.mp3")
STEP = int(0.30 * SR)          # 每个脚步样本长度（步间隔 0.33s，不跨步）
PRE = int(0.005 * SR)          # 峰值前保留
FADE_OUT = int(0.015 * SR)
LOOP_FADE = int(0.15 * SR)     # 循环交叉淡化长度（火盆/推石）
EDGE_FADE = int(0.01 * SR)     # 单发音头尾淡化（石门）
FIRE_RMS = -25.5               # 火盆目标 RMS（dB，对齐上一版合成响度）
DOOR_RMS = -17.9               # 石门目标 RMS（同上）
GRIND_RMS = -17.2              # 推石目标 RMS（同上）
SILENCE_REL = -60.0            # 首尾静音判定：低于全局峰 X dB 视为静音（door/grind 裁段）
LIMIT_TH = -12.0               # 限幅阈值（dB，只作用于溢出瞬态，主体不动）
LIMIT_RATIO = 8.0              # 限幅比
DOOR_REF = os.path.join(HERE, "..", "docs", "milestones", "M5", "ref_audio", "door_ref.mp3")
GRIND_REF = os.path.join(HERE, "..", "docs", "milestones", "M5", "ref_audio", "grind_ref.mp3")


def decode_mono(mp3):
    """ffmpeg 解码为 44.1kHz 单声道 float 样本（经 stdout，无临时文件）。"""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", mp3,
                          "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return [v / 32768.0 for v in struct.unpack("<%dh" % (len(raw) // 2), raw)]


def find_peaks(s):
    """10ms 包络超阈值（全局峰 25%）取局部最大；80ms 内不重复取峰（一步一次）。"""
    win = int(0.01 * SR)
    env = [math.sqrt(sum(v * v for v in s[i:i + win]) / win)
           for i in range(0, len(s) - win, win)]
    th = max(env) * 0.25
    peaks, i = [], 0
    while i < len(env):
        if env[i] > th:
            j = i
            while j < len(env) and env[j] > th:
                j += 1
            pk = i + max(range(j - i), key=lambda k: env[i + k])
            peaks.append((pk * win, env[pk]))
            i = j + 8
        else:
            i += 1
    return peaks


def slice_at(s, pk):
    start = max(0, pk - PRE)
    return (s[start:start + STEP] + [0.0] * STEP)[:STEP]


def norm_rms(seg, norm=0.9):
    """切片按峰值归一化到 norm 后的 RMS（dB），用于筛选可过自检的样本。"""
    pk = max(abs(v) for v in seg) or 1.0
    k = norm / pk
    return 20 * math.log10(math.sqrt(sum((v * k) ** 2 for v in seg) / len(seg)) + 1e-12)


def footstep_main(ref=REF):
    s = decode_mono(ref)
    peaks = find_peaks(s)
    smax = max(a for _, a in peaks) if peaks else 1.0
    print("peaks:", [(round(p / SR, 2), round(a / smax, 2)) for p, a in peaks])
    # 候选筛选：包络峰强度 ≥ 全局 50%（去双响轻击）+ 归一化后 RMS ≥ -28dB（保自检 -30 余量）
    cand = [(p, slice_at(s, p)) for p, a in peaks if a >= smax * 0.5]
    cand = [(p, seg) for p, seg in cand if norm_rms(seg) >= -28.0]
    if not cand:
        print("ERR: no usable peaks")
        sys.exit(1)
    if len(cand) >= 4:                                       # 均匀抽 4 个
        idx = sorted({round(i * (len(cand) - 1) / 3) for i in range(4)})
        picked = [cand[i] for i in idx]
    else:
        picked = list(cand)
    while len(picked) < 4:                                   # 兜底：候选不足时循环复用
        picked.append(cand[len(picked) % len(cand)])
    for n, (pk, seg) in enumerate(picked[:4], 1):
        seg = list(seg)
        fi = int(0.003 * SR)
        for i in range(fi):                                  # 首 3ms fade in
            seg[i] *= i / fi
        for i in range(FADE_OUT):                            # 尾 15ms fade out
            seg[STEP - FADE_OUT + i] *= 1 - i / FADE_OUT
        name = "footstep_stone_%d.wav" % n
        write_wav(os.path.join(OUT, name), seg, normalize=0.9)
        print("extract:", name, round(STEP / SR, 3), "s  @", round(pk / SR, 2),
              "s  rms %.1f dB" % norm_rms(seg))
    print("OK footsteps extracted from", os.path.basename(ref))


def limit(x, th_db=LIMIT_TH, ratio=LIMIT_RATIO):
    """dB 域限幅：超过阈值部分按 ratio 压缩（阈值处连续，未超部分原样通过）。"""
    th = 10 ** (th_db / 20.0)
    a = abs(x)
    if a <= th:
        return x
    over = 20 * math.log10(a / th)
    y = th * 10 ** (over / ratio / 20.0)
    return y if x >= 0 else -y


def active_span(s, th_rel=-20.0):
    """100ms 窗包络找最长连续活跃段（高于全局峰 th_rel dB），返回 (起, 止) 样本位。"""
    w = int(0.1 * SR)
    wins = [math.sqrt(sum(v * v for v in s[i:i + w]) / w)
            for i in range(0, len(s) - w + 1, w)]
    th = max(wins) * 10 ** (th_rel / 20.0)
    best = (0, 0)
    cur = None
    for i, v in enumerate(wins):
        if v > th:
            if cur is None:
                cur = i
        elif cur is not None:
            if i - cur > best[1] - best[0]:
                best = (cur, i)
            cur = None
    if cur is not None and len(wins) - cur > best[1] - best[0]:
        best = (cur, len(wins))
    return best[0] * w, min(len(s), best[1] * w)


def align_and_write(seg, name, rms_db, loop=False, th_db=-12.0, ratio=8.0):
    """循环交叉淡化（可选）+ RMS 对齐 + 限幅 → 写 wav。"""
    seg = list(seg)
    if loop:
        n = len(seg)
        L = min(LOOP_FADE, n // 4)
        # 交叉淡化：新开头 = 原尾 L 样本（淡出）× 原头 L 样本（淡入），整体去尾 L（循环跳回处连续）
        head = [seg[n - L + i] * (1 - i / L) + seg[i] * (i / L) for i in range(L)]
        seg = head + seg[L:n - L]
    else:
        for i in range(EDGE_FADE):                       # 头尾 10ms fade（防截断爆音）
            seg[i] *= i / EDGE_FADE
            seg[-1 - i] *= i / EDGE_FADE
    rms = math.sqrt(sum(v * v for v in seg) / len(seg))
    g = 10 ** (rms_db / 20.0) / (rms + 1e-12)
    seg = [limit(v * g, th_db, ratio) for v in seg]      # 增益对齐 RMS；限幅吸收溢出瞬态
    out_rms = 20 * math.log10(math.sqrt(sum(v * v for v in seg) / len(seg)) + 1e-12)
    pk = max(abs(v) for v in seg)
    write_wav(os.path.join(OUT, name), seg, normalize=0)
    print("%s: dur %.3f s  rms %.1f dB  peak %.3f" % (name, len(seg) / SR, out_rms, pk))
    return seg


def fire_main(ref=FIRE_REF):
    """火盆实录：整段采用 + 150ms 循环交叉淡化（无缝）+ 增益对齐 RMS -25.5dB + 爆点限幅。"""
    align_and_write(decode_mono(ref), "fire_crackle.wav", FIRE_RMS, loop=True)


def door_main(ref=DOOR_REF):
    """石门实录：裁掉首尾纯静音 + 头尾 10ms 淡化 + 响度对齐。"""
    s = decode_mono(ref)
    a, b = active_span(s, SILENCE_REL)
    print("door span: %.2f-%.2f s (%.2f s)" % (a / SR, b / SR, (b - a) / SR))
    align_and_write(s[a:b], "door_rumble.wav", DOOR_RMS, loop=False, th_db=-1.5, ratio=4.0)


def grind_main(ref=GRIND_REF):
    """推石实录：裁掉首尾静音/拖尾 + 循环交叉淡化 + 响度对齐。"""
    s = decode_mono(ref)
    a, b = active_span(s, SILENCE_REL)
    print("grind span: %.2f-%.2f s (%.2f s)" % (a / SR, b / SR, (b - a) / SR))
    align_and_write(s[a:b], "block_grind.wav", GRIND_RMS, loop=True, th_db=-4.0, ratio=6.0)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "footstep"
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    if mode == "fire":
        fire_main(arg or FIRE_REF)
    elif mode == "door":
        door_main(arg or DOOR_REF)
    elif mode == "grind":
        grind_main(arg or GRIND_REF)
    elif mode == "footstep":
        footstep_main(arg or REF)
    else:
        print("usage: python tools/audio_extract.py [footstep|fire|door|grind] [refmp3]")
        sys.exit(1)


main()
